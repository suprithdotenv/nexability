from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.employer_profile import EmployerProfile
from app.models.candidate_profile import CandidateProfile
from app.api.v1.endpoints.employers import get_employer_profile
from app.api.v1.endpoints.candidates import get_candidate_profile
from ..schemas.accommodation import (
    AccommodationCreate,
    AccommodationResponseUpdate,
    AccommodationResponse,
)
from ..services.accommodation import (
    create_accommodation_request,
    list_employer_accommodations,
    get_employer_accommodation,
    update_accommodation_response,
    list_candidate_accommodations,
)

router = APIRouter()


# -------------------------------------------------------------
# Candidate Accommodation Request Endpoints
# -------------------------------------------------------------


@router.post(
    "/candidates/me/jobs/{job_id}/accommodations",
    response_model=AccommodationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Candidate requests accommodation for a job",
)
def candidate_request_accommodation_endpoint(
    job_id: UUID,
    payload: AccommodationCreate,
    db: Session = Depends(get_db),
    candidate: CandidateProfile = Depends(get_candidate_profile),
) -> AccommodationResponse:
    try:
        return create_accommodation_request(db, candidate.id, job_id, payload)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        )


@router.get(
    "/candidates/me/accommodations",
    response_model=list[AccommodationResponse],
    summary="Candidate lists their own accommodation requests",
)
def candidate_list_accommodations_endpoint(
    db: Session = Depends(get_db),
    candidate: CandidateProfile = Depends(get_candidate_profile),
) -> list[AccommodationResponse]:
    return list_candidate_accommodations(db, candidate.id)


# -------------------------------------------------------------
# Employer Accommodation Inbox Endpoints (Strictly Scoped)
# -------------------------------------------------------------


@router.get(
    "/employers/me/accommodations",
    response_model=list[AccommodationResponse],
    summary="Employer inbox: list accommodation requests for employer's jobs only",
)
def employer_list_accommodations_endpoint(
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    db: Session = Depends(get_db),
    profile: EmployerProfile = Depends(get_employer_profile),
) -> list[AccommodationResponse]:
    clean_status = status_filter if isinstance(status_filter, str) else None
    return list_employer_accommodations(db, profile.id, status_filter=clean_status)


@router.get(
    "/employers/me/accommodations/{request_id}",
    response_model=AccommodationResponse,
    summary="Get single accommodation request detail",
)
def employer_get_accommodation_endpoint(
    request_id: UUID,
    db: Session = Depends(get_db),
    profile: EmployerProfile = Depends(get_employer_profile),
) -> AccommodationResponse:
    res = get_employer_accommodation(db, profile.id, request_id)
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Accommodation request not found or access denied.",
        )
    return res


@router.patch(
    "/employers/me/accommodations/{request_id}",
    response_model=AccommodationResponse,
    summary="Employer responds to accommodation request (Approve, Decline, Alternative Offered)",
)
def employer_respond_accommodation_endpoint(
    request_id: UUID,
    payload: AccommodationResponseUpdate,
    db: Session = Depends(get_db),
    profile: EmployerProfile = Depends(get_employer_profile),
) -> AccommodationResponse:
    res = update_accommodation_response(
        db,
        profile.id,
        request_id,
        payload.status,
        payload.response_message,
    )
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Accommodation request not found or access denied.",
        )
    return res
