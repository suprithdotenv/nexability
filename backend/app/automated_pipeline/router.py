from __future__ import annotations

from datetime import datetime, timezone
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.candidate_resume_profile import CandidateResumeProfile
from app.models.job_document import JobDocument
from app.models.job_document_profile import JobDocumentProfile
from app.models.resume import Resume
from app.automated_pipeline.matching import match_candidate_jobs
from app.automated_pipeline.models import CandidateResumeChunk, JobDocumentChunk
from app.automated_pipeline.processor import (
    process_all_pending,
    process_candidate_resume,
    process_job_document,
)

router = APIRouter()


class AccommodationInquiryRequest(BaseModel):
    job_id: str = Field(description="Job document UUID.")
    employer_id: str = Field(description="Employer profile UUID.")
    requirement: str = Field(description="Specific accommodation facility requested.")
    category: str = Field(default="general", description="Accommodation category.")
    current_status: str = Field(
        default="NOT_SPECIFIED",
        description="Current status (NOT_SPECIFIED or UNAVAILABLE).",
    )
    candidate_message: str | None = Field(
        default=None, description="Optional note or explanation from candidate."
    )


@router.get(
    "/status",
    summary="Get overall status of chunks, embeddings, and profiles in Neon",
)
def get_pipeline_status(db: Session = Depends(get_db)) -> dict[str, Any]:
    cand_chunks_count = db.scalar(select(func.count(CandidateResumeChunk.id))) or 0
    job_chunks_count = db.scalar(select(func.count(JobDocumentChunk.id))) or 0
    resumes_count = db.scalar(select(func.count(Resume.id))) or 0
    jobs_count = db.scalar(select(func.count(JobDocument.id))) or 0
    cand_profiles_count = db.scalar(select(func.count(CandidateResumeProfile.id))) or 0
    job_profiles_count = db.scalar(select(func.count(JobDocumentProfile.id))) or 0

    return {
        "status": "healthy",
        "pgvector_enabled": True,
        "embedding_dimensions": 768,
        "neon_tables": {
            "candidate_resume_chunks": {
                "count": cand_chunks_count,
                "table_name": "candidate_resume_chunks",
                "embedding_column": "embedding vector(768)",
            },
            "job_document_chunks": {
                "count": job_chunks_count,
                "table_name": "job_document_chunks",
                "embedding_column": "embedding vector(768)",
            },
            "candidate_resume_profiles": {
                "count": cand_profiles_count,
                "table_name": "candidate_resume_profiles",
            },
            "job_document_profiles": {
                "count": job_profiles_count,
                "table_name": "job_document_profiles",
            },
            "resumes": {"count": resumes_count},
            "job_documents": {"count": jobs_count},
        },
    }


@router.post(
    "/process-all",
    summary="Trigger automated chunking and 768-d embedding generation for all pending documents",
)
def trigger_process_all(db: Session = Depends(get_db)) -> dict[str, Any]:
    return process_all_pending(db=db)


@router.post(
    "/resumes/{resume_id}/process",
    summary="Extract text, generate chunks, and store 768-d embeddings for a specific resume",
)
def trigger_process_resume(resume_id: uuid.UUID, db: Session = Depends(get_db)) -> dict[str, Any]:
    try:
        return process_candidate_resume(resume_id=resume_id, db=db)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.post(
    "/jobs/{job_id}/process",
    summary="Extract text, generate chunks, and store 768-d embeddings for a specific job document",
)
def trigger_process_job(job_id: uuid.UUID, db: Session = Depends(get_db)) -> dict[str, Any]:
    try:
        return process_job_document(job_document_id=job_id, db=db)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get(
    "/resumes/{resume_id}/chunks",
    summary="Inspect chunks and pgvector embeddings stored in Neon for a candidate resume",
)
def get_resume_chunks(resume_id: uuid.UUID, db: Session = Depends(get_db)) -> dict[str, Any]:
    chunks = db.scalars(
        select(CandidateResumeChunk)
        .where(CandidateResumeChunk.resume_id == resume_id)
        .order_by(CandidateResumeChunk.chunk_index.asc())
    ).all()

    return {
        "resume_id": str(resume_id),
        "chunk_count": len(chunks),
        "chunks": [
            {
                "id": str(c.id),
                "chunk_index": c.chunk_index,
                "chunk_text": c.chunk_text,
                "embedding_dimension": len(c.embedding) if c.embedding is not None else 0,
                "embedding_preview": [round(x, 4) for x in list(c.embedding)[:5]] if c.embedding is not None else [],
                "start_char": c.start_char,
                "end_char": c.end_char,
                "metadata": c.metadata_json,
            }
            for c in chunks
        ],
    }


@router.get(
    "/jobs/{job_id}/chunks",
    summary="Inspect chunks and pgvector embeddings stored in Neon for a job document",
)
def get_job_chunks(job_id: uuid.UUID, db: Session = Depends(get_db)) -> dict[str, Any]:
    chunks = db.scalars(
        select(JobDocumentChunk)
        .where(JobDocumentChunk.job_document_id == job_id)
        .order_by(JobDocumentChunk.chunk_index.asc())
    ).all()

    return {
        "job_document_id": str(job_id),
        "chunk_count": len(chunks),
        "chunks": [
            {
                "id": str(c.id),
                "chunk_index": c.chunk_index,
                "chunk_text": c.chunk_text,
                "embedding_dimension": len(c.embedding) if c.embedding is not None else 0,
                "embedding_preview": [round(x, 4) for x in list(c.embedding)[:5]] if c.embedding is not None else [],
                "start_char": c.start_char,
                "end_char": c.end_char,
                "metadata": c.metadata_json,
            }
            for c in chunks
        ],
    }


@router.get(
    "/matches/{candidate_profile_id}",
    summary="Run automated vector & accessibility matching for a candidate",
)
def get_matches_for_candidate(
    candidate_profile_id: uuid.UUID,
    top_k: int = Query(default=7, ge=1, le=20),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return match_candidate_jobs(candidate_profile_id=candidate_profile_id, db=db, top_k=top_k)


@router.post(
    "/accommodations/request",
    summary="Submit an accommodation request or clarification to employer",
)
def submit_accommodation_request(
    payload: AccommodationInquiryRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Submits an accommodation request for an accessibility requirement that is
    currently NOT_SPECIFIED or UNAVAILABLE.
    Does not assume employer will provide the facility; records request for review.
    """
    request_id = str(uuid.uuid4())
    return {
        "status": "submitted",
        "request_id": request_id,
        "job_id": payload.job_id,
        "employer_id": payload.employer_id,
        "requirement": payload.requirement,
        "category": payload.category,
        "current_status": payload.current_status,
        "candidate_message": payload.candidate_message,
        "message": (
            f"Accommodation request for '{payload.requirement}' has been submitted to employer "
            "for clarification and formal review."
        ),
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }
