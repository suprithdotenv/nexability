"""
NexAbility ML — Matching Service
=================================

Standalone FastAPI application that provides candidate-to-job matchmaking.
Ranks candidates strictly by professional compatibility (skills, experience,
qualifications, and semantic chunk embeddings).

Accessibility is evaluated separately:
- Exact statuses: AVAILABLE, ON_REQUEST, NOT_SPECIFIED, UNAVAILABLE
- NOT_SPECIFIED is NOT treated as UNAVAILABLE
- Missing accessibility information never reduces professional match score
"""
from __future__ import annotations

import logging
import os
from typing import Any
from uuid import UUID

from fastapi import FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from nexability_ml.api_client import InternalMLClient
from nexability_ml.config import (
    EMBEDDING_DIM,
    EMBEDDING_MODEL,
    GROQ_MODEL,
)
from nexability_ml.embeddings import create_embedding_model, create_tokenizer
from nexability_ml.pipeline import NexAbilityMLPipeline
from nexability_ml.ranking import (
    TOP_K_MATCHES,
    rank_and_select,
)

logger = logging.getLogger(__name__)

# In-memory document profile & accessibility caches to ensure millisecond response times
_job_profiles_cache: dict[str, dict[str, Any]] = {}
_resume_profiles_cache: dict[str, dict[str, Any]] = {}
_employer_accessibility_cache: dict[str, dict[str, Any]] = {}

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="NexAbility ML Matching Service",
    version="2.0.0",
    description=(
        "Job matchmaking service ranked primarily by professional compatibility. "
        "Accessibility evaluations are computed independently and visible separately."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://.*$",
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Shared pipeline (lazy-loaded once per process)
# ---------------------------------------------------------------------------
_pipeline: NexAbilityMLPipeline | None = None


def _get_pipeline() -> NexAbilityMLPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = NexAbilityMLPipeline(
            embedding_model=create_embedding_model(),
            tokenizer=create_tokenizer(),
        )
    return _pipeline


def _get_client() -> InternalMLClient:
    base_url = os.environ.get("NEXABILITY_BACKEND_URL", "http://localhost:8000")
    api_key = os.environ.get("NEXABILITY_INTERNAL_ML_API_KEY", "ml-internal-secret-token")
    return InternalMLClient(base_url, api_key=api_key)


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------

def _get_service_key() -> str:
    return os.environ.get("NEXABILITY_INTERNAL_ML_API_KEY", "ml-internal-secret-token")


def _require_service_key(
    x_internal_service_key: str | None = Header(None, alias="X-Internal-Service-Key"),
) -> None:
    configured_key = _get_service_key()
    if configured_key and x_internal_service_key != configured_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Internal-Service-Key.",
        )


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class ScoresSchema(BaseModel):
    """Component scores block."""

    professional_match_score: float = Field(
        description="Professional match score 0–100."
    )
    accessibility_compatibility: float = Field(
        default=100.0, description="Informational accessibility compatibility 0–100."
    )
    ranking_score: float = Field(
        description="Final ranking score, equal to professional_match_score."
    )
    accessibility_note: str = Field(
        default="Evaluated separately", description="How accessibility data was used."
    )
    ranking_formula: str = Field(
        default="Ranked strictly by professional compatibility. Accessibility evaluated separately.",
        description="Human-readable ranking formula used.",
    )


class JobMatchResult(BaseModel):
    """Single ranked job match result."""

    rank: int
    job_id: str | None
    employer_id: str | None = None
    job_title: str | None = None
    company_info: dict[str, Any] = Field(default_factory=dict)
    job_info: dict[str, Any] = Field(default_factory=dict)
    professional_match_score: float = 0.0
    scores: ScoresSchema
    professional_match: dict[str, Any]
    accessibility_match: dict[str, Any]
    accessibility_requirements: list[dict[str, Any]] = Field(default_factory=list)
    accessibility_gaps: list[dict[str, Any]] = Field(default_factory=list)
    can_request_accommodation: bool = False


class MatchResponse(BaseModel):
    """Ranked match results for a candidate."""

    candidate_id: str
    status: str
    match_count: int
    ranking_formula: str
    ranking_strategy: str = "professional_compatibility_first"
    top_matches: list[JobMatchResult]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_candidate_id(raw: str | None) -> UUID:
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Candidate-Id header is required.",
        )
    try:
        return UUID(raw.strip())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Candidate-Id must be a valid UUID.",
        ) from None


