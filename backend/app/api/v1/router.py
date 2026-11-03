from fastapi import APIRouter

from app.api.v1.endpoints import auth, candidates, employers, matches, ml_access
from app.automated_pipeline.router import router as pipeline_router


api_router = APIRouter()

api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(candidates.router, prefix="/candidates", tags=["candidates"])
api_router.include_router(matches.router, prefix="/candidates", tags=["matching"])
api_router.include_router(employers.router, prefix="/employers", tags=["employers"])
api_router.include_router(ml_access.router, prefix="/internal/ml", tags=["internal-ml"])
api_router.include_router(pipeline_router, prefix="/pipeline", tags=["automated-pipeline"])
