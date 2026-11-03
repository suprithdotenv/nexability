from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

import pytest
from pydantic import ValidationError

from nexability_ml.api_client import InternalMLClient
from nexability_ml.embeddings import SimpleEmbeddingModel, WhitespaceTokenizer
from nexability_ml.groq_extraction import GroqExtractionClient
from nexability_ml.parser import parse_document_bytes
from nexability_ml.pipeline import NexAbilityMLPipeline
from nexability_ml.resume_processing import (
    RESUME_PROFILE_SCHEMA_VERSION,
    ResumeExtractionProcessor,
    ResumeProcessingError,
    validate_resume_profile,
)
from nexability_ml.schemas import ResumeExtraction

RESUME_ID = UUID("b1aa8ea9-782c-4c8f-afc2-d4e56075bb65")
CANDIDATE_ID = UUID("f0f7d526-37ec-4af5-bd2a-0ca90d8dcc62")


def _docx_bytes(text: str) -> bytes:
    import io
    import zipfile

    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body><w:p><w:r><w:t>" + text + "</w:t></w:r></w:p></w:body></w:document>"
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("word/document.xml", xml)
    return output.getvalue()


class FakeRepository:
    def __init__(self):
        self.status = None
        self.attempt = 0
        self.completed = None
        self.failure = None
        self.candidate_profile_id = None
        self.resume_id = None

    def claim(self, candidate_profile_id, resume_id, *, force=False):
        self.candidate_profile_id = candidate_profile_id
        self.resume_id = resume_id
        if self.status == "SUCCEEDED" and not force:
            return None
        self.attempt += 1
        self.status = "PROCESSING"
        return self.attempt

    def complete(
        self,
        resume_id,
        attempt,
        *,
        profile_json,
        provider,
        model,
        schema_version,
        extraction_mode,
        llm_skipped_reason,
    ):
        self.completed = {
            "resume_id": resume_id,
            "attempt": attempt,
            "profile_json": profile_json,
            "provider": provider,
            "model": model,
            "schema_version": schema_version,
            "extraction_mode": extraction_mode,
            "llm_skipped_reason": llm_skipped_reason,
        }
        self.status = "SUCCEEDED"

    def fail(self, resume_id, attempt, *, error_details):
        self.failure = {
            "resume_id": resume_id,
            "attempt": attempt,
            "error_details": error_details,
        }
        self.status = "FAILED"


class FakeClient:
    def __init__(self, content=None):
        self.content = content or _docx_bytes(
            "Jane Doe\nTECHNICAL SKILLS\nPython\nEXPERIENCE\nBuilt Python services."
        )

    def list_pending_documents(self):
        return {
            "pending_job_documents": [],
            "active_resumes": [self.metadata(RESUME_ID, CANDIDATE_ID)],
        }

    def get_resume_metadata(self, resume_id):
        return self.metadata(UUID(resume_id), CANDIDATE_ID)

    def get_resume_content(self, resume_id):
        return self.content

    @staticmethod
    def metadata(resume_id, candidate_id):
        return {
            "document_id": str(resume_id),
            "document_type": "RESUME",
            "owner_id": str(candidate_id),
            "original_filename": "resume.docx",
            "mime_type": (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ),
        }


def _pipeline(extraction_client=None):
    return NexAbilityMLPipeline(
        embedding_model=SimpleEmbeddingModel(),
        tokenizer=WhitespaceTokenizer(),
        extraction_client=extraction_client,
        enable_llm_extraction=extraction_client is not None,
    )


def test_docx_extraction_is_processed_and_persisted_for_exact_resume():
    repo = FakeRepository()
    processor = ResumeExtractionProcessor(
        client=FakeClient(),
        repository=repo,
        pipeline=_pipeline(),
    )

    counts = processor.process_pending_resumes()

    assert counts == {"processed": 1, "skipped": 0, "failed": 0}
    assert repo.completed["resume_id"] == RESUME_ID
    assert repo.completed["schema_version"] == RESUME_PROFILE_SCHEMA_VERSION
    assert repo.completed["profile_json"]["full_name"] is None
    assert repo.completed["profile_json"]["skills"][0]["name"] == "python"
    assert repo.completed["profile_json"]["skills"][0]["evidence"] == [
        "Python",
        "Built Python services.",
    ]
    assert repo.status == "SUCCEEDED"


