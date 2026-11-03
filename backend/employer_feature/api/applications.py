from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.employer_profile import EmployerProfile
from app.models.candidate_profile import CandidateProfile
from app.api.v1.endpoints.employers import get_employer_profile
from app.api.v1.endpoints.candidates import get_candidate_profile
from ..schemas.application import (
    JobApplicationCreate,
    JobApplicationStatusUpdate,
    JobApplicationResponse,
)
from ..services.application import (
    apply_for_job,
    list_employer_applications,
    get_employer_application,
    update_application_status,
    list_candidate_applications,
)

router = APIRouter()


# -------------------------------------------------------------
# Candidate Application Endpoints
# -------------------------------------------------------------


@router.post(
    "/candidates/me/jobs/{job_id}/apply",
    response_model=JobApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Candidate applies for a job listing",
)
def candidate_apply_job_endpoint(
    job_id: UUID,
    payload: JobApplicationCreate,
    db: Session = Depends(get_db),
    candidate: CandidateProfile = Depends(get_candidate_profile),
) -> JobApplicationResponse:
    try:
        return apply_for_job(db, candidate.id, job_id, payload)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        )


@router.get(
    "/candidates/me/applications",
    response_model=list[JobApplicationResponse],
    summary="Candidate lists their own job applications",
)
def candidate_list_applications_endpoint(
    db: Session = Depends(get_db),
    candidate: CandidateProfile = Depends(get_candidate_profile),
) -> list[JobApplicationResponse]:
    return list_candidate_applications(db, candidate.id)


# -------------------------------------------------------------
# Employer Application Review Endpoints (Strictly Scoped)
# -------------------------------------------------------------


@router.get(
    "/employers/me/applications",
    response_model=list[JobApplicationResponse],
    summary="List applications for current employer's jobs only",
)
def employer_list_applications_endpoint(
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    job_id: Annotated[UUID | None, Query()] = None,
    db: Session = Depends(get_db),
    profile: EmployerProfile = Depends(get_employer_profile),
) -> list[JobApplicationResponse]:
    # Defensive check if passed as Query object
    clean_status = status_filter if isinstance(status_filter, str) else None
    clean_job_id = job_id if isinstance(job_id, UUID) else None
    return list_employer_applications(
        db, profile.id, status_filter=clean_status, job_id_filter=clean_job_id
    )


@router.get(
    "/employers/me/applications/{application_id}",
    response_model=JobApplicationResponse,
    summary="Get single application detail for employer's job",
)
def employer_get_application_endpoint(
    application_id: UUID,
    db: Session = Depends(get_db),
    profile: EmployerProfile = Depends(get_employer_profile),
) -> JobApplicationResponse:
    app_res = get_employer_application(db, profile.id, application_id)
    if not app_res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found or access denied.",
        )
    return app_res


@router.patch(
    "/employers/me/applications/{application_id}/status",
    response_model=JobApplicationResponse,
    summary="Update application status (Reviewing, Shortlisted, Interview, Rejected, Accepted)",
)
def employer_update_application_status_endpoint(
    application_id: UUID,
    payload: JobApplicationStatusUpdate,
    db: Session = Depends(get_db),
    profile: EmployerProfile = Depends(get_employer_profile),
) -> JobApplicationResponse:
    app_res = update_application_status(
        db, profile.id, application_id, payload.status
    )
    if not app_res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found or access denied.",
        )
    return app_res
