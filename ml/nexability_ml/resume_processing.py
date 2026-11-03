from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from typing import Any, Protocol
from uuid import UUID

from pydantic import ValidationError

from .config import GROQ_MODEL
from .groq_extraction import sanitize_resume_profile_for_storage
from .pipeline import NexAbilityMLPipeline
from .schemas import ExtractedSkill, ResumeExtraction

logger = logging.getLogger(__name__)

RESUME_PROFILE_SCHEMA_VERSION = "1"
RULE_BASED_PROVIDER = "rule_based"


class CandidateResumeProfileRepository(Protocol):
    def claim(
        self, candidate_profile_id: UUID, resume_id: UUID, *, force: bool = False
    ) -> int | None: ...

    def complete(
        self,
        resume_id: UUID,
        attempt: int,
        *,
        profile_json: dict[str, Any],
        provider: str,
        model: str | None,
        schema_version: str,
        extraction_mode: str,
        llm_skipped_reason: str | None,
    ) -> None: ...

    def fail(
        self,
        resume_id: UUID,
        attempt: int,
        *,
        error_details: str,
    ) -> None: ...


class ResumeProcessingError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def validate_resume_profile(
    pipeline_result: Mapping[str, Any],
) -> tuple[dict[str, Any], str, str | None]:
    extraction_mode = pipeline_result.get("extraction_mode")
    if extraction_mode == "llm":
        raw_profile = pipeline_result.get("llm_extraction")
        provider = "groq"
        model = GROQ_MODEL
    else:
        normalized = pipeline_result.get("structured_profile")
        if not isinstance(normalized, Mapping):
            raise ResumeProcessingError("invalid_rule_based_profile")

        source_text = pipeline_result.get("safe_source_text")
        if not isinstance(source_text, str):
            source_text = ""
        skills: list[dict[str, Any]] = []
        for item in normalized.get("skills", []):
            if not isinstance(item, str):
                continue
            evidence_pattern = re.compile(
                rf"(?<![A-Za-z0-9]){re.escape(item)}(?![A-Za-z0-9])",
                flags=re.IGNORECASE,
            )
            evidence = [
                line.strip()
                for line in source_text.splitlines()
                if evidence_pattern.search(line)
            ]
            skills.append(
                ExtractedSkill(name=item, evidence=evidence).model_dump(mode="json")
            )

        raw_profile = {
            "full_name": normalized.get("full_name"),
            "email": normalized.get("email"),
            "professional_summary": None,
            "skills": skills,
            "experience": [
                {
                    "company": entry.get("company"),
                    "job_title": entry.get("job_title"),
                }
                for entry in normalized.get("work_experience", [])
                if isinstance(entry, Mapping)
            ],
        }
        provider = RULE_BASED_PROVIDER
        model = None

    if not isinstance(raw_profile, Mapping):
        raise ResumeProcessingError("missing_extracted_profile")

    try:
        validated = ResumeExtraction.model_validate(raw_profile)
    except ValidationError as exc:
        raise ResumeProcessingError("profile_validation_failed") from exc

    profile = sanitize_resume_profile_for_storage(validated.model_dump(mode="json"))
    validated = ResumeExtraction.model_validate(profile)
    profile = validated.model_dump(mode="json")
    profile["full_name"] = None
    profile["email"] = None
    profile["phone"] = None
    profile["location"] = None
    return profile, provider, model


class ResumeExtractionProcessor:
    """Processes active backend resumes and persists one validated profile per resume."""

    def __init__(
        self,
        *,
        client: Any,
        repository: CandidateResumeProfileRepository,
        pipeline: NexAbilityMLPipeline | None = None,
    ) -> None:
        self.client = client
        self.repository = repository
        self.pipeline = pipeline or NexAbilityMLPipeline()

    def process_pending_resumes(self) -> dict[str, int]:
        queue = self.client.list_pending_documents()
        if not isinstance(queue, Mapping) or not isinstance(queue.get("active_resumes"), list):
            raise RuntimeError("The backend pending-resume response has an invalid shape.")

        counts = {"processed": 0, "skipped": 0, "failed": 0}
        for document in queue["active_resumes"]:
            outcome = self.process_resume_metadata(document)
            counts[outcome] += 1
        return counts

    def process_resume_metadata(
        self, queued_document: Mapping[str, Any], *, force: bool = False
    ) -> str:
        if not isinstance(queued_document, Mapping):
            raise ValueError("A resume queue item must be an object.")
        if queued_document.get("document_type") != "RESUME":
            raise ValueError("Only resume documents can be processed by this worker.")

        try:
            resume_id = UUID(str(queued_document["document_id"]))
            candidate_profile_id = UUID(str(queued_document["owner_id"]))
        except (KeyError, ValueError, TypeError) as exc:
            raise ValueError("Resume queue item is missing valid document or owner IDs.") from exc

        attempt = self.repository.claim(candidate_profile_id, resume_id, force=force)
        if attempt is None:
            return "skipped"

        stage = "metadata"
        try:
            metadata = self.client.get_resume_metadata(str(resume_id))
            self._validate_metadata(metadata, resume_id, candidate_profile_id)

            stage = "download"
            document_bytes = self.client.get_resume_content(str(resume_id))
            if not isinstance(document_bytes, bytes) or not document_bytes:
                raise ResumeProcessingError("empty_document_content")

            stage = "extraction"
            result = self.pipeline.process_resume_document(
                document_bytes=document_bytes,
                filename=str(metadata["original_filename"]),
                candidate_id=str(candidate_profile_id),
                content_type=str(metadata["mime_type"]),
            )
            if result.get("document_status") != "processed":
                raise ResumeProcessingError("no_extractable_text")

            profile_json, provider, model = validate_resume_profile(result)
            stage = "persistence"
            self.repository.complete(
                resume_id,
                attempt,
                profile_json=profile_json,
                provider=provider,
                model=model,
                schema_version=RESUME_PROFILE_SCHEMA_VERSION,
                extraction_mode=str(result["extraction_mode"]),
                llm_skipped_reason=result.get("llm_skipped_reason"),
            )
        except Exception as exc:
            error_details = (
                exc.code
                if isinstance(exc, ResumeProcessingError)
                else f"{stage}_{type(exc).__name__}".casefold()
            )
            self.repository.fail(
                resume_id,
                attempt,
                error_details=error_details,
            )
            logger.warning(
                "Résumé extraction failed for resume_id=%s error_code=%s",
                resume_id,
                error_details,
            )
            return "failed"

        return "processed"

    @staticmethod
    def _validate_metadata(
        metadata: Any, resume_id: UUID, candidate_profile_id: UUID
    ) -> None:
        if not isinstance(metadata, Mapping):
            raise ResumeProcessingError("invalid_document_metadata")
        try:
            response_resume_id = UUID(str(metadata["document_id"]))
            response_candidate_id = UUID(str(metadata["owner_id"]))
        except (KeyError, ValueError, TypeError) as exc:
            raise ResumeProcessingError("invalid_document_metadata") from exc

        if (
            metadata.get("document_type") != "RESUME"
            or response_resume_id != resume_id
            or response_candidate_id != candidate_profile_id
            or not metadata.get("original_filename")
            or not metadata.get("mime_type")
        ):
            raise ResumeProcessingError("document_metadata_mismatch")
