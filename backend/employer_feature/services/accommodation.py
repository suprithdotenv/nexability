from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models.job_posting import JobPosting
from ..models.accommodation_request import AccommodationRequest
from ..schemas.accommodation import AccommodationCreate, AccommodationResponse


def _to_accommodation_response(req: AccommodationRequest) -> AccommodationResponse:
    candidate = req.candidate_profile
    job = req.job_posting
    company_name = job.employer.company_name if (job and job.employer) else None

    return AccommodationResponse(
        id=req.id,
        job_posting_id=req.job_posting_id,
        job_title=job.title if job else "Unknown Job",
        company_name=company_name,
        candidate_profile_id=req.candidate_profile_id,
        candidate_name=candidate.full_name if candidate else "Candidate",
        facility=req.facility,
        description=req.description,
        status=req.status,
        response_message=req.response_message,
        created_at=req.created_at,
        updated_at=req.updated_at,
    )


def create_accommodation_request(
    db: Session,
    candidate_profile_id: UUID,
    job_id: UUID,
    payload: AccommodationCreate,
) -> AccommodationResponse:
    job = db.scalar(select(JobPosting).where(JobPosting.id == job_id, JobPosting.is_active.is_(True)))
    if not job:
        raise ValueError("Job not found or inactive")

    req = AccommodationRequest(
        job_posting_id=job_id,
        candidate_profile_id=candidate_profile_id,
        facility=payload.facility.strip(),
        description=payload.description.strip() if payload.description else None,
        status="PENDING",
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return _to_accommodation_response(req)


def list_employer_accommodations(
    db: Session,
    employer_id: UUID,
    status_filter: str | None = None,
) -> list[AccommodationResponse]:
    query = (
        select(AccommodationRequest)
        .join(JobPosting, AccommodationRequest.job_posting_id == JobPosting.id)
        .where(JobPosting.employer_profile_id == employer_id)
        .order_by(AccommodationRequest.created_at.desc())
    )
    if status_filter:
        query = query.where(AccommodationRequest.status == status_filter)

    items = db.scalars(query).all()
    return [_to_accommodation_response(i) for i in items]


def get_employer_accommodation(
    db: Session,
    employer_id: UUID,
    request_id: UUID,
) -> AccommodationResponse | None:
    query = (
        select(AccommodationRequest)
        .join(JobPosting, AccommodationRequest.job_posting_id == JobPosting.id)
        .where(
            AccommodationRequest.id == request_id,
            JobPosting.employer_profile_id == employer_id,
        )
    )
    req = db.scalar(query)
    return _to_accommodation_response(req) if req else None


def update_accommodation_response(
    db: Session,
    employer_id: UUID,
    request_id: UUID,
    new_status: str,
    response_message: str | None = None,
) -> AccommodationResponse | None:
    query = (
        select(AccommodationRequest)
        .join(JobPosting, AccommodationRequest.job_posting_id == JobPosting.id)
        .where(
            AccommodationRequest.id == request_id,
            JobPosting.employer_profile_id == employer_id,
        )
    )
    req = db.scalar(query)
    if not req:
        return None

    req.status = new_status
    if response_message is not None:
        req.response_message = response_message.strip() if response_message else None

    db.add(req)
    db.commit()
    db.refresh(req)
    return _to_accommodation_response(req)


def list_candidate_accommodations(
    db: Session,
    candidate_profile_id: UUID,
) -> list[AccommodationResponse]:
    items = db.scalars(
        select(AccommodationRequest)
        .where(AccommodationRequest.candidate_profile_id == candidate_profile_id)
        .order_by(AccommodationRequest.created_at.desc())
    ).all()
    return [_to_accommodation_response(i) for i in items]

