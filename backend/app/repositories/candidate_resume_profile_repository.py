from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.models.candidate_resume_profile import CandidateResumeProfile
from app.models.resume import Resume

PROCESSING_LEASE = timedelta(minutes=15)
MAX_RETRY_DELAY = timedelta(hours=1)


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


class ResumeAssociationError(ValueError):
    """Raised when a resume does not belong to the supplied candidate profile."""


class StaleResumeProcessingAttempt(RuntimeError):
    """Raised when a worker tries to complete a superseded processing attempt."""


class CandidateResumeProfileRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def claim(
        self,
        candidate_profile_id: uuid.UUID,
        resume_id: uuid.UUID,
        *,
        force: bool = False,
    ) -> int | None:
        for retry in range(2):
            try:
                with self._session_factory.begin() as session:
                    bind = session.get_bind()
                    is_postgresql = bind.dialect.name == "postgresql"
                    now = datetime.now(UTC)
                    if is_postgresql:
                        lock_key = int.from_bytes(
                            hashlib.blake2b(resume_id.bytes, digest_size=8).digest(),
                            byteorder="big",
                            signed=True,
                        )
                        session.execute(select(func.pg_advisory_xact_lock(lock_key)))

                    resume_owner_id = session.scalar(
                        select(Resume.candidate_profile_id).where(Resume.id == resume_id)
                    )
                    if resume_owner_id is None:
                        raise ResumeAssociationError(
                            "The resume does not exist."
                        )
                    if resume_owner_id != candidate_profile_id:
                        raise ResumeAssociationError(
                            "The resume does not belong to the supplied candidate profile."
                        )

                    record = session.scalar(
                        select(CandidateResumeProfile)
                        .where(CandidateResumeProfile.resume_id == resume_id)
                        .with_for_update()
                    )
                    if record is None:
                        record = CandidateResumeProfile(
                            resume_id=resume_id,
                            status="PENDING",
                        )
                        session.add(record)
                        session.flush()

                    if record.status == "SUCCEEDED" and not force:
                        return None
                    if record.status == "PROCESSING":
                        if is_postgresql:
                            is_fresh = session.scalar(
                                select(
                                    CandidateResumeProfile.updated_at
                                    > func.now() - text("INTERVAL '15 minutes'")
                                ).where(CandidateResumeProfile.id == record.id)
                            )
                        else:
                            is_fresh = (
                                record.updated_at is not None
                                and _as_utc(record.updated_at) > now - PROCESSING_LEASE
                            )
                        if is_fresh:
                            return None

                    if record.status == "FAILED" and record.next_attempt_at is not None:
                        if is_postgresql:
                            retry_is_pending = session.scalar(
                                select(CandidateResumeProfile.next_attempt_at > func.now())
                                .where(CandidateResumeProfile.id == record.id)
                            )
                        else:
                            retry_is_pending = (
                                _as_utc(record.next_attempt_at) > now
                            )
                        if retry_is_pending and not force:
                            return None

                    database_now = func.now() if is_postgresql else now
                    record.status = "PROCESSING"
                    record.error_details = None
                    record.next_attempt_at = None
                    record.processed_at = None
                    record.attempt_count += 1
                    record.updated_at = database_now
                    session.flush()
                    return record.attempt_count
            except IntegrityError:
                if retry:
                    raise

        raise RuntimeError("Could not claim the resume extraction run.")

    def complete(
        self,
        resume_id: uuid.UUID,
        attempt: int,
        *,
        profile_json: dict[str, Any],
        provider: str,
        model: str | None,
        schema_version: str,
        extraction_mode: str,
        llm_skipped_reason: str | None,
    ) -> None:
        with self._session_factory.begin() as session:
            is_postgresql = session.get_bind().dialect.name == "postgresql"
            now = func.now() if is_postgresql else datetime.now(UTC)
            result = session.execute(
                update(CandidateResumeProfile)
                .where(
                    CandidateResumeProfile.resume_id == resume_id,
                    CandidateResumeProfile.attempt_count == attempt,
                    CandidateResumeProfile.status == "PROCESSING",
                )
                .values(
                    profile_json=profile_json,
                    status="SUCCEEDED",
                    last_success_provider=provider,
                    last_success_model=model,
                    last_success_schema_version=schema_version,
                    extraction_mode=extraction_mode,
                    llm_skipped_reason=llm_skipped_reason,
                    error_details=None,
                    next_attempt_at=None,
                    processed_at=now,
                    updated_at=now,
                )
            )
            if result.rowcount != 1:
                raise StaleResumeProcessingAttempt(
                    "The resume extraction attempt is no longer current."
                )

    def fail(
        self,
        resume_id: uuid.UUID,
        attempt: int,
        *,
        error_details: str,
    ) -> None:
        now = datetime.now(UTC)
        retry_seconds = min(
            60 * 2 ** min(max(attempt - 1, 0), 6),
            int(MAX_RETRY_DELAY.total_seconds()),
        )
        with self._session_factory.begin() as session:
            is_postgresql = session.get_bind().dialect.name == "postgresql"
            database_now = func.now() if is_postgresql else now
            next_attempt_at = (
                func.now() + text(f"INTERVAL '{retry_seconds} seconds'")
                if is_postgresql
                else now + timedelta(seconds=retry_seconds)
            )
            result = session.execute(
                update(CandidateResumeProfile)
                .where(
                    CandidateResumeProfile.resume_id == resume_id,
                    CandidateResumeProfile.attempt_count == attempt,
                    CandidateResumeProfile.status == "PROCESSING",
                )
                .values(
                    status="FAILED",
                    error_details=error_details[:500],
                    next_attempt_at=next_attempt_at,
                    processed_at=None,
                    updated_at=database_now,
                )
            )
            if result.rowcount != 1:
                raise StaleResumeProcessingAttempt(
                    "The resume extraction attempt is no longer current."
                )

    def get_status(self, resume_id: uuid.UUID) -> dict[str, Any] | None:
        with self._session_factory() as session:
            record = session.scalar(
                select(CandidateResumeProfile).where(
                    CandidateResumeProfile.resume_id == resume_id
                )
            )
            if record is None:
                return None
            return {
                "resume_id": str(record.resume_id),
                "status": record.status,
                "last_success_provider": record.last_success_provider,
                "last_success_model": record.last_success_model,
                "last_success_schema_version": record.last_success_schema_version,
                "extraction_mode": record.extraction_mode,
                "llm_skipped_reason": record.llm_skipped_reason,
                "error_details": record.error_details,
                "attempt_count": record.attempt_count,
                "processed_at": record.processed_at.isoformat()
                if record.processed_at
                else None,
            }

    def get_profile_if_succeeded(self, resume_id: uuid.UUID) -> dict[str, Any] | None:
        with self._session_factory() as session:
            record = session.scalar(
                select(CandidateResumeProfile).where(
                    CandidateResumeProfile.resume_id == resume_id,
                    CandidateResumeProfile.status == "SUCCEEDED",
                )
            )
            return record.profile_json if record is not None else None
