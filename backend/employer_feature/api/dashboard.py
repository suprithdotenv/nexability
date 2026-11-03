from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.employer_profile import EmployerProfile
from app.api.dependencies import require_role
from app.api.v1.endpoints.employers import get_employer_profile
from ..schemas.dashboard import EmployerDashboardSummary
from ..services.dashboard import get_dashboard_summary

router = APIRouter()


@router.get(
    "/employers/me/dashboard",
    response_model=EmployerDashboardSummary,
    summary="Get aggregated employer dashboard summary, stats, and recent activities",
)
def get_employer_dashboard_endpoint(
    current_user: User = Depends(require_role(UserRole.EMPLOYER)),
    profile: EmployerProfile = Depends(get_employer_profile),
    db: Session = Depends(get_db),
) -> EmployerDashboardSummary:
    return get_dashboard_summary(db, profile, current_user)

