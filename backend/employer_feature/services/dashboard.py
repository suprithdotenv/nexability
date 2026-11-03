from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from ..models.job_posting import JobPosting
from ..models.job_application import JobApplication
from ..models.accommodation_request import AccommodationRequest
from .job import list_jobs
from .application import list_employer_applications
from .accommodation import list_employer_accommodations
from ..schemas.dashboard import EmployerDashboardStats, EmployerDashboardSummary
from app.models.employer_profile import EmployerProfile
from app.models.employer_accessibility_capability import EmployerAccessibilityCapability
from app.schemas.employer import EmployerProfileResponse, EmployerAccessibilityResponse
from app.models.user import User


def get_dashboard_summary(
    db: Session,
    profile: EmployerProfile,
    user: User,
) -> EmployerDashboardSummary:
    total_jobs = db.scalar(
        select(func.count(JobPosting.id)).where(
            JobPosting.employer_profile_id == profile.id
        )
    ) or 0

    active_jobs = db.scalar(
        select(func.count(JobPosting.id)).where(
            JobPosting.employer_profile_id == profile.id,
            JobPosting.is_active.is_(True),
        )
    ) or 0

    total_apps = db.scalar(
        select(func.count(JobApplication.id))
        .join(JobPosting, JobApplication.job_posting_id == JobPosting.id)
        .where(JobPosting.employer_profile_id == profile.id)
    ) or 0

    pending_apps = db.scalar(
        select(func.count(JobApplication.id))
        .join(JobPosting, JobApplication.job_posting_id == JobPosting.id)
        .where(
            JobPosting.employer_profile_id == profile.id,
            JobApplication.status == "APPLIED",
        )
    ) or 0

    pending_acc = db.scalar(
        select(func.count(AccommodationRequest.id))
        .join(JobPosting, AccommodationRequest.job_posting_id == JobPosting.id)
        .where(
            JobPosting.employer_profile_id == profile.id,
            AccommodationRequest.status == "PENDING",
        )
    ) or 0

    capabilities = db.scalars(
        select(EmployerAccessibilityCapability)
        .where(EmployerAccessibilityCapability.employer_profile_id == profile.id)
        .order_by(EmployerAccessibilityCapability.created_at.asc())
    ).all()

    profile_complete = bool(
        profile.company_name
        and profile.full_name
        and profile.website
        and profile.phone
    )

    stats = EmployerDashboardStats(
        total_jobs=total_jobs,
        active_jobs=active_jobs,
        total_applications=total_apps,
        pending_applications=pending_apps,
        pending_accommodations=pending_acc,
        verification_status=profile.verification_status,
        profile_complete=profile_complete,
        accessibility_capabilities_count=len(capabilities),
    )

    profile_res = EmployerProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        email=user.email,
        full_name=profile.full_name,
        company_name=profile.company_name,
        email_domain=profile.email_domain,
        website=profile.website,
        phone=profile.phone,
        verification_status=profile.verification_status,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )

    recent_jobs = list_jobs(db, profile.id)[:5]
    recent_apps = list_employer_applications(db, profile.id)[:5]
    recent_acc = list_employer_accommodations(db, profile.id)[:5]
    cap_res = [EmployerAccessibilityResponse.model_validate(c) for c in capabilities]

    return EmployerDashboardSummary(
        stats=stats,
        profile=profile_res,
        recent_jobs=recent_jobs,
        recent_applications=recent_apps,
        recent_accommodations=recent_acc,
        accessibility_capabilities=cap_res,
    )

