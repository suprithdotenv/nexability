from __future__ import annotations

import io
import json
import zipfile
from types import SimpleNamespace
from uuid import UUID

import pytest

from nexability_ml.document_dispatcher import DocumentProcessingDispatcher
from nexability_ml.embeddings import SimpleEmbeddingModel, WhitespaceTokenizer
from nexability_ml.groq_extraction import GroqExtractionClient
from nexability_ml.job_processing import (
    JOB_PROFILE_SCHEMA_VERSION,
    JobDocumentProcessor,
)
from nexability_ml.pipeline import NexAbilityMLPipeline

JOB_ID = UUID("b1aa8ea9-782c-4c8f-afc2-d4e56075bb65")
EMPLOYER_ID = UUID("f0f7d526-37ec-4af5-bd2a-0ca90d8dcc62")
RESUME_ID = UUID("1c152f14-25d5-4c83-b3ea-12640b75b8bd")
CANDIDATE_ID = UUID("742572f5-6d63-4dae-a537-504b5d88efba")


def _docx_bytes(text: str) -> bytes:
    output = io.BytesIO()
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        + "".join(f"<w:p><w:r><w:t>{line}</w:t></w:r></w:p>" for line in text.splitlines())
        + "</w:body></w:document>"
    )
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("word/document.xml", xml)
    return output.getvalue()


class FakeProfileRepository:
    def __init__(self) -> None:
        self.claimed = None
        self.completed = None
        self.failure = None
        self.attempt = 0

    def claim(self, document_id, employer_profile_id, *, force=False):
        self.claimed = (document_id, employer_profile_id)
        self.attempt += 1
        return self.attempt

    def complete(self, document_id, attempt, **values):
        self.completed = {
            "document_id": document_id,
            "attempt": attempt,
            **values,
        }

    def fail(self, document_id, attempt, *, error_details):
        self.failure = (document_id, attempt, error_details)


class FakeResumeRepository:
    def claim(self, *_args, **_kwargs):
        return None


class FakeClient:
    def __init__(self) -> None:
        self.job_bytes = _docx_bytes(
            "Job Title: Data Engineer\nRequired Skills\n- Python\n"
            "Responsibilities\n- Build reliable data pipelines"
        )
        self.active_resumes = []

    def get_job_document_metadata(self, _document_id):
        return {
            "document_id": str(JOB_ID),
            "document_type": "JOB_DOCUMENT",
            "owner_id": str(EMPLOYER_ID),
            "original_filename": "job.docx",
            "mime_type": (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ),
        }

    def get_job_document_content(self, _document_id):
        return self.job_bytes

    def list_pending_documents(self):
        return {
            "pending_job_documents": [
                {
                    "document_id": str(JOB_ID),
                    "document_type": "JOB_DOCUMENT",
                    "owner_id": str(EMPLOYER_ID),
                }
            ],
            "active_resumes": self.active_resumes,
        }


def _pipeline(*, extraction_client=None, enable_llm_extraction=False):
    return NexAbilityMLPipeline(
        embedding_model=SimpleEmbeddingModel(),
        tokenizer=WhitespaceTokenizer(),
        extraction_client=extraction_client,
        enable_llm_extraction=enable_llm_extraction,
    )


def test_job_document_profile_is_linked_to_exact_document_and_employer():
    repository = FakeProfileRepository()
    processor = JobDocumentProcessor(
        client=FakeClient(),
        repository=repository,
        pipeline=_pipeline(),
    )

    assert processor.process_job_metadata(
        {
            "document_id": str(JOB_ID),
            "document_type": "JOB_DOCUMENT",
            "owner_id": str(EMPLOYER_ID),
        }
    ) == "processed"
    assert repository.claimed == (JOB_ID, EMPLOYER_ID)
    assert repository.completed["document_id"] == JOB_ID
    assert repository.completed["schema_version"] == JOB_PROFILE_SCHEMA_VERSION
    profile = repository.completed["profile_json"]
    assert profile["job_id"] == str(JOB_ID)
    assert profile["employer_id"] == str(EMPLOYER_ID)
    assert profile["required_skills"] == ["Python"]
    assert "source_text" not in profile


