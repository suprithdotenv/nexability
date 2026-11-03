"""
Tests for the NexAbility ML matching service API.

Uses FastAPI TestClient with mocked InternalMLClient.
Covers:
- Authentication (valid key, missing key, wrong key)
- Missing / malformed X-Candidate-Id
- No résumé found for candidate
- No eligible jobs
- Fewer than 7 jobs → returns all
- More than 7 jobs → returns 7
- Correct response schema (no overall_score)
- Accessibility information never sent to Groq
- Accessibility has greater ranking weight than professional score
"""

from __future__ import annotations

import io
import os
import zipfile
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

try:
    from fastapi.testclient import TestClient
    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False

# Mark all tests to skip cleanly when FastAPI is not installed.
pytestmark = pytest.mark.skipif(
    not _FASTAPI_AVAILABLE, reason="fastapi and httpx are required for service tests"
)

if _FASTAPI_AVAILABLE:
    import nexability_ml.matching_service as svc

VALID_KEY = "test-internal-service-key-never-expose"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _docx_bytes(text: str) -> bytes:
    output = io.BytesIO()
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        + "".join(
            f"<w:p><w:r><w:t>{line}</w:t></w:r></w:p>" for line in text.splitlines()
        )
        + "</w:body></w:document>"
    )
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("word/document.xml", xml)
    return output.getvalue()


_RESUME_BYTES = _docx_bytes(
    "Jane Doe\nTECHNICAL SKILLS\nPython SQL\nPROJECTS\nBuilt Python tools."
)
_JOB_BYTES = _docx_bytes(
    "Job Title: Data Engineer\nRequired Skills\n- Python\n- SQL"
)

CANDIDATE_ID = "f0f7d526-37ec-4af5-bd2a-0ca90d8dcc62"
EMPLOYER_ID = "b1aa8ea9-782c-4c8f-afc2-d4e56075bb65"
JOB_ID = "d2f5e6a1-9b3c-4d8e-a7f2-c1e0b9a4d5f6"


def _make_resume_meta(candidate_id=CANDIDATE_ID):
    return {
        "document_id": "resume-doc-id-1",
        "document_type": "RESUME",
        "owner_id": candidate_id,
        "original_filename": "resume.docx",
        "mime_type": (
            "application/vnd.openxmlformats-officedocument"
            ".wordprocessingml.document"
        ),
        "file_size_bytes": len(_RESUME_BYTES),
    }


def _make_job_meta(job_id=JOB_ID, employer_id=EMPLOYER_ID):
    return {
        "document_id": job_id,
        "document_type": "JOB_DOCUMENT",
        "owner_id": employer_id,
        "original_filename": "job.docx",
        "mime_type": (
            "application/vnd.openxmlformats-officedocument"
            ".wordprocessingml.document"
        ),
        "file_size_bytes": len(_JOB_BYTES),
    }


def _make_queue(candidate_id=CANDIDATE_ID, n_jobs=1):
    return {
        "active_resumes": [_make_resume_meta(candidate_id)],
        "pending_job_documents": [
            _make_job_meta(f"job-{i}", f"emp-{i}") for i in range(n_jobs)
        ],
    }


@contextmanager
def _service_env(extra_env: dict | None = None):
    """Patch service env vars and yield a TestClient."""
    env = {
        "NEXABILITY_INTERNAL_ML_API_KEY": VALID_KEY,
        "NEXABILITY_BACKEND_URL": "https://backend.test",
        **(extra_env or {}),
    }
    with patch.dict(os.environ, env):
        yield TestClient(svc.app, raise_server_exceptions=False)


def _make_mock_client(queue=None, n_jobs=1):
    mock_client = MagicMock()
    mock_client.list_pending_documents.return_value = (
        queue if queue is not None else _make_queue(n_jobs=n_jobs)
    )
    mock_client.get_resume_content.return_value = _RESUME_BYTES
    mock_client.get_job_document_content.return_value = _JOB_BYTES
    mock_client.get_candidate_accessibility_preferences.return_value = []
    mock_client.get_employer_accessibility_profile.return_value = {
        "profile_completed": True,
        "capabilities": [],
    }
    return mock_client


def _fake_pipeline():
    from nexability_ml.embeddings import SimpleEmbeddingModel, WhitespaceTokenizer
    from nexability_ml.pipeline import NexAbilityMLPipeline

    return NexAbilityMLPipeline(
        embedding_model=SimpleEmbeddingModel(),
        tokenizer=WhitespaceTokenizer(),
        enable_llm_extraction=False,
    )


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