def _find_active_resume(
    client: InternalMLClient, candidate_id: UUID
) -> dict[str, Any] | None:
    try:
        queue = client.list_pending_documents()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Backend ML service is unreachable: {exc}",
        ) from exc

    active_resumes = queue.get("active_resumes", [])
    for resume in active_resumes:
        if str(resume.get("owner_id")) == str(candidate_id):
            return resume
    return None


def _fetch_all_job_profiles(
    client: InternalMLClient,
) -> list[dict[str, Any]]:
    try:
        queue = client.list_pending_documents()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Backend ML service is unreachable: {exc}",
        ) from exc

    job_docs = queue.get("pending_job_documents", [])
    return job_docs


def _process_and_profile_resume(
    client: InternalMLClient,
    pipeline: NexAbilityMLPipeline,
    resume_meta: dict[str, Any],
    candidate_id: UUID,
    force_reprocess: bool = False,
) -> dict[str, Any]:
    resume_id = str(resume_meta.get("document_id", ""))
    if not force_reprocess and resume_id in _resume_profiles_cache:
        return _resume_profiles_cache[resume_id]

    if not force_reprocess and resume_meta.get("parsed_profile"):
        structured = dict(resume_meta["parsed_profile"])
        if "source_text" not in structured or not structured["source_text"]:
            structured["source_text"] = " ".join(
                str(structured.get(k) or "")
                for k in ("professional_summary", "skills", "experience", "education")
            )
        _resume_profiles_cache[resume_id] = structured
        return structured

    try:
        document_bytes = client.get_resume_content(resume_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not download résumé: {exc}",
        ) from exc

    if not document_bytes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Active résumé binary is empty.",
        )

    result = pipeline.process_resume_document(
        document_bytes=document_bytes,
        filename=str(resume_meta.get("original_filename", "resume")),
        candidate_id=str(candidate_id),
        content_type=str(resume_meta.get("mime_type", "")),
    )

    structured = result.get("structured_profile", {})
    structured["source_text"] = result.get("safe_source_text") or ""
    _resume_profiles_cache[resume_id] = structured
    return structured


def _build_job_profile_from_bytes(
    client: InternalMLClient,
    pipeline: NexAbilityMLPipeline,
    job_meta: dict[str, Any],
    force_reprocess: bool = False,
) -> dict[str, Any] | None:
    doc_id = str(job_meta.get("document_id", ""))
    employer_id = str(job_meta.get("owner_id", ""))

    if not force_reprocess and doc_id in _job_profiles_cache:
        return _job_profiles_cache[doc_id]

    if not force_reprocess and job_meta.get("parsed_profile"):
        profile = dict(job_meta["parsed_profile"])
        profile["job_id"] = doc_id
        profile["employer_id"] = employer_id
        profile["job_title"] = profile.get("job_title") or job_meta.get("original_filename", "Software Role")
        _job_profiles_cache[doc_id] = profile
        return profile

    try:
        doc_bytes = client.get_job_document_content(doc_id)
    except Exception:
        logger.warning("Could not download job document %s; skipping.", doc_id)
        return None

    if not doc_bytes:
        return None

    try:
        result = pipeline.process_job_document(
            document_bytes=doc_bytes,
            filename=str(job_meta.get("original_filename", "job.pdf")),
            employer_id=employer_id,
            job_id=doc_id,
            content_type=str(job_meta.get("mime_type", "")),
        )
    except Exception:
        logger.warning("Job document processing failed for %s; skipping.", doc_id)
        return None

    if result.get("document_status") != "processed":
        return None

    profile = result.get("structured_profile", {})
    profile["job_id"] = doc_id
    profile["employer_id"] = employer_id
    profile["job_title"] = profile.get("job_title") or job_meta.get("original_filename", "Software Role")
    _job_profiles_cache[doc_id] = profile
    return profile


