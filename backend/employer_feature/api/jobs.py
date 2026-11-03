from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.dependencies import require_role
from app.db.session import get_db
from app.models.user import UserRole
from app.models.employer_profile import EmployerProfile
from app.api.v1.endpoints.employers import get_employer_profile
from ..schemas.job import JobCreate, JobUpdate, JobResponse
from ..services.job import (
    create_job,
    list_jobs,
    get_job,
    update_job,
    delete_job,
    list_public_jobs,
    get_public_job,
)

router = APIRouter()


# -------------------------------------------------------------
# Employer Job Management Endpoints
# -------------------------------------------------------------


@router.post(
    "/employers/me/jobs",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new job listing for current employer",
)
def create_job_endpoint(
    payload: JobCreate,
    db: Session = Depends(get_db),
    profile: EmployerProfile = Depends(get_employer_profile),
) -> JobResponse:
    return create_job(db, profile.id, payload)


@router.get(
    "/employers/me/jobs",
    response_model=list[JobResponse],
    summary="List all job listings for current employer",
)
def list_my_jobs_endpoint(
    db: Session = Depends(get_db),
    profile: EmployerProfile = Depends(get_employer_profile),
) -> list[JobResponse]:
    return list_jobs(db, profile.id)


@router.get(
    "/employers/me/jobs/{job_id}",
    response_model=JobResponse,
    summary="Get single job listing for current employer",
)
def get_my_job_endpoint(
    job_id: UUID,
    db: Session = Depends(get_db),
    profile: EmployerProfile = Depends(get_employer_profile),
) -> JobResponse:
    job = get_job(db, profile.id, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or access denied.",
        )
    return job


@router.patch(
    "/employers/me/jobs/{job_id}",
    response_model=JobResponse,
    summary="Update a job listing",
)
def update_my_job_endpoint(
    job_id: UUID,
    payload: JobUpdate,
    db: Session = Depends(get_db),
    profile: EmployerProfile = Depends(get_employer_profile),
) -> JobResponse:
    job = update_job(db, profile.id, job_id, payload)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or access denied.",
        )
    return job


@router.delete(
    "/employers/me/jobs/{job_id}",
    summary="Delete a job listing",
)
def delete_my_job_endpoint(
    job_id: UUID,
    db: Session = Depends(get_db),
    profile: EmployerProfile = Depends(get_employer_profile),
) -> dict:
    success = delete_job(db, profile.id, job_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or access denied.",
        )
    return {"message": "Job deleted successfully."}


# -------------------------------------------------------------
# Public / Candidate Job Exploration Endpoints
# -------------------------------------------------------------


@router.get(
    "/jobs",
    response_model=list[JobResponse],
    summary="List active jobs publicly",
)
def list_public_jobs_endpoint(
    db: Session = Depends(get_db),
) -> list[JobResponse]:
    return list_public_jobs(db)


@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    summary="Get public job details",
)
def get_public_job_endpoint(
    job_id: UUID,
    db: Session = Depends(get_db),
) -> JobResponse:
    job = get_public_job(db, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or no longer active.",
        )
    return job

