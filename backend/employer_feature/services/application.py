from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models.job_posting import JobPosting
from ..models.job_application import JobApplication
from ..schemas.application import JobApplicationCreate, JobApplicationResponse
from app.models.candidate_profile import CandidateProfile
from app.models.candidate_declaration import CandidateDeclaration
from app.models.user import User


def _to_application_response(app: JobApplication, db: Session) -> JobApplicationResponse:
    candidate = app.candidate_profile
    user = db.scalar(select(User).where(User.id == candidate.user_id)) if candidate else None

    # Fetch voluntary declaration if exists and active
    declaration = db.scalar(
        select(CandidateDeclaration).where(
            CandidateDeclaration.candidate_profile_id == candidate.id,
            CandidateDeclaration.withdrawn_at.is_(None),
        ).order_by(CandidateDeclaration.accepted_at.desc())
    ) if candidate else None

    company_name = app.job_posting.employer.company_name if (app.job_posting and app.job_posting.employer) else None

    return JobApplicationResponse(
        id=app.id,
        job_posting_id=app.job_posting_id,
        job_title=app.job_posting.title if app.job_posting else "Unknown Job",
        company_name=company_name,
        candidate_profile_id=app.candidate_profile_id,
        candidate_name=candidate.full_name if candidate else "Anonymous",
        candidate_email=user.email if user else None,
        candidate_phone=candidate.phone if candidate else None,
        status=app.status,
        cover_note=app.cover_note,
        has_declaration=declaration is not None,
        declaration_version=declaration.declaration_version if declaration else None,
        declaration_accepted_at=declaration.accepted_at if declaration else None,
        created_at=app.created_at,
        updated_at=app.updated_at,
    )


def apply_for_job(
    db: Session,
    candidate_profile_id: UUID,
    job_id: UUID,
    payload: JobApplicationCreate,
) -> JobApplicationResponse:
    job = db.scalar(select(JobPosting).where(JobPosting.id == job_id, JobPosting.is_active.is_(True)))
    if not job:
        raise ValueError("Job not found or inactive")

    # Prevent duplicate applications
    existing = db.scalar(
        select(JobApplication).where(
            JobApplication.job_posting_id == job_id,
            JobApplication.candidate_profile_id == candidate_profile_id,
        )
    )
    if existing:
        return _to_application_response(existing, db)

    application = JobApplication(
        job_posting_id=job_id,
        candidate_profile_id=candidate_profile_id,
        status="APPLIED",
        cover_note=payload.cover_note.strip() if payload.cover_note else None,
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return _to_application_response(application, db)


def list_employer_applications(
    db: Session,
    employer_id: UUID,
    status_filter: str | None = None,
    job_id_filter: UUID | None = None,
) -> list[JobApplicationResponse]:
    # Strictly join JobPosting and ensure JobPosting.employer_profile_id == employer_id
    query = (
        select(JobApplication)
        .join(JobPosting, JobApplication.job_posting_id == JobPosting.id)
        .where(JobPosting.employer_profile_id == employer_id)
        .order_by(JobApplication.created_at.desc())
    )
    if status_filter:
        query = query.where(JobApplication.status == status_filter)
    if job_id_filter:
        query = query.where(JobApplication.job_posting_id == job_id_filter)

    applications = db.scalars(query).all()
    return [_to_application_response(app, db) for app in applications]


def get_employer_application(
    db: Session,
    employer_id: UUID,
    application_id: UUID,
) -> JobApplicationResponse | None:
    query = (
        select(JobApplication)
        .join(JobPosting, JobApplication.job_posting_id == JobPosting.id)
        .where(
            JobApplication.id == application_id,
            JobPosting.employer_profile_id == employer_id,
        )
    )
    app = db.scalar(query)
    return _to_application_response(app, db) if app else None


def update_application_status(
    db: Session,
    employer_id: UUID,
    application_id: UUID,
    new_status: str,
) -> JobApplicationResponse | None:
    query = (
        select(JobApplication)
        .join(JobPosting, JobApplication.job_posting_id == JobPosting.id)
        .where(
            JobApplication.id == application_id,
            JobPosting.employer_profile_id == employer_id,
        )
    )
    app = db.scalar(query)
    if not app:
        return None

    app.status = new_status
    db.add(app)
    db.commit()
    db.refresh(app)
    return _to_application_response(app, db)


def list_candidate_applications(
    db: Session,
    candidate_profile_id: UUID,
) -> list[JobApplicationResponse]:
    apps = db.scalars(
        select(JobApplication)
        .where(JobApplication.candidate_profile_id == candidate_profile_id)
        .order_by(JobApplication.created_at.desc())
    ).all()
    return [_to_application_response(app, db) for app in apps]

