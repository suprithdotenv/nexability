from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class JobApplicationCreate(BaseModel):
    cover_note: str | None = Field(default=None, max_length=2000)


class JobApplicationStatusUpdate(BaseModel):
    status: str = Field(..., max_length=50)  # APPLIED, REVIEWING, SHORTLISTED, REJECTED, ACCEPTED


class JobApplicationResponse(BaseModel):
    id: UUID
    job_posting_id: UUID
    job_title: str
    company_name: str | None = None
    candidate_profile_id: UUID
    candidate_name: str
    candidate_email: str | None = None
    candidate_phone: str | None = None
    status: str
    cover_note: str | None = None
    has_declaration: bool = False
    declaration_version: str | None = None
    declaration_accepted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

