"""
GET /api/v1/candidates/me/matches
==================================

Candidate-facing job-matching endpoint.

Returns job matches ranked primarily and strictly by professional compatibility
(skills, work experience, qualifications, and dense pgvector semantic similarity).

Accessibility requirements are evaluated separately and transparently:
- Exact statuses: AVAILABLE, ON_REQUEST, NOT_SPECIFIED, UNAVAILABLE
- Missing accessibility information does NOT reduce professional match score
- Any accessibility gaps (NOT_SPECIFIED or UNAVAILABLE) are flagged so the
  candidate can submit an accommodation request directly to the employer.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_role
from app.db.session import get_db
from app.models.candidate_profile import CandidateProfile
from app.models.user import User, UserRole
from app.schemas.matches import CandidateMatchResponse
from app.services.matching import (
    MLServiceError,
    MLServiceUnavailableError,
    request_matches,
)

router = APIRouter()


def _get_candidate_profile(
    current_user: User = Depends(require_role(UserRole.CANDIDATE)),
    db: Session = Depends(get_db),
) -> CandidateProfile:
    profile = db.scalar(
        select(CandidateProfile).where(CandidateProfile.user_id == current_user.id)
    )
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate profile not found.",
        )
    return profile


@router.get(
    "/me/matches",
    response_model=CandidateMatchResponse,
    summary="Get ranked job matches for the authenticated candidate",
    description=(
        "Returns jobs ranked strictly by professional compatibility. "
        "Accessibility evaluations are computed independently and visible separately. "
        "Accessibility data is never forwarded to any external LLM."
    ),
)
def get_candidate_matches(
    force_reprocess: bool = Query(
        default=False,
        description="Re-process the résumé even if already processed.",
    ),
    min_threshold: float = Query(
        default=60.0,
        ge=0.0,
        le=100.0,
        description="Minimum professional compatibility score required (default: 60.0%).",
    ),
    profile: CandidateProfile = Depends(_get_candidate_profile),
    db: Session = Depends(get_db),
) -> CandidateMatchResponse:
    candidate_profile_id = str(profile.id)

    try:
        payload = request_matches(
            candidate_profile_id,
            force_reprocess=force_reprocess,
            min_threshold=min_threshold,
        )
    except MLServiceUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except MLServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    if payload.get("status") == "no_resume":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active résumé found. Please upload a résumé before requesting matches.",
        )

    # Filter out any matches below the minimum professional match threshold
    from app.models.employer_profile import EmployerProfile
    import uuid as _uuid
    raw_matches = payload.get("top_matches", [])
    qualifying_matches = [
        m for m in raw_matches
        if (m.get("professional_match_score") or 0.0) >= min_threshold
    ]

    # Enrich true company names and assign 1-based ranks
    for idx, m in enumerate(qualifying_matches, start=1):
        m["rank"] = idx
        emp_id = m.get("employer_id") or (m.get("company_info") or {}).get("employer_id")
        if emp_id:
            try:
                emp_uuid = _uuid.UUID(str(emp_id))
                emp_prof = db.scalar(select(EmployerProfile).where(EmployerProfile.id == emp_uuid))
                if emp_prof:
                    m["company_info"] = {
                        "employer_id": str(emp_prof.id),
                        "company_name": emp_prof.company_name,
                        "company_domain": emp_prof.email_domain,
                        "website": emp_prof.website,
                        "phone": emp_prof.phone,
                        "verification_status": emp_prof.verification_status,
                    }
            except Exception:
                pass

    payload["top_matches"] = qualifying_matches
    payload["match_count"] = len(qualifying_matches)
    if len(qualifying_matches) == 0 and payload.get("status") not in ("no_resume", "no_jobs_available"):
        payload["status"] = "no_qualifying_matches"

    return CandidateMatchResponse(**payload)
