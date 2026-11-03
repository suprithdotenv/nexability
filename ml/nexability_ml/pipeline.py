from __future__ import annotations

import logging
from typing import Any

from .accessibility_repository import AccessibilityProfileRepository
from .chunking import chunk_document_text
from .config import NEXABILITY_LLM_EXTRACTION
from .embeddings import create_embedding_model, create_tokenizer, retrieve_resume_chunks
from .groq_extraction import (
    GroqExtractionClient,
    GroqExtractionError,
    PrivacyFilterError,
    prepare_resume_text_for_groq,
)
from .matcher import _job_requirements, build_accessibility_summary, match_candidate_to_jobs
from .normalizer import normalize_job_description, normalize_resume_profile
from .parser import parse_document_bytes

logger = logging.getLogger(__name__)


class NexAbilityMLPipeline:
    """End-to-end extraction and matching pipeline for resume and job documents."""

    def __init__(
        self,
        embedding_model: Any = None,
        *,
        extraction_client: Any = None,
        enable_llm_extraction: bool | None = None,
        tokenizer: Any = None,
    ):
        self.embedding_model = embedding_model or create_embedding_model()
        self.extraction_client = extraction_client or GroqExtractionClient()
        self.enable_llm_extraction = (
            NEXABILITY_LLM_EXTRACTION
            if enable_llm_extraction is None
            else enable_llm_extraction
        )
        self.tokenizer = tokenizer or create_tokenizer()

    def _extract_resume_with_llm(
        self, text: str
    ) -> tuple[str, Any, str | None, str]:
        safe_source_text = prepare_resume_text_for_groq(text)
        if not self.enable_llm_extraction:
            return "rule_based", None, None, safe_source_text or ""
        if safe_source_text is None:
            return "rule_based", None, "privacy_filter", ""
        try:
            extracted = self.extraction_client.extract_resume(text)
        except PrivacyFilterError:
            return "rule_based", None, "privacy_filter", ""
        except GroqExtractionError:
            logger.warning("Groq résumé extraction failed; using rule-based extraction.")
            return "rule_based", None, None, safe_source_text
        if extracted is None:
            return "rule_based", None, None, safe_source_text
        return "llm", extracted, None, safe_source_text

    def _enrich_job_with_llm(
        self, text: str, requirements: list[dict[str, Any]]
    ) -> tuple[str, Any, str | None]:
        if not self.enable_llm_extraction:
            return "rule_based", None, None
        try:
            extracted = self.extraction_client.enrich_job(text, requirements)
        except PrivacyFilterError:
            return "rule_based", None, "privacy_filter"
        except GroqExtractionError:
            logger.warning("Groq job extraction failed; using rule-based extraction.")
            return "rule_based", None, "provider_error"
        return ("llm", extracted, None) if extracted is not None else ("rule_based", None, None)

    def process_resume_document(
        self,
        *,
        document_bytes: bytes,
        filename: str,
        candidate_id: str | None = None,
        content_type: str | None = None,
        candidate_profile: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        extraction = parse_document_bytes(document_bytes, filename, content_type)
        (
            extraction_mode,
            llm_extraction,
            llm_skipped_reason,
            safe_source_text,
        ) = (
            self._extract_resume_with_llm(extraction.text)
        )
        normalized = normalize_resume_profile(
            extraction.text,
            candidate_id=candidate_id,
            full_name=(candidate_profile or {}).get("full_name"),
            email=(candidate_profile or {}).get("email"),
        )
        chunks = chunk_document_text(
            extraction.text,
            metadata={"document_type": "resume", "candidate_id": candidate_id},
            tokenizer=self.tokenizer,
        )
        embeddings = self.embedding_model.encode(
            [chunk["text"] for chunk in chunks], prefix="passage: "
        )
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            chunk["embedding"] = embedding
        return {
            "extraction": extraction,
            "structured_profile": normalized,
            "chunks": chunks,
            "extraction_mode": extraction_mode,
            "llm_skipped_reason": llm_skipped_reason,
            "safe_source_text": safe_source_text,
            "llm_extraction": (
                llm_extraction.model_dump() if llm_extraction is not None else None
            ),
            "document_status": "processed" if extraction.text.strip() else "empty",
            "is_scanned": extraction.is_scanned,
        }

    def process_job_document(
        self,
        *,
        document_bytes: bytes,
        filename: str,
        employer_id: str | None = None,
        job_id: str | None = None,
        content_type: str | None = None,
    ) -> dict[str, Any]:
        extraction = parse_document_bytes(document_bytes, filename, content_type)
        normalized = normalize_job_description(
            extraction.text, employer_id=employer_id, job_id=job_id
        )
        extraction_mode, llm_extraction, llm_skipped_reason = self._enrich_job_with_llm(
            extraction.text, normalized["requirements"]
        )
        chunks = chunk_document_text(
            extraction.text,
            metadata={"document_type": "job", "job_id": job_id},
            tokenizer=self.tokenizer,
        )
        embeddings = self.embedding_model.encode(
            [chunk["text"] for chunk in chunks], prefix="query: "
        )
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            chunk["embedding"] = embedding
        return {
            "extraction": extraction,
            "structured_profile": normalized,
            "chunks": chunks,
            "extraction_mode": extraction_mode,
            "llm_skipped_reason": llm_skipped_reason,
            "llm_extraction": (
                llm_extraction.model_dump() if llm_extraction is not None else None
            ),
            "document_status": "processed" if extraction.text.strip() else "empty",
            "is_scanned": extraction.is_scanned,
        }

    def match_candidates_to_jobs(
        self,
        candidate_profile: dict[str, Any],
        job_profiles: list[dict[str, Any]],
        *,
        accessibility_profiles: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        accessibility_profiles = accessibility_profiles or {}
        source_text = candidate_profile.get("source_text")
        retrieved_chunks_by_job = {
            index: retrieve_resume_chunks(
                source_text if isinstance(source_text, str) else "",
                [item["requirement"] for item in _job_requirements(job)],
                embedding_model=self.embedding_model,
                tokenizer=self.tokenizer,
            )
            for index, job in enumerate(job_profiles)
        }
        ranked_jobs = match_candidate_to_jobs(
            candidate_profile,
            job_profiles,
            retrieved_chunks_by_job=retrieved_chunks_by_job,
            candidate_accessibility_preferences=accessibility_profiles.get(
                "candidate_accessibility_preferences"
            ),
            employer_accessibility_capabilities=accessibility_profiles.get(
                "employer_accessibility_capabilities"
            ),
            employer_profile_completed=accessibility_profiles.get("employer_profile_completed"),
        )
        best_job = ranked_jobs[0] if ranked_jobs else None
        if best_job is None:
            status = "no_match"
        elif (
            best_job["professional_match"]["professional_evidence_score"]["status"]
            == "unavailable"
        ):
            status = "assessment_incomplete"
        elif best_job["professional_match"]["professional_evidence_score"]["value"] < 50:
            status = "low_confidence_match"
        else:
            status = "match_found"

        result = {
            "status": status,
            "ranked_jobs": ranked_jobs,
            "best_match": best_job,
            "accessibility_summary": build_accessibility_summary(
                candidate_profile,
                next(
                    (
                        job
                        for job in job_profiles
                        if job.get("job_id") == best_job.get("job_id")
                        and job.get("job_title") == best_job.get("job_title")
                    ),
                    {},
                ),
                candidate_accessibility_preferences=accessibility_profiles.get(
                    "candidate_accessibility_preferences"
                ),
                employer_accessibility_capabilities=accessibility_profiles.get(
                    "employer_accessibility_capabilities"
                ),
                employer_profile_completed=accessibility_profiles.get("employer_profile_completed"),
            )
            if best_job
            else {
                "candidate_name": candidate_profile.get("full_name"),
                "job_title": None,
                "requirements": [],
            },
        }
        if accessibility_profiles.get("sources"):
            result["accessibility_data_sources"] = accessibility_profiles["sources"]
        return result

    def match_candidates_to_jobs_from_backend(
        self,
        candidate_profile: dict[str, Any],
        job_profiles: list[dict[str, Any]],
        *,
        repository: AccessibilityProfileRepository,
        candidate_id: str,
        employer_id: str,
    ) -> dict[str, Any]:
        employer_profile = repository.get_employer_accessibility_profile(employer_id)
        accessibility_profiles = {
            "candidate_accessibility_preferences": (
                repository.get_candidate_accessibility_preferences(candidate_id)
            ),
            "employer_accessibility_capabilities": employer_profile["capabilities"],
            "employer_profile_completed": employer_profile["profile_completed"],
            "sources": {
                "candidate": (f"/api/v1/internal/ml/candidates/{candidate_id}/accessibility"),
                "employer": (f"/api/v1/internal/ml/employers/{employer_id}/accessibility"),
            },
        }
        return self.match_candidates_to_jobs(
            candidate_profile,
            job_profiles,
            accessibility_profiles=accessibility_profiles,
        )
