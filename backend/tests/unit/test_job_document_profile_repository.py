from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.employer_profile import EmployerProfile
from app.models.job_document import JobDocument
from app.models.job_document_profile import JobDocumentProfile
from app.models.user import User, UserRole
from app.repositories.job_document_profile_repository import (
    JobDocumentAssociationError,
    JobDocumentProfileRepository,
    StaleJobProcessingAttempt,
)


@pytest.fixture
def repository():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    user_id = uuid.uuid4()
    employer_id = uuid.uuid4()
    document_id = uuid.uuid4()
    with sessions.begin() as session:
        session.add(
            User(
                id=user_id,
                email=f"{user_id}@example.test",
                role=UserRole.EMPLOYER,
            )
        )
        session.flush()
        session.add(
            EmployerProfile(
                id=employer_id,
                user_id=user_id,
                full_name="Employer",
                company_name="Test Company",
                email_domain="example.test",
            )
        )
        session.flush()
        session.add(
            JobDocument(
                id=document_id,
                employer_profile_id=employer_id,
                original_filename="job.docx",
                storage_path=f"employers/{employer_id}/{document_id}.docx",
                mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                file_size_bytes=100,
                status="UPLOADED",
            )
        )
    yield JobDocumentProfileRepository(sessions), sessions, employer_id, document_id
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_job_profile_is_persisted_by_document_and_duplicate_skips(repository):
    repo, sessions, employer_id, document_id = repository
    attempt = repo.claim(document_id, employer_id)
    assert attempt == 1
    profile = {"job_id": str(document_id), "requirements": []}
    repo.complete(
        document_id,
        attempt,
        profile_json=profile,
        provider="rule_based",
        model=None,
        schema_version="1",
        extraction_mode="rule_based",
        llm_skipped_reason=None,
    )

    assert repo.claim(document_id, employer_id) is None
    assert repo.get_profile_if_succeeded(document_id) == profile
    with sessions() as session:
        record = session.scalar(
            select(JobDocumentProfile).where(
                JobDocumentProfile.document_id == document_id
            )
        )
        assert record.status == "SUCCEEDED"
        assert record.last_success_schema_version == "1"


def test_wrong_employer_cannot_claim_job_document(repository):
    repo, _sessions, _employer_id, document_id = repository
    with pytest.raises(JobDocumentAssociationError):
        repo.claim(document_id, uuid.uuid4())


def test_failed_reprocessing_keeps_last_success_but_hides_profile(repository):
    repo, sessions, employer_id, document_id = repository
    first = repo.claim(document_id, employer_id)
    last_good = {"job_title": "Data Engineer"}
    repo.complete(
        document_id,
        first,
        profile_json=last_good,
        provider="rule_based",
        model=None,
        schema_version="3",
        extraction_mode="rule_based",
        llm_skipped_reason=None,
    )

    retry = repo.claim(document_id, employer_id, force=True)
    repo.fail(document_id, retry, error_details="no_extractable_text")

    assert repo.get_profile_if_succeeded(document_id) is None
    status = repo.get_status(document_id)
    assert status["status"] == "FAILED"
    assert status["last_success_schema_version"] == "3"
    assert "profile_json" not in status
    with sessions() as session:
        record = session.scalar(
            select(JobDocumentProfile).where(
                JobDocumentProfile.document_id == document_id
            )
        )
        assert record.profile_json == last_good


def test_stale_job_attempt_cannot_overwrite_a_newer_claim(repository):
    repo, sessions, employer_id, document_id = repository
    first = repo.claim(document_id, employer_id)
    with sessions.begin() as session:
        record = session.scalar(
            select(JobDocumentProfile).where(
                JobDocumentProfile.document_id == document_id
            )
        )
        record.updated_at = datetime.now(UTC) - timedelta(minutes=20)

    second = repo.claim(document_id, employer_id)
    assert second == first + 1
    with pytest.raises(StaleJobProcessingAttempt):
        repo.complete(
            document_id,
            first,
            profile_json={"job_title": "stale"},
            provider="rule_based",
            model=None,
            schema_version="1",
            extraction_mode="rule_based",
            llm_skipped_reason=None,
        )
