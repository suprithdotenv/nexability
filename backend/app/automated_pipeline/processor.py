from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.candidate_resume_profile import CandidateResumeProfile
from app.models.job_document import JobDocument
from app.models.job_document_profile import JobDocumentProfile
from app.models.resume import Resume
from app.services.storage.storage_service import storage_service

from app.automated_pipeline.chunker import chunk_text
from app.automated_pipeline.embeddings import get_embedding_encoder
from app.automated_pipeline.extractor import (
    extract_candidate_profile_json,
    extract_job_profile_json,
    extract_text_from_bytes,
)
from app.automated_pipeline.models import CandidateResumeChunk, JobDocumentChunk

logger = logging.getLogger("automated_pipeline.processor")




def process_candidate_resume(
    resume_id: uuid.UUID,
    db: Session | None = None,
    content: bytes | None = None,
) -> dict[str, Any]:
    """
    Automated processing of a candidate's resume:
    1. Reads document bytes (from Supabase storage or memory).
    2. Extracts full text.
    3. Token-chunks text with offsets.
    4. Computes 768-d normalized embeddings.
    5. Saves chunks & pgvector embeddings in Neon `candidate_resume_chunks`.
    6. Extracts structured candidate profile & saves to `candidate_resume_profiles`.
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        resume = db.scalar(select(Resume).where(Resume.id == resume_id))
        if not resume:
            raise ValueError(f"Resume {resume_id} not found.")

        # 1. Download bytes if not provided
        if content is None:
            logger.info("Downloading resume %s from Supabase storage...", resume_id)
            content = storage_service.download_file(
                bucket=settings.SUPABASE_STORAGE_BUCKET_RESUMES,
                storage_path=resume.storage_path,
            )

        if not content:
            raise ValueError("Empty resume document content.")

        # 2. Extract text
        raw_text = extract_text_from_bytes(content, resume.original_filename, resume.mime_type)
        if not raw_text.strip():
            logger.warning("No text extractable from resume %s", resume_id)
            raw_text = f"Resume filename: {resume.original_filename}"

        # 3. Chunk text
        chunks_data = chunk_text(raw_text)
        if not chunks_data:
            chunks_data = [{
                "chunk_index": 0,
                "chunk_text": raw_text[:500],
                "start_char": 0,
                "end_char": min(500, len(raw_text)),
                "metadata": {"section_name": "general", "token_count": len(raw_text.split())},
            }]

        # 4. Generate 768-d embeddings
        encoder = get_embedding_encoder()
        texts_to_encode = [c["chunk_text"] for c in chunks_data]
        embeddings = encoder.encode(texts_to_encode, prefix="passage: ")

        # 5. Persist chunks and embeddings in Neon pgvector
        db.execute(delete(CandidateResumeChunk).where(CandidateResumeChunk.resume_id == resume_id))

        chunk_rows = []
        for c, emb in zip(chunks_data, embeddings, strict=True):
            row = CandidateResumeChunk(
                candidate_profile_id=resume.candidate_profile_id,
                resume_id=resume.id,
                chunk_index=c["chunk_index"],
                chunk_text=c["chunk_text"],
                embedding=emb,
                start_char=c.get("start_char"),
                end_char=c.get("end_char"),
                metadata_json=c.get("metadata"),
            )
            chunk_rows.append(row)
        db.add_all(chunk_rows)

        # 6. Extract structured profile
        profile_json = extract_candidate_profile_json(raw_text)

        # Save/update CandidateResumeProfile
        resume_profile = db.scalar(
            select(CandidateResumeProfile).where(CandidateResumeProfile.resume_id == resume_id)
        )
        now = datetime.now(timezone.utc)
        if not resume_profile:
            resume_profile = CandidateResumeProfile(
                resume_id=resume.id,
                profile_json=profile_json,
                status="SUCCEEDED",
                last_success_provider="automated_pipeline",
                last_success_model="pgvector-e5",
                last_success_schema_version="1.0",
                extraction_mode="rule_based",
                processed_at=now,
                attempt_count=1,
            )
            db.add(resume_profile)
        else:
            resume_profile.profile_json = profile_json
            resume_profile.status = "SUCCEEDED"
            resume_profile.last_success_provider = "automated_pipeline"
            resume_profile.last_success_model = "pgvector-e5"
            resume_profile.processed_at = now
            resume_profile.error_details = None

        db.commit()
        logger.info(
            "Resume %s processed: stored %d chunks with 768-d embeddings in Neon.",
            resume_id,
            len(chunk_rows),
        )

        return {
            "resume_id": str(resume.id),
            "candidate_profile_id": str(resume.candidate_profile_id),
            "status": "SUCCEEDED",
            "chunks_stored": len(chunk_rows),
            "embeddings_stored": len(chunk_rows),
            "embedding_dim": 768,
            "skills_count": profile_json.get("skills_count", 0),
        }
    except Exception as exc:
        db.rollback()
        logger.error("Failed to process candidate resume %s: %s", resume_id, exc)
        raise
    finally:
        if close_db:
            db.close()


def process_job_document(
    job_document_id: uuid.UUID,
    db: Session | None = None,
    content: bytes | None = None,
) -> dict[str, Any]:
    """
    Automated processing of an employer's job description:
    1. Reads document bytes (from Supabase storage or memory).
    2. Extracts full text.
    3. Token-chunks text with offsets.
    4. Computes 768-d normalized embeddings.
    5. Saves chunks & pgvector embeddings in Neon `job_document_chunks`.
    6. Extracts structured job profile & saves to `job_document_profiles`.
    7. Updates job_document.status = 'PROCESSED'.
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        doc = db.scalar(select(JobDocument).where(JobDocument.id == job_document_id))
        if not doc:
            raise ValueError(f"Job document {job_document_id} not found.")

        # 1. Download bytes if not provided
        if content is None:
            logger.info("Downloading job document %s from Supabase storage...", job_document_id)
            content = storage_service.download_file(
                bucket=settings.SUPABASE_STORAGE_BUCKET_JOB_DOCS,
                storage_path=doc.storage_path,
            )

        if not content:
            raise ValueError("Empty job document content.")

        # 2. Extract text
        raw_text = extract_text_from_bytes(content, doc.original_filename, doc.mime_type)
        if not raw_text.strip():
            logger.warning("No text extractable from job document %s", job_document_id)
            raw_text = f"Job document filename: {doc.original_filename}"

        # 3. Chunk text
        chunks_data = chunk_text(raw_text)
        if not chunks_data:
            chunks_data = [{
                "chunk_index": 0,
                "chunk_text": raw_text[:500],
                "start_char": 0,
                "end_char": min(500, len(raw_text)),
                "metadata": {"section_name": "general", "token_count": len(raw_text.split())},
            }]

        # 4. Generate 768-d embeddings
        encoder = get_embedding_encoder()
        texts_to_encode = [c["chunk_text"] for c in chunks_data]
        embeddings = encoder.encode(texts_to_encode, prefix="passage: ")

        # 5. Persist chunks and embeddings in Neon pgvector
        db.execute(delete(JobDocumentChunk).where(JobDocumentChunk.job_document_id == job_document_id))

        chunk_rows = []
        for c, emb in zip(chunks_data, embeddings, strict=True):
            row = JobDocumentChunk(
                employer_profile_id=doc.employer_profile_id,
                job_document_id=doc.id,
                chunk_index=c["chunk_index"],
                chunk_text=c["chunk_text"],
                embedding=emb,
                start_char=c.get("start_char"),
                end_char=c.get("end_char"),
                metadata_json=c.get("metadata"),
            )
            chunk_rows.append(row)
        db.add_all(chunk_rows)

        # 6. Extract structured profile
        profile_json = extract_job_profile_json(raw_text, filename=doc.original_filename)

        # Save/update JobDocumentProfile
        job_profile = db.scalar(
            select(JobDocumentProfile).where(JobDocumentProfile.document_id == job_document_id)
        )
        now = datetime.now(timezone.utc)
        if not job_profile:
            job_profile = JobDocumentProfile(
                document_id=doc.id,
                profile_json=profile_json,
                status="SUCCEEDED",
                last_success_provider="automated_pipeline",
                last_success_model="pgvector-e5",
                last_success_schema_version="1.0",
                extraction_mode="rule_based",
                processed_at=now,
                attempt_count=1,
            )
            db.add(job_profile)
        else:
            job_profile.profile_json = profile_json
            job_profile.status = "SUCCEEDED"
            job_profile.last_success_provider = "automated_pipeline"
            job_profile.last_success_model = "pgvector-e5"
            job_profile.processed_at = now
            job_profile.error_details = None

        # Update JobDocument status
        doc.status = "PROCESSED"

        db.commit()
        logger.info(
            "Job document %s processed: stored %d chunks with 768-d embeddings in Neon.",
            job_document_id,
            len(chunk_rows),
        )

        return {
            "job_document_id": str(doc.id),
            "employer_profile_id": str(doc.employer_profile_id),
            "status": "PROCESSED",
            "chunks_stored": len(chunk_rows),
            "embeddings_stored": len(chunk_rows),
            "embedding_dim": 768,
            "job_title": profile_json.get("job_title"),
            "requirements_count": profile_json.get("requirements_count", 0),
        }
    except Exception as exc:
        db.rollback()
        logger.error("Failed to process job document %s: %s", job_document_id, exc)
        raise
    finally:
        if close_db:
            db.close()


def process_all_pending(db: Session | None = None) -> dict[str, Any]:
    """
    Finds and processes all resumes and job documents currently in the Neon database
    that require chunking and embedding.
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        # 1. Process all active resumes
        resumes = db.scalars(select(Resume).where(Resume.is_active.is_(True))).all()
        resume_results = []
        for res in resumes:
            try:
                res_outcome = process_candidate_resume(res.id, db=db)
                resume_results.append(res_outcome)
            except Exception as e:
                logger.error("Failed processing resume %s: %s", res.id, e)
                resume_results.append({"resume_id": str(res.id), "status": "FAILED", "error": str(e)})

        # 2. Process all job documents
        jobs = db.scalars(select(JobDocument)).all()
        job_results = []
        for j in jobs:
            try:
                j_outcome = process_job_document(j.id, db=db)
                job_results.append(j_outcome)
            except Exception as e:
                logger.error("Failed processing job %s: %s", j.id, e)
                job_results.append({"job_document_id": str(j.id), "status": "FAILED", "error": str(e)})

        return {
            "resumes_processed": len(resume_results),
            "jobs_processed": len(job_results),
            "resumes": resume_results,
            "jobs": job_results,
        }
    finally:
        if close_db:
            db.close()
