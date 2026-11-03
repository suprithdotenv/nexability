from __future__ import annotations

import argparse
import logging
import os
import time
from typing import TYPE_CHECKING, Any
from uuid import UUID

os.environ["PYTHON_DOTENV_DISABLED"] = "1"

if TYPE_CHECKING:
    from nexability_ml.document_dispatcher import DocumentProcessingDispatcher

    from app.repositories.candidate_resume_profile_repository import (
        CandidateResumeProfileRepository,
    )


logger = logging.getLogger("nexability.resume_worker")


def _required_environment(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Required process environment variable {name} is not set.")
    return value


def build_processor() -> tuple[
    DocumentProcessingDispatcher, CandidateResumeProfileRepository, Any
]:
    from nexability_ml.api_client import InternalMLClient
    from nexability_ml.document_dispatcher import DocumentProcessingDispatcher
    from nexability_ml.embeddings import WhitespaceTokenizer
    from nexability_ml.job_processing import JobDocumentProcessor
    from nexability_ml.pipeline import NexAbilityMLPipeline
    from nexability_ml.resume_processing import ResumeExtractionProcessor
    from nexability_ml.vectorstore import SimpleEmbeddingModel
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.repositories.candidate_resume_profile_repository import (
        CandidateResumeProfileRepository,
    )
    from app.repositories.job_document_profile_repository import (
        JobDocumentProfileRepository,
    )

    database_url = _required_environment("DATABASE_URL")
    backend_url = _required_environment("NEXABILITY_BACKEND_URL")
    internal_service_key = _required_environment("INTERNAL_ML_API_KEY")

    engine = create_engine(database_url, pool_pre_ping=True)
    session_factory = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    resume_repository = CandidateResumeProfileRepository(session_factory)
    job_repository = JobDocumentProfileRepository(session_factory)
    client = InternalMLClient(backend_url, api_key=internal_service_key)
    pipeline = NexAbilityMLPipeline(
        embedding_model=SimpleEmbeddingModel(),
        tokenizer=WhitespaceTokenizer(),
    )
    resume_processor = ResumeExtractionProcessor(
        client=client,
        repository=resume_repository,
        pipeline=pipeline,
    )
    job_processor = JobDocumentProcessor(
        client=client,
        repository=job_repository,
        pipeline=pipeline,
    )
    return (
        DocumentProcessingDispatcher(
            resume_processor=resume_processor,
            job_processor=job_processor,
        ),
        resume_repository,
        engine,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Poll and process uploaded résumé and job documents."
    )
    parser.add_argument("--once", action="store_true", help="Process the queue once and exit.")
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=30,
        help="Seconds between queue polls (minimum 1).",
    )
    parser.add_argument("--reprocess", type=UUID, help="Force re-extraction for this resume ID.")
    parser.add_argument(
        "--status",
        type=UUID,
        help="Show stored processing status for this resume.",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        _run_worker()
    except Exception as exc:
        logger.error("Resume worker stopped after an internal error (%s).", type(exc).__name__)
        raise SystemExit(1) from None


def _run_worker() -> None:
    args = _parse_args()
    if args.poll_interval < 1:
        raise ValueError("--poll-interval must be at least 1.")

    dispatcher, repository, engine = build_processor()
    try:
        if args.status:
            status_record = repository.get_status(args.status)
            if status_record is None:
                print("No extraction record exists for that resume.")
            else:
                print(status_record)
            return

        if args.reprocess:
            metadata = dispatcher.resume_processor.client.get_resume_metadata(
                str(args.reprocess)
            )
            result = dispatcher.resume_processor.process_resume_metadata(
                metadata,
                force=True,
            )
            logger.info("Resume reprocessing finished: outcome=%s", result)
            return

        while True:
            counts = dispatcher.process_pending_documents()
            logger.info(
                "Document queue poll complete: processed=%d skipped=%d failed=%d",
                counts["processed"],
                counts["skipped"],
                counts["failed"],
            )
            if args.once:
                return
            time.sleep(args.poll_interval)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