def test_pdf_extraction_uses_existing_parser_without_ocr(monkeypatch):
    def fake_reader(_stream):
        return SimpleNamespace(
            pages=[SimpleNamespace(extract_text=lambda: "Jane Doe\nPython Developer")]
        )

    monkeypatch.setitem(
        __import__("sys").modules,
        "pypdf",
        SimpleNamespace(PdfReader=fake_reader),
    )
    result = parse_document_bytes(b"%PDF-1.4", "resume.pdf", "application/pdf")

    assert result.text == "Jane Doe\nPython Developer"
    assert result.is_scanned is False


def test_mocked_groq_payload_redacts_identifiers_and_nulls_unverified_identity():
    request_payloads = []
    profile = {
        "full_name": "Forged Name",
        "email": "forged@example.test",
        "phone": "+1 212 555 0199",
        "location": None,
        "professional_summary": None,
        "skills": [{"name": "Python", "category": None, "evidence": ["Built Python APIs."]}],
        "experience": [],
        "education": [],
        "certifications": [],
    }

    def create(**kwargs):
        request_payloads.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=__import__("json").dumps(profile)
                    )
                )
            ]
        )

    fake = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=create),
        )
    )
    extraction_client = GroqExtractionClient(api_key="unit-test-key", client=fake)
    pipeline = _pipeline(extraction_client)
    repo = FakeRepository()
    processor = ResumeExtractionProcessor(
        client=FakeClient(
            _docx_bytes(
                "Jane Doe\njane.doe@example.test\n"
                "+1 (415) 555-0188\nhttps://example.test/jane\n"
                "Summary\nPrivate summary not for Groq\n"
                "TECHNICAL SKILLS\nPython\n"
                "Contact Jane Doe jane.doe@example.test +1 (415) 555-0188 "
                "https://example.test/profile\n"
                "EXPERIENCE\nBuilt Python APIs.\n"
                "References\nJane Doe\nLanguages\nEnglish"
            )
        ),
        repository=repo,
        pipeline=pipeline,
    )

    assert processor.process_pending_resumes()["processed"] == 1
    sent_text = request_payloads[0]["messages"][1]["content"]
    for private_value in (
        "Jane Doe",
        "Private summary not for Groq",
        "English",
        "jane.doe@example.test",
        "+1 (415) 555-0188",
        "https://example.test/jane",
    ):
        assert private_value not in sent_text
    assert repo.completed["provider"] == "groq"
    assert repo.completed["profile_json"]["full_name"] is None
    assert repo.completed["profile_json"]["email"] is None
    assert repo.completed["profile_json"]["phone"] is None
    assert repo.completed["profile_json"]["skills"][0]["evidence"] == ["Built Python APIs."]


@pytest.mark.parametrize(
    "sensitive_line",
    [
        "I work best with predictable routines and a low-stimulation environment.",
        "The employee would benefit from flexible breaks during the workday.",
        "Need a quiet workspace and reduced sensory interruptions.",
    ],
)
def test_indirect_accommodation_fails_closed_to_rule_based(sensitive_line):
    request_payloads = []
    fake = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda **kwargs: request_payloads.append(kwargs)
            )
        )
    )
    repository = FakeRepository()
    processor = ResumeExtractionProcessor(
        client=FakeClient(
            _docx_bytes(
                "TECHNICAL SKILLS\nPython\nEXPERIENCE\n"
                f"Built Python services. {sensitive_line}"
            )
        ),
        repository=repository,
        pipeline=_pipeline(GroqExtractionClient(api_key="unit-test-key", client=fake)),
    )

    assert processor.process_pending_resumes() == {
        "processed": 1,
        "skipped": 0,
        "failed": 0,
    }
    assert request_payloads == []
    assert repository.completed["provider"] == "rule_based"
    assert repository.completed["extraction_mode"] == "rule_based"
    assert repository.completed["llm_skipped_reason"] == "privacy_filter"
    assert sensitive_line.casefold() not in repr(
        repository.completed["profile_json"]
    ).casefold()


