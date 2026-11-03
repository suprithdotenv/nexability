from pydantic import BaseModel, ConfigDict
from app.schemas.employer import EmployerProfileResponse, EmployerAccessibilityResponse
from .job import JobResponse
from .application import JobApplicationResponse
from .accommodation import AccommodationResponse


class EmployerDashboardStats(BaseModel):
    total_jobs: int = 0
    active_jobs: int = 0
    total_applications: int = 0
    pending_applications: int = 0
    pending_accommodations: int = 0
    verification_status: str = "PENDING"
    profile_complete: bool = False
    accessibility_capabilities_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class EmployerDashboardSummary(BaseModel):
    stats: EmployerDashboardStats
    profile: EmployerProfileResponse
    recent_jobs: list[JobResponse] = []
    recent_applications: list[JobApplicationResponse] = []
    recent_accommodations: list[AccommodationResponse] = []
    accessibility_capabilities: list[EmployerAccessibilityResponse] = []

    model_config = ConfigDict(from_attributes=True)

