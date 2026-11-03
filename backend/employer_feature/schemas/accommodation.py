from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class AccommodationCreate(BaseModel):
    facility: str = Field(..., min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=2000)


class AccommodationResponseUpdate(BaseModel):
    status: str = Field(
        ..., max_length=50
    )  # APPROVED, DECLINED, ALTERNATIVE_OFFERED, PENDING
    response_message: str | None = Field(default=None, max_length=2000)


class AccommodationResponse(BaseModel):
    id: UUID
    job_posting_id: UUID
    job_title: str
    company_name: str | None = None
    candidate_profile_id: UUID
    candidate_name: str
    facility: str
    description: str | None = None
    status: str
    response_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