def test_missing_service_key_returns_401():
    with _service_env() as c:
        resp = c.get(
            "/api/v1/ml/matches",
            headers={"X-Candidate-Id": CANDIDATE_ID},
        )
    assert resp.status_code == 401


def test_wrong_service_key_returns_401():
    with _service_env() as c:
        resp = c.get(
            "/api/v1/ml/matches",
            headers={
                "X-Internal-Service-Key": "wrong-key",
                "X-Candidate-Id": CANDIDATE_ID,
            },
        )
    assert resp.status_code == 401


def test_unconfigured_service_key_returns_401():
    """Service with no key configured should reject ALL requests."""
    with patch.dict(os.environ, {"NEXABILITY_INTERNAL_ML_API_KEY": ""}):
        c = TestClient(svc.app, raise_server_exceptions=False)
        resp = c.get(
            "/api/v1/ml/matches",
            headers={
                "X-Internal-Service-Key": VALID_KEY,
                "X-Candidate-Id": CANDIDATE_ID,
            },
        )
    assert resp.status_code == 401


def test_missing_candidate_id_returns_400():
    with _service_env() as c:
        resp = c.get(
            "/api/v1/ml/matches",
            headers={"X-Internal-Service-Key": VALID_KEY},
        )
    assert resp.status_code == 400


def test_invalid_candidate_id_uuid_returns_400():
    with _service_env() as c:
        resp = c.get(
            "/api/v1/ml/matches",
            headers={
                "X-Internal-Service-Key": VALID_KEY,
                "X-Candidate-Id": "not-a-uuid",
            },
        )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# No résumé / no jobs scenarios
# ---------------------------------------------------------------------------


