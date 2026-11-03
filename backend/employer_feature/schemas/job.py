from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class JobCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    description: str = Field(..., min_length=10)
    responsibilities: str | None = None
    requirements: str | None = None
    location: str | None = Field(default=None, max_length=200)
    work_mode: str | None = Field(default="Hybrid", max_length=100)
    status: str = Field(default="ACTIVE", max_length=50)
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class JobUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, min_length=10)
    responsibilities: str | None = None
    requirements: str | None = None
    location: str | None = Field(default=None, max_length=200)
    work_mode: str | None = Field(default=None, max_length=100)
    status: str | None = Field(default=None, max_length=50)
    is_active: bool | None = None

    model_config = ConfigDict(from_attributes=True)


class CapabilityItem(BaseModel):
    id: UUID
    category: str
    capability: str
    status: str
    details: str | None = None

    model_config = ConfigDict(from_attributes=True)


class JobResponse(BaseModel):
    id: UUID
    employer_profile_id: UUID
    company_name: str | None = None
    title: str
    description: str
    responsibilities: str | None = None
    requirements: str | None = None
    location: str | None = None
    work_mode: str | None = None
    status: str
    is_active: bool
    applications_count: int = 0
    accommodation_requests_count: int = 0
    accessibility_capabilities: list[CapabilityItem] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
