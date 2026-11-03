from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.dependencies import require_role
from app.core.config import settings
from app.db.session import get_db
from app.models.user import UserRole
from app.api.v1.endpoints.employers import get_employer_profile
from ..services.job import create_job, get_job, list_jobs, update_job, delete_job
from ..schemas.job import JobCreate, JobUpdate, JobResponse

router = APIRouter(
    prefix="/employers/me/jobs",
    tags=["employer-jobs"],
    dependencies=[Depends(require_role(UserRole.EMPLOYER))],
)

@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job_endpoint(
    payload: JobCreate,
    db: Session = Depends(get_db),
    profile=Depends(get_employer_profile),
):
    return create_job(db, profile.id, payload)

@router.get("/", response_model=list[JobResponse])
def list_jobs_endpoint(
    db: Session = Depends(get_db),
    profile=Depends(get_employer_profile),
):
    return list_jobs(db, profile.id)

@router.get("/{job_id}", response_model=JobResponse)
def get_job_endpoint(
    job_id: str,
    db: Session = Depends(get_db),
    profile=Depends(get_employer_profile),
):
    job = get_job(db, profile.id, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.patch("/{job_id}", response_model=JobResponse)
def update_job_endpoint(
    job_id: str,
    payload: JobUpdate,
    db: Session = Depends(get_db),
    profile=Depends(get_employer_profile),
):
    job = update_job(db, profile.id, job_id, payload)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.delete("/{job_id}", response_model=dict)
def delete_job_endpoint(
    job_id: str,
    db: Session = Depends(get_db),
    profile=Depends(get_employer_profile),
):
    success = delete_job(db, profile.id, job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"detail": "Job deleted"}

