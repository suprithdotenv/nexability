from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.candidate_profile import CandidateProfile
from app.models.candidate_resume_profile import CandidateResumeProfile
from app.models.resume import Resume
from app.models.user import User, UserRole
from app.repositories.candidate_resume_profile_repository import (
    CandidateResumeProfileRepository,
    ResumeAssociationError,
)


@pytest.fixture
def repository():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)

    user_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    resume_id = uuid.uuid4()
    with sessions.begin() as session:
        session.add(
            User(
                id=user_id,
                email=f"{user_id}@example.test",
                role=UserRole.CANDIDATE,
            )
        )
        session.flush()
        session.add(
            CandidateProfile(
                id=candidate_id,
                user_id=user_id,
                full_name="Candidate",
            )
        )
        session.flush()
        session.add(
            Resume(
                id=resume_id,
                candidate_profile_id=candidate_id,
                original_filename="resume.docx",
                storage_path=f"candidates/{candidate_id}/{resume_id}.docx",
                mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                file_size_bytes=100,
                is_active=True,
            )
        )

    yield CandidateResumeProfileRepository(sessions), sessions, candidate_id, resume_id
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_claim_persists_profile_and_success_skips_duplicate(repository):
    repo, sessions, candidate_id, resume_id = repository
    attempt = repo.claim(candidate_id, resume_id)
    assert attempt == 1

    repo.complete(
        resume_id,
        attempt,
        profile_json={"full_name": "Candidate", "skills": []},
        provider="groq",
        model="test-model",
        schema_version="1",
        extraction_mode="llm",
        llm_skipped_reason=None,
    )
    assert repo.claim(candidate_id, resume_id) is None

    with sessions() as session:
        record = session.scalar(
            select(CandidateResumeProfile).where(
                CandidateResumeProfile.resume_id == resume_id
            )
        )
        assert record is not None
        assert record.resume_id == resume_id
        assert record.status == "SUCCEEDED"
        assert record.profile_json == {"full_name": "Candidate", "skills": []}
        assert record.last_success_provider == "groq"
        assert record.last_success_model == "test-model"
        assert record.last_success_schema_version == "1"
        assert record.extraction_mode == "llm"


def test_wrong_candidate_cannot_claim_resume(repository):
    repo, _sessions, _candidate_id, resume_id = repository

    with pytest.raises(ResumeAssociationError):
        repo.claim(uuid.uuid4(), resume_id)


def test_failure_status_backoff_and_forced_reextraction(repository):
    repo, sessions, candidate_id, resume_id = repository
    attempt = repo.claim(candidate_id, resume_id)
    repo.fail(
        resume_id,
        attempt,
        error_details="download_runtimeerror",
    )

    with sessions() as session:
        record = session.scalar(
            select(CandidateResumeProfile).where(
                CandidateResumeProfile.resume_id == resume_id
            )
        )
        assert record.status == "FAILED"
        assert record.error_details == "download_runtimeerror"
        assert record.next_attempt_at is not None
        assert record.last_success_provider is None
        assert record.last_success_model is None
        assert record.last_success_schema_version is None
        retry_at = record.next_attempt_at
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=UTC)
        assert retry_at > datetime.now(UTC)

    assert repo.claim(candidate_id, resume_id) is None
    retry_attempt = repo.claim(candidate_id, resume_id, force=True)
    assert retry_attempt == 2


def test_stale_attempt_cannot_overwrite_retried_result(repository):
    repo, sessions, candidate_id, resume_id = repository
    first_attempt = repo.claim(candidate_id, resume_id)

    with sessions.begin() as session:
        record = session.scalar(
            select(CandidateResumeProfile).where(
                CandidateResumeProfile.resume_id == resume_id
            )
        )
        record.updated_at = datetime.now(UTC) - timedelta(minutes=20)

    second_attempt = repo.claim(candidate_id, resume_id)
    assert second_attempt == first_attempt + 1

    from app.repositories.candidate_resume_profile_repository import (
        StaleResumeProcessingAttempt,
    )

    with pytest.raises(StaleResumeProcessingAttempt):
        repo.complete(
            resume_id,
            first_attempt,
            profile_json={"full_name": "stale"},
            provider="rule_based",
            model=None,
            schema_version="1",
            extraction_mode="rule_based",
            llm_skipped_reason=None,
        )


def test_failed_reprocessing_keeps_last_success_but_hides_it(repository):
    repo, sessions, candidate_id, resume_id = repository
    first_attempt = repo.claim(candidate_id, resume_id)
    last_good_profile = {"full_name": "Candidate", "skills": ["python"]}
    repo.complete(
        resume_id,
        first_attempt,
        profile_json=last_good_profile,
        provider="groq",
        model="test-model",
        schema_version="7",
        extraction_mode="llm",
        llm_skipped_reason=None,
    )

    retry_attempt = repo.claim(candidate_id, resume_id, force=True)
    repo.fail(resume_id, retry_attempt, error_details="extraction_failed")

    assert repo.get_profile_if_succeeded(resume_id) is None
    status = repo.get_status(resume_id)
    assert status["status"] == "FAILED"
    assert status["last_success_provider"] == "groq"
    assert status["last_success_model"] == "test-model"
    assert status["last_success_schema_version"] == "7"
    assert "profile_json" not in status

    with sessions() as session:
        record = session.scalar(
            select(CandidateResumeProfile).where(
                CandidateResumeProfile.resume_id == resume_id
            )
        )
        assert record.profile_json == last_good_profile
