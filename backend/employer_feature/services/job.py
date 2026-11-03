from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from ..models.job_posting import JobPosting
from ..models.job_application import JobApplication
from ..models.accommodation_request import AccommodationRequest
from ..schemas.job import JobCreate, JobUpdate, JobResponse
from app.models.employer_profile import EmployerProfile


def _to_job_response(job: JobPosting, db: Session) -> JobResponse:
    app_count = db.scalar(
        select(func.count(JobApplication.id)).where(
            JobApplication.job_posting_id == job.id
        )
    ) or 0
    acc_count = db.scalar(
        select(func.count(AccommodationRequest.id)).where(
            AccommodationRequest.job_posting_id == job.id
        )
    ) or 0
    company_name = job.employer.company_name if job.employer else None

    return JobResponse(
        id=job.id,
        employer_profile_id=job.employer_profile_id,
        company_name=company_name,
        title=job.title,
        description=job.description,
        responsibilities=job.responsibilities,
        requirements=job.requirements,
        location=job.location,
        work_mode=job.work_mode,
        status=job.status,
        is_active=job.is_active,
        applications_count=app_count,
        accommodation_requests_count=acc_count,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def create_job(db: Session, employer_id: UUID, payload: JobCreate) -> JobResponse:
    job = JobPosting(
        employer_profile_id=employer_id,
        title=payload.title.strip(),
        description=payload.description.strip(),
        responsibilities=payload.responsibilities.strip() if payload.responsibilities else None,
        requirements=payload.requirements.strip() if payload.requirements else None,
        location=payload.location.strip() if payload.location else None,
        work_mode=payload.work_mode.strip() if payload.work_mode else "Hybrid",
        status=payload.status or "ACTIVE",
        is_active=payload.is_active,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return _to_job_response(job, db)


def list_jobs(db: Session, employer_id: UUID) -> list[JobResponse]:
    jobs = db.scalars(
        select(JobPosting)
        .where(JobPosting.employer_profile_id == employer_id)
        .order_by(JobPosting.created_at.desc())
    ).all()
    return [_to_job_response(j, db) for j in jobs]


def get_job(db: Session, employer_id: UUID, job_id: UUID) -> JobResponse | None:
    job = db.scalar(
        select(JobPosting).where(
            JobPosting.id == job_id,
            JobPosting.employer_profile_id == employer_id,
        )
    )
    return _to_job_response(job, db) if job else None


def update_job(
    db: Session, employer_id: UUID, job_id: UUID, payload: JobUpdate
) -> JobResponse | None:
    job = db.scalar(
        select(JobPosting).where(
            JobPosting.id == job_id,
            JobPosting.employer_profile_id == employer_id,
        )
    )
    if not job:
        return None

    if payload.title is not None:
        job.title = payload.title.strip()
    if payload.description is not None:
        job.description = payload.description.strip()
    if payload.responsibilities is not None:
        job.responsibilities = payload.responsibilities.strip() if payload.responsibilities else None
    if payload.requirements is not None:
        job.requirements = payload.requirements.strip() if payload.requirements else None
    if payload.location is not None:
        job.location = payload.location.strip() if payload.location else None
    if payload.work_mode is not None:
        job.work_mode = payload.work_mode.strip() if payload.work_mode else None
    if payload.status is not None:
        job.status = payload.status
        job.is_active = (payload.status == "ACTIVE")
    if payload.is_active is not None:
        job.is_active = payload.is_active

    db.add(job)
    db.commit()
    db.refresh(job)
    return _to_job_response(job, db)


def delete_job(db: Session, employer_id: UUID, job_id: UUID) -> bool:
    job = db.scalar(
        select(JobPosting).where(
            JobPosting.id == job_id,
            JobPosting.employer_profile_id == employer_id,
        )
    )
    if not job:
        return False
    db.delete(job)
    db.commit()
    return True


def list_public_jobs(db: Session) -> list[JobResponse]:
    jobs = db.scalars(
        select(JobPosting)
        .where(JobPosting.is_active.is_(True), JobPosting.status == "ACTIVE")
        .order_by(JobPosting.created_at.desc())
    ).all()
    return [_to_job_response(j, db) for j in jobs]


def get_public_job(db: Session, job_id: UUID) -> JobResponse | None:
    job = db.scalar(
        select(JobPosting).where(
            JobPosting.id == job_id,
            JobPosting.is_active.is_(True),
        )
    )
    return _to_job_response(job, db) if job else None