@pytest.mark.parametrize(
    "sensitive_requirement",
    [
        "The employee would benefit from flexible breaks.",
        "Work best with a low-stimulation environment.",
        "Quiet workspace and predictable routines are preferred.",
        "Accommodation is available for candidates with disabilities.",
        "Contact jane.doe@example.test for further information.",
    ],
)
def test_accessibility_or_contact_requirements_are_not_persisted(sensitive_requirement):
    repository = FakeProfileRepository()
    client = FakeClient()
    client.job_bytes = _docx_bytes(
        f"Required Skills\n- Python\n- {sensitive_requirement}"
    )
    processor = JobDocumentProcessor(
        client=client,
        repository=repository,
        pipeline=_pipeline(),
    )

    assert processor.process_job_metadata(
        {
            "document_id": str(JOB_ID),
            "document_type": "JOB_DOCUMENT",
            "owner_id": str(EMPLOYER_ID),
        }
    ) == "processed"
    assert sensitive_requirement not in json.dumps(repository.completed["profile_json"])
    assert repository.completed["profile_json"]["required_skills"] == ["Python"]


def test_job_groq_receives_only_parser_requirements_not_document_text():
    requests = []
    job_source = (
        "Job Title: Data Engineer\n"
        "Contact Jane Doe at jane.doe@example.test, +1 (415) 555-0188 "
        "https://example.test/jobs\n"
        "Required Skills\n- Python\n"
        "Responsibilities\n- Build reliable data pipelines"
    )
    job_enrichment = {
        "job_title": None,
        "role_summary": None,
        "requirement_enrichments": [
            {
                "original_requirement": "Python",
                "normalized_requirement": None,
                "normalized_skill": "python",
            },
            {
                "original_requirement": "Build reliable data pipelines",
                "normalized_requirement": None,
                "normalized_skill": None,
            },
        ],
    }

    def create(**kwargs):
        requests.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=json.dumps(job_enrichment),
                    )
                )
            ]
        )

    fake = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    processor = JobDocumentProcessor(
        client=FakeClient(),
        repository=FakeProfileRepository(),
        pipeline=_pipeline(
            extraction_client=GroqExtractionClient(api_key="mock-key", client=fake),
            enable_llm_extraction=True,
        ),
    )
    processor.client.job_bytes = _docx_bytes(job_source)
    processor.process_job_metadata(
        {
            "document_id": str(JOB_ID),
            "document_type": "JOB_DOCUMENT",
            "owner_id": str(EMPLOYER_ID),
        }
    )

    user_payload = requests[0]["messages"][1]["content"]
    assert "Job Title: Data Engineer" not in user_payload
    assert "Required Skills" not in user_payload
    assert "Responsibilities" not in user_payload
    for private_value in (
        "Jane Doe",
        "jane.doe@example.test",
        "+1 (415) 555-0188",
        "https://example.test/jobs",
    ):
        assert private_value not in user_payload
    assert "Python" in user_payload


@pytest.mark.parametrize(
    "sensitive_requirement",
    [
        "The employee would benefit from flexible breaks.",
        "Work best with a low-stimulation environment.",
        "Quiet workspace and predictable routines are preferred.",
    ],
)
def test_job_accessibility_text_fails_closed_before_mocked_groq(
    sensitive_requirement,
):
    requests = []
    fake = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda **kwargs: requests.append(kwargs)
            )
        )
    )
    client = FakeClient()
    client.job_bytes = _docx_bytes(
        f"Required Skills\n- Python\n- {sensitive_requirement}"
    )
    repository = FakeProfileRepository()
    processor = JobDocumentProcessor(
        client=client,
        repository=repository,
        pipeline=_pipeline(
            extraction_client=GroqExtractionClient(api_key="mock-key", client=fake),
            enable_llm_extraction=True,
        ),
    )

    assert processor.process_job_metadata(
        {
            "document_id": str(JOB_ID),
            "document_type": "JOB_DOCUMENT",
            "owner_id": str(EMPLOYER_ID),
        }
    ) == "processed"
    assert requests == []
    assert repository.completed["extraction_mode"] == "rule_based"
    assert repository.completed["llm_skipped_reason"] == "privacy_filter"
    assert sensitive_requirement not in json.dumps(repository.completed["profile_json"])


def test_dispatcher_continues_after_one_document_failure():
    class BrokenJobProcessor:
        def process_job_metadata(self, _document):
            raise RuntimeError("PRIVATE DOCUMENT BODY")

    class FakeResumeProcessor:
        def __init__(self):
            self.client = FakeClient()
            self.client.active_resumes = [
                {
                    "document_id": str(RESUME_ID),
                    "document_type": "RESUME",
                    "owner_id": str(CANDIDATE_ID),
                }
            ]

        def process_resume_metadata(self, _document):
            return "processed"

    dispatcher = DocumentProcessingDispatcher(
        resume_processor=FakeResumeProcessor(),
        job_processor=BrokenJobProcessor(),
    )

    assert dispatcher.process_pending_documents() == {
        "processed": 1,
        "skipped": 0,
        "failed": 1,
    }
