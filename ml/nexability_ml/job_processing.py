from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol
from uuid import UUID

from pydantic import ValidationError

from .config import GROQ_MODEL
from .groq_extraction import is_safe_professional_text
from .pipeline import NexAbilityMLPipeline
from .schemas import JobExtraction, JobProfile, RequirementEnrichment

JOB_PROFILE_SCHEMA_VERSION = "1"


class JobDocumentProfileRepository(Protocol):
    def claim(
        self, document_id: UUID, employer_profile_id: UUID, *, force: bool = False
    ) -> int | None: ...

    def complete(
        self,
        document_id: UUID,
        attempt: int,
        *,
        profile_json: dict[str, Any],
        provider: str,
        model: str | None,
        schema_version: str,
        extraction_mode: str,
        llm_skipped_reason: str | None,
    ) -> None: ...

    def fail(self, document_id: UUID, attempt: int, *, error_details: str) -> None: ...


class JobProcessingError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def validate_job_profile(
    pipeline_result: Mapping[str, Any], document_id: UUID, employer_profile_id: UUID
) -> tuple[dict[str, Any], str, str | None]:
    normalized = pipeline_result.get("structured_profile")
    if not isinstance(normalized, Mapping):
        raise JobProcessingError("invalid_rule_based_profile")

    source_requirements = normalized.get("requirements", [])
    if not isinstance(source_requirements, list):
        raise JobProcessingError("invalid_rule_based_profile")

    extraction_mode = pipeline_result.get("extraction_mode")
    enrichments: list[RequirementEnrichment] = []
    if extraction_mode == "llm":
        try:
            llm_result = JobExtraction.model_validate(pipeline_result.get("llm_extraction"))
        except ValidationError:
            raise JobProcessingError("invalid_llm_enrichment") from None
        if len(llm_result.requirement_enrichments) != len(source_requirements):
            raise JobProcessingError("invalid_llm_enrichment")
        for requirement, enrichment in zip(
            source_requirements,
            llm_result.requirement_enrichments,
            strict=True,
        ):
            if (
                not isinstance(requirement, Mapping)
                or enrichment.original_requirement != requirement.get("requirement")
            ):
                raise JobProcessingError("invalid_llm_enrichment")
            if not is_safe_professional_text(enrichment.original_requirement):
                continue
            enrichments.append(
                RequirementEnrichment(
                    original_requirement=enrichment.original_requirement,
                    normalized_requirement=(
                        enrichment.normalized_requirement
                        if enrichment.normalized_requirement
                        and is_safe_professional_text(enrichment.normalized_requirement)
                        else None
                    ),
                    normalized_skill=(
                        enrichment.normalized_skill
                        if enrichment.normalized_skill
                        and is_safe_professional_text(enrichment.normalized_skill)
                        else None
                    ),
                )
            )

    safe_requirements = []
    for requirement in source_requirements:
        if not isinstance(requirement, Mapping):
            continue
        text = requirement.get("requirement")
        category = requirement.get("category")
        priority = requirement.get("priority")
        if (
            not isinstance(text, str)
            or not isinstance(category, str)
            or not isinstance(priority, str)
            or not is_safe_professional_text(text)
        ):
            continue
        normalized_skill = requirement.get("normalized_skill")
        safe_requirements.append(
            {
                "requirement": text,
                "category": category,
                "priority": priority,
                "normalized_skill": (
                    normalized_skill
                    if isinstance(normalized_skill, str)
                    and is_safe_professional_text(normalized_skill)
                    else None
                ),
            }
        )

    def values_for(category: str) -> list[str]:
        return [
            item["requirement"]
            for item in safe_requirements
            if item["category"] == category
        ]

    title = normalized.get("job_title")
    payload = {
        "job_id": str(document_id),
        "employer_id": str(employer_profile_id),
        "job_title": title if isinstance(title, str) and is_safe_professional_text(title) else None,
        "required_skills": values_for("required_skills"),
        "preferred_skills": values_for("preferred_skills"),
        "responsibilities": values_for("responsibilities"),
        "domain_knowledge": values_for("domain_knowledge"),
        "education_requirements": values_for("education"),
        "experience_requirements": values_for("experience"),
        "requirements": safe_requirements,
        "requirement_enrichments": [
            item.model_dump(mode="json") for item in enrichments
        ],
        "required_qualifications": values_for("education"),
        "preferred_qualifications": [],
    }

    try:
        profile = JobProfile.model_validate(payload).model_dump(mode="json")
    except ValidationError:
        raise JobProcessingError("profile_validation_failed") from None

    if extraction_mode not in {"llm", "rule_based"}:
        raise JobProcessingError("invalid_extraction_mode")
    return (
        profile,
        "groq" if extraction_mode == "llm" else "rule_based",
        GROQ_MODEL if extraction_mode == "llm" else None,
    )