def _get_employer_accessibility(
    client: InternalMLClient,
    employer_id: str,
) -> dict[str, Any]:
    if employer_id in _employer_accessibility_cache:
        return _employer_accessibility_cache[employer_id]
    try:
        employer_profile = client.get_employer_accessibility_profile(employer_id)
    except Exception:
        employer_profile = {"profile_completed": None, "capabilities": []}
    _employer_accessibility_cache[employer_id] = employer_profile
    return employer_profile


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@app.get(
    "/api/v1/ml/matches",
    response_model=MatchResponse,
    summary="Get top ranked job matches for a candidate",
)
def get_matches(
    x_internal_service_key: str | None = Header(None, alias="X-Internal-Service-Key"),
    x_candidate_id: str | None = Header(None, alias="X-Candidate-Id"),
    force_reprocess: bool = Query(False, description="Re-process résumé even if cached"),
    min_threshold: float = Query(60.0, description="Minimum professional compatibility score required"),
) -> MatchResponse:
    # 1. Authorise
    _require_service_key(x_internal_service_key)
    candidate_id = _parse_candidate_id(x_candidate_id)

    client = _get_client()
    pipeline = _get_pipeline()

    # 2. Find the candidate's active résumé
    resume_meta = _find_active_resume(client, candidate_id)
    if resume_meta is None:
        return MatchResponse(
            candidate_id=str(candidate_id),
            status="no_resume",
            match_count=0,
            ranking_formula="Ranked strictly by professional compatibility. Accessibility evaluated separately.",
            top_matches=[],
        )

    # 3. Process the résumé
    candidate_profile = _process_and_profile_resume(
        client, pipeline, resume_meta, candidate_id, force_reprocess=force_reprocess
    )

    # 4. Get candidate accessibility preferences once
    try:
        cand_preferences = client.get_candidate_accessibility_preferences(str(candidate_id))
    except Exception:
        cand_preferences = []

    # 5. Get all job documents and build job profiles
    job_metas = _fetch_all_job_profiles(client)
    if not job_metas:
        return MatchResponse(
            candidate_id=str(candidate_id),
            status="no_jobs_available",
            match_count=0,
            ranking_formula="Ranked strictly by professional compatibility. Accessibility evaluated separately.",
            top_matches=[],
        )

    job_profiles: list[dict[str, Any]] = []
    for job_meta in job_metas:
        profile = _build_job_profile_from_bytes(
            client, pipeline, job_meta, force_reprocess=force_reprocess
        )
        if profile is not None:
            job_profiles.append(profile)

    if not job_profiles:
        return MatchResponse(
            candidate_id=str(candidate_id),
            status="no_jobs_available",
            match_count=0,
            ranking_formula="Ranked strictly by professional compatibility. Accessibility evaluated separately.",
            top_matches=[],
        )

    # 6. Match against each job
    from nexability_ml.matcher import _accessibility_match, _professional_match

    # Extract candidate skills for fallback skill scoring
    cand_skill_names = {
        (s.get("name") if isinstance(s, dict) else str(s)).strip().lower()
        for s in (candidate_profile.get("skills") or [])
        if s
    }

    all_results: list[dict[str, Any]] = []
    for job_profile in job_profiles:
        employer_id = str(job_profile.get("employer_id", ""))

        prof_match = _professional_match(candidate_profile, job_profile)
        
        # Ensure realistic professional score from skills overlap if evidence score unavailable
        prof_evidence = prof_match.get("professional_evidence_score", {})
        if prof_evidence.get("status") != "available" or prof_evidence.get("value") is None:
            job_skills = [
                str(s).lower()
                for s in (job_profile.get("required_skills") or job_profile.get("skills") or [])
            ]
            if job_skills:
                import re
                matched = [
                    s for s in job_skills
                    if any(cs == s or bool(re.search(r"\b" + re.escape(cs) + r"\b", s)) or bool(re.search(r"\b" + re.escape(s) + r"\b", cs)) for cs in cand_skill_names if len(cs) > 1)
                ]
                computed_prof = round((len(matched) / len(job_skills)) * 100.0, 2)
            else:
                computed_prof = 0.0
            prof_match["professional_evidence_score"] = {
                "status": "available",
                "value": computed_prof,
            }

        emp_accessibility = _get_employer_accessibility(client, employer_id)
        acc_match = _accessibility_match(
            cand_preferences,
            emp_accessibility.get("capabilities", []),
            employer_profile_completed=emp_accessibility.get("profile_completed"),
        )

        all_results.append(
            {
                "job_id": job_profile.get("job_id"),
                "employer_id": employer_id,
                "job_title": job_profile.get("job_title"),
                "company_name": emp_accessibility.get("company_name") or "Innovative Technology Employer",
                "verification_status": emp_accessibility.get("verification_status") or "VERIFIED",
                "professional_match": prof_match,
                "accessibility_match": acc_match,
            }
        )

    # 7. Rank strictly by professional compatibility (filtered by minimum threshold)
    ranked = rank_and_select(all_results, top_k=TOP_K_MATCHES, min_threshold=min_threshold)

    # 8. Build normalized response with exact statuses
    top_matches: list[JobMatchResult] = []
    for rank_position, match in enumerate(ranked, start=1):
        scores = match["scores"]
        acc_match = match.get("accessibility_match", {})
        raw_reqs = acc_match.get("requirements", [])
        
        norm_requirements = []
        for r in raw_reqs:
            raw_st = str(r.get("employer_status") or r.get("status") or "NOT_SPECIFIED").upper()
            if raw_st in ("AVAILABLE", "CONFIRMED", "YES"):
                final_st = "AVAILABLE"
                is_gap = False
                details = r.get("details") or f"Officially supported by employer: {r.get('evidence') or r.get('requirement')}"
            elif raw_st in ("ON_REQUEST", "UNVERIFIED", "UPON_REQUEST"):
                final_st = "ON_REQUEST"
                is_gap = False
                details = r.get("details") or f"Available upon request: {r.get('evidence') or r.get('requirement')}"
            elif raw_st in ("UNAVAILABLE", "MISSING", "NO"):
                final_st = "UNAVAILABLE"
                is_gap = True
                details = r.get("details") or f"Employer confirmed facility is currently unavailable: {r.get('requirement')}"
            else:
                final_st = "NOT_SPECIFIED"
                is_gap = True
                details = r.get("details") or f"Employer has not specified workplace information for {r.get('requirement')}"

            pref_text = r.get("preference") or r.get("requirement") or "Workplace Accommodation"
            norm_requirements.append({
                "preference": pref_text,
                "requirement": pref_text,
                "employer_status": final_st,
                "status": final_st,
                "employer_capability": r.get("employer_capability") or r.get("evidence"),
                "details": details,
                "is_gap": is_gap,
                "can_request": is_gap,
            })

        acc_gaps = [r for r in norm_requirements if r["is_gap"]]

        top_matches.append(
            JobMatchResult(
                rank=rank_position,
                job_id=match.get("job_id"),
                employer_id=match.get("employer_id"),
                job_title=match.get("job_title"),
                company_info={
                    "employer_id": match.get("employer_id"),
                    "company_name": match.get("company_name") or "Innovative Technology Employer",
                    "verification_status": match.get("verification_status") or "VERIFIED",
                },
                job_info={
                    "job_id": match.get("job_id"),
                    "job_title": match.get("job_title"),
                    "overview": f"Professional position: {match.get('job_title')}",
                },
                professional_match_score=scores["professional_match_score"],
                scores=ScoresSchema(
                    accessibility_compatibility=scores["accessibility_compatibility"],
                    professional_match_score=scores["professional_match_score"],
                    ranking_score=scores["ranking_score"],
                    accessibility_note=scores["accessibility_note"],
                    ranking_formula=scores["ranking_formula"],
                ),
                professional_match=match.get("professional_match", {}),
                accessibility_match={
                    "requirements": norm_requirements,
                    "gaps": acc_gaps,
                },
                accessibility_requirements=norm_requirements,
                accessibility_gaps=acc_gaps,
                can_request_accommodation=len(acc_gaps) > 0,
            )
        )

    formula = "Ranked strictly by professional compatibility. Accessibility evaluated separately."

    return MatchResponse(
        candidate_id=str(candidate_id),
        status="match_found" if top_matches else "no_qualifying_matches",
        match_count=len(top_matches),
        ranking_formula=formula,
        ranking_strategy="professional_compatibility_first",
        top_matches=top_matches,
    )


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", include_in_schema=False)
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "embedding_model": EMBEDDING_MODEL,
        "embedding_dim": str(EMBEDDING_DIM),
        "groq_model": GROQ_MODEL,
        "ranking_logic": "professional_compatibility_first",
    }
