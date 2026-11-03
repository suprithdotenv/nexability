from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from employer_feature import employer_feature_router


app = FastAPI(
    title="NexAbility API",
    description="Backend API for the NexAbility platform",
    version="1.0.0",
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


app.include_router(
    api_router,
    prefix="/api/v1",
)

app.include_router(
    employer_feature_router,
    prefix="/api/v1",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