class JobDocumentProcessor:
    """Processes backend-owned job documents and persists profiles by document ID."""

    def __init__(
        self,
        *,
        client: Any,
        repository: JobDocumentProfileRepository,
        pipeline: NexAbilityMLPipeline,
    ) -> None:
        self.client = client
        self.repository = repository
        self.pipeline = pipeline

    def process_job_metadata(
        self, queued_document: Mapping[str, Any], *, force: bool = False
    ) -> str:
        if not isinstance(queued_document, Mapping):
            raise JobProcessingError("invalid_queue_item")
        if queued_document.get("document_type") != "JOB_DOCUMENT":
            raise JobProcessingError("invalid_document_type")
        try:
            document_id = UUID(str(queued_document["document_id"]))
            employer_profile_id = UUID(str(queued_document["owner_id"]))
        except (KeyError, TypeError, ValueError):
            raise JobProcessingError("invalid_queue_identifiers") from None

        attempt = self.repository.claim(
            document_id, employer_profile_id, force=force
        )
        if attempt is None:
            return "skipped"

        stage = "metadata"
        try:
            metadata = self.client.get_job_document_metadata(str(document_id))
            self._validate_metadata(metadata, document_id, employer_profile_id)

            stage = "download"
            document_bytes = self.client.get_job_document_content(str(document_id))
            if not isinstance(document_bytes, bytes) or not document_bytes:
                raise JobProcessingError("empty_document_content")

            stage = "extraction"
            result = self.pipeline.process_job_document(
                document_bytes=document_bytes,
                filename=str(metadata["original_filename"]),
                employer_id=str(employer_profile_id),
                job_id=str(document_id),
                content_type=str(metadata["mime_type"]),
            )
            if result.get("document_status") != "processed":
                raise JobProcessingError("no_extractable_text")

            profile_json, provider, model = validate_job_profile(
                result, document_id, employer_profile_id
            )
            stage = "persistence"
            self.repository.complete(
                document_id,
                attempt,
                profile_json=profile_json,
                provider=provider,
                model=model,
                schema_version=JOB_PROFILE_SCHEMA_VERSION,
                extraction_mode=str(result["extraction_mode"]),
                llm_skipped_reason=result.get("llm_skipped_reason"),
            )
        except Exception as exc:
            error_details = (
                exc.code
                if isinstance(exc, JobProcessingError)
                else f"{stage}_{type(exc).__name__}".casefold()
            )
            self.repository.fail(
                document_id,
                attempt,
                error_details=error_details,
            )
            return "failed"
        return "processed"

    @staticmethod
    def _validate_metadata(
        metadata: Any, document_id: UUID, employer_profile_id: UUID
    ) -> None:
        if not isinstance(metadata, Mapping):
            raise JobProcessingError("invalid_document_metadata")
        try:
            response_id = UUID(str(metadata["document_id"]))
            response_owner_id = UUID(str(metadata["owner_id"]))
        except (KeyError, TypeError, ValueError):
            raise JobProcessingError("invalid_document_metadata") from None
        if response_id != document_id or response_owner_id != employer_profile_id:
            raise JobProcessingError("document_metadata_mismatch")
        if not isinstance(metadata.get("original_filename"), str):
            raise JobProcessingError("invalid_document_metadata")
        if not isinstance(metadata.get("mime_type"), str):
            raise JobProcessingError("invalid_document_metadata")