def test_worker_only_processes_active_resume_queue():
    repository = FakeRepository()
    client = FakeClient()
    client.list_pending_documents = lambda: {
        "pending_job_documents": [
            {
                "document_id": "unused-job-document",
                "document_type": "JOB_DOCUMENT",
                "owner_id": str(CANDIDATE_ID),
            }
        ],
        "active_resumes": [FakeClient.metadata(RESUME_ID, CANDIDATE_ID)],
    }
    processor = ResumeExtractionProcessor(
        client=client,
        repository=repository,
        pipeline=_pipeline(),
    )

    assert processor.process_pending_resumes()["processed"] == 1
    assert repository.resume_id == RESUME_ID


def test_invalid_profile_schema_is_rejected():
    with pytest.raises(ResumeProcessingError, match="profile_validation_failed"):
        validate_resume_profile(
            {
                "extraction_mode": "llm",
                "llm_extraction": {"unexpected": True},
            }
        )

    with pytest.raises(ValidationError):
        ResumeExtraction.model_validate({"unexpected": True})


def test_failure_is_recorded_without_exception_text_and_retry_can_succeed(caplog):
    repo = FakeRepository()

    class BrokenClient(FakeClient):
        def get_resume_content(self, _resume_id):
            raise RuntimeError("PRIVATE TOKEN SHOULD NOT BE SAVED")

    processor = ResumeExtractionProcessor(
        client=BrokenClient(),
        repository=repo,
        pipeline=_pipeline(),
    )
    queued = FakeClient.metadata(RESUME_ID, CANDIDATE_ID)

    assert processor.process_resume_metadata(queued) == "failed"
    assert repo.failure["error_details"] == "download_runtimeerror"
    assert "PRIVATE TOKEN SHOULD NOT BE SAVED" not in str(repo.failure)
    assert "PRIVATE TOKEN SHOULD NOT BE SAVED" not in caplog.text

    processor.client = FakeClient()
    assert processor.process_resume_metadata(queued) == "processed"
    assert repo.attempt == 2


def test_succeeded_resume_is_not_processed_twice_without_force():
    repo = FakeRepository()
    processor = ResumeExtractionProcessor(
        client=FakeClient(),
        repository=repo,
        pipeline=_pipeline(),
    )
    queued = FakeClient.metadata(RESUME_ID, CANDIDATE_ID)

    assert processor.process_resume_metadata(queued) == "processed"
    assert processor.process_resume_metadata(queued) == "skipped"
    assert processor.process_resume_metadata(queued, force=True) == "processed"
    assert repo.attempt == 2


def test_internal_client_authenticates_existing_retrieval_requests(monkeypatch):
    requests = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return b"content"

    def fake_urlopen(req):
        requests.append(req)
        return FakeResponse()

    monkeypatch.setattr("nexability_ml.api_client.request.urlopen", fake_urlopen)
    client = InternalMLClient("https://backend.invalid", api_key="unit-test-internal-key")
    assert client.get_resume_content(str(RESUME_ID)) == b"content"
    assert requests[0].get_header("X-internal-service-key") == "unit-test-internal-key"
    assert requests[0].full_url.endswith(
        f"/api/v1/internal/ml/resumes/{RESUME_ID}/content"
    )


def test_internal_client_http_errors_do_not_expose_url_or_response(monkeypatch):
    from urllib.error import HTTPError

    def fake_urlopen(req):
        raise HTTPError(
            req.full_url,
            403,
            "PRIVATE RESPONSE BODY AND SIGNED URL",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr("nexability_ml.api_client.request.urlopen", fake_urlopen)
    client = InternalMLClient(
        "https://user:private-password@backend.invalid",
        api_key="private-internal-key",
    )

    with pytest.raises(RuntimeError) as error_info:
        client.get_resume_metadata(str(RESUME_ID))

    error_message = str(error_info.value)
    for private_value in (
        "PRIVATE RESPONSE BODY",
        "user:private-password",
        "private-internal-key",
    ):
        assert private_value not in error_message
    assert error_info.value.__suppress_context__ is True
