from fastapi import APIRouter
from .jobs import router as jobs_router
from .applications import router as applications_router
from .accommodation import router as accommodation_router
from .dashboard import router as dashboard_router

employer_feature_router = APIRouter()

employer_feature_router.include_router(jobs_router, tags=["employer-jobs"])
employer_feature_router.include_router(
    applications_router, tags=["employer-applications"]
)
employer_feature_router.include_router(
    accommodation_router, tags=["employer-accommodations"]
)
employer_feature_router.include_router(
    dashboard_router, tags=["employer-dashboard"]
)

__all__ = ["employer_feature_router"]