def test_no_resume_for_candidate_returns_resume_not_processed():
    queue_no_resume = {
        "active_resumes": [],
        "pending_job_documents": [_make_job_meta()],
    }
    mock_client = _make_mock_client(queue=queue_no_resume)

    with patch.object(svc, "_get_client", return_value=mock_client), \
         patch.object(svc, "_get_pipeline", return_value=_fake_pipeline()), \
         _service_env() as c:
        resp = c.get(
            "/api/v1/ml/matches",
            headers={
                "X-Internal-Service-Key": VALID_KEY,
                "X-Candidate-Id": CANDIDATE_ID,
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "resume_not_processed"
    assert data["match_count"] == 0
    assert data["top_matches"] == []


def test_no_jobs_returns_no_jobs_available():
    queue_no_jobs = {
        "active_resumes": [_make_resume_meta()],
        "pending_job_documents": [],
    }
    mock_client = _make_mock_client(queue=queue_no_jobs)

    with patch.object(svc, "_get_client", return_value=mock_client), \
         patch.object(svc, "_get_pipeline", return_value=_fake_pipeline()), \
         _service_env() as c:
        resp = c.get(
            "/api/v1/ml/matches",
            headers={
                "X-Internal-Service-Key": VALID_KEY,
                "X-Candidate-Id": CANDIDATE_ID,
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "no_jobs_available"
    assert data["match_count"] == 0


# ---------------------------------------------------------------------------
# Matching results schema
# ---------------------------------------------------------------------------


def _mock_full_run(n_jobs: int):
    """Run a complete fake match for n_jobs. Returns the Response object."""
    mock_client = _make_mock_client(n_jobs=n_jobs)
    fake_pl = _fake_pipeline()

    with patch.object(svc, "_get_client", return_value=mock_client), \
         patch.object(svc, "_get_pipeline", return_value=fake_pl), \
         _service_env() as c:
        resp = c.get(
            "/api/v1/ml/matches",
            headers={
                "X-Internal-Service-Key": VALID_KEY,
                "X-Candidate-Id": CANDIDATE_ID,
            },
        )
    return resp


def test_response_schema_contains_required_fields():
    resp = _mock_full_run(n_jobs=1)
    assert resp.status_code == 200
    data = resp.json()
    assert "candidate_id" in data
    assert "status" in data
    assert "match_count" in data
    assert "ranking_formula" in data
    assert "top_matches" in data


def test_fewer_than_7_jobs_returns_all():
    resp = _mock_full_run(n_jobs=3)
    assert resp.status_code == 200
    data = resp.json()
    assert data["match_count"] == 3
    assert len(data["top_matches"]) == 3


def test_more_than_7_jobs_returns_7():
    resp = _mock_full_run(n_jobs=10)
    assert resp.status_code == 200
    data = resp.json()
    assert data["match_count"] == 7
    assert len(data["top_matches"]) == 7


def test_response_has_no_overall_score_key():
    resp = _mock_full_run(n_jobs=2)
    assert resp.status_code == 200

    def all_keys(obj):
        if isinstance(obj, dict):
            yield from obj.keys()
            for v in obj.values():
                yield from all_keys(v)
        elif isinstance(obj, list):
            for item in obj:
                yield from all_keys(item)

    all_key_set = set(all_keys(resp.json()))
    assert "overall_score" not in all_key_set
    assert "overall_match_score" not in all_key_set


def test_each_match_has_separate_scores():
    resp = _mock_full_run(n_jobs=1)
    assert resp.status_code == 200
    match = resp.json()["top_matches"][0]
    assert "scores" in match
    scores = match["scores"]
    assert "accessibility_compatibility" in scores
    assert "professional_match_score" in scores
    assert "ranking_score" in scores
    assert "overall_score" not in scores


def test_ranks_are_numbered_starting_from_1():
    resp = _mock_full_run(n_jobs=3)
    assert resp.status_code == 200
    ranks = [m["rank"] for m in resp.json()["top_matches"]]
    assert ranks == [1, 2, 3]


def test_ranking_formula_is_documented_in_response():
    resp = _mock_full_run(n_jobs=1)
    assert resp.status_code == 200
    formula = resp.json()["ranking_formula"]
    assert "60%" in formula or "0.6" in formula or "accessibility" in formula.lower()


def test_match_status_is_match_found_when_results_exist():
    resp = _mock_full_run(n_jobs=1)
    assert resp.status_code == 200
    assert resp.json()["status"] == "match_found"


def test_health_endpoint_returns_ok():
    c = TestClient(svc.app)
    resp = c.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Accessibility isolation — not forwarded to pipeline/Groq
# ---------------------------------------------------------------------------


def test_accessibility_data_is_fetched_but_not_forwarded_to_pipeline():
    """
    Accessibility preferences must be retrieved for matching but must never
    appear inside the document pipeline (which may call Groq for extraction).
    """
    pipeline_calls: list[dict] = []
    fake_pl = _fake_pipeline()
    original_resume = fake_pl.process_resume_document
    original_job = fake_pl.process_job_document

    def spy_resume(**kwargs):
        pipeline_calls.append({"type": "resume", "kwargs": str(kwargs)})
        return original_resume(**kwargs)

    def spy_job(**kwargs):
        pipeline_calls.append({"type": "job", "kwargs": str(kwargs)})
        return original_job(**kwargs)

    fake_pl.process_resume_document = spy_resume
    fake_pl.process_job_document = spy_job

    PRIVATE_ACCESSIBILITY = "private_accessibility_requirement_must_not_reach_pipeline"

    mock_client = _make_mock_client(n_jobs=1)
    mock_client.get_candidate_accessibility_preferences.return_value = [
        {"category": "SCREEN_READER", "preference": PRIVATE_ACCESSIBILITY}
    ]

    with patch.object(svc, "_get_client", return_value=mock_client), \
         patch.object(svc, "_get_pipeline", return_value=fake_pl), \
         _service_env() as c:
        resp = c.get(
            "/api/v1/ml/matches",
            headers={
                "X-Internal-Service-Key": VALID_KEY,
                "X-Candidate-Id": CANDIDATE_ID,
            },
        )

    assert resp.status_code == 200
    all_kwargs_str = str(pipeline_calls)
    assert PRIVATE_ACCESSIBILITY not in all_kwargs_str


def test_accessibility_influences_ranking_score():
    """
    Confirmed accessibility must produce accessibility_compatibility == 100
    and ranking_score >= 60 (the 60% weight floor from full accessibility match).
    """
    mock_client = _make_mock_client(n_jobs=1)
    mock_client.get_candidate_accessibility_preferences.return_value = [
        {
            "category": "SCREEN_READER",
            "preference": "Screen reader support",
            "is_active": True,
        }
    ]
    mock_client.get_employer_accessibility_profile.return_value = {
        "profile_completed": True,
        "capabilities": [
            {
                "category": "SCREEN_READER",
                "capability": "Screen reader support",
                "status": "AVAILABLE",
            }
        ],
    }

    with patch.object(svc, "_get_client", return_value=mock_client), \
         patch.object(svc, "_get_pipeline", return_value=_fake_pipeline()), \
         _service_env() as c:
        resp = c.get(
            "/api/v1/ml/matches",
            headers={
                "X-Internal-Service-Key": VALID_KEY,
                "X-Candidate-Id": CANDIDATE_ID,
            },
        )

    assert resp.status_code == 200
    match = resp.json()["top_matches"][0]
    assert match["scores"]["accessibility_compatibility"] == 100.0
    assert match["scores"]["ranking_score"] >= 60.0
