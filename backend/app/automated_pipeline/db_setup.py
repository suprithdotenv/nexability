from __future__ import annotations

import logging
from sqlalchemy import create_engine, text

from app.core.config import settings
from app.db.base import Base

# Ensure all models are imported so Base.metadata knows about them
from app.models.candidate_resume_profile import CandidateResumeProfile  # noqa: F401
from app.models.job_document_profile import JobDocumentProfile  # noqa: F401
from app.automated_pipeline.models import CandidateResumeChunk, JobDocumentChunk  # noqa: F401

logger = logging.getLogger("automated_pipeline.db_setup")


def init_pgvector_tables() -> None:
    """
    Ensure the vector extension and all required tables exist in the Neon database.
    Idempotent and safe to run multiple times.
    """
    engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

    with engine.connect() as conn:
        # 1. Enable pgvector extension
        logger.info("Enabling pgvector extension in Neon...")
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()

        # 2. Verify extension
        res = conn.execute(
            text("SELECT extname, extversion FROM pg_extension WHERE extname = 'vector'")
        ).fetchone()
        logger.info("Neon pgvector extension status: %s", res)

    # 3. Create all tables defined in Base.metadata
    logger.info("Creating any missing tables in Neon...")
    Base.metadata.create_all(bind=engine)

    # 4. Create HNSW vector cosine indexes for lightning-fast nearest-neighbor search
    with engine.begin() as conn:
        logger.info("Creating HNSW cosine vector index on candidate_resume_chunks...")
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_candidate_resume_chunks_embedding
                ON candidate_resume_chunks USING hnsw (embedding vector_cosine_ops);
                """
            )
        )

        logger.info("Creating HNSW cosine vector index on job_document_chunks...")
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_job_document_chunks_embedding
                ON job_document_chunks USING hnsw (embedding vector_cosine_ops);
                """
            )
        )

    logger.info("pgvector database setup completed successfully in Neon!")
    engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_pgvector_tables()
