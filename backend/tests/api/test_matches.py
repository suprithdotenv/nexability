"""
Tests for GET /api/v1/candidates/me/matches

Covers:
- Authentication and authorization (401/403 for wrong roles)
- Successful match response passthrough from ML service (mocked)
- ML service unavailable → 503
- ML service error → 502
- No active résumé → 404
- No jobs available (empty match list)
- force_reprocess query parameter forwarded
- Ranking scores kept separate (no overall_score)
- Response schema validation
"""
from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.matching.ml_matching_service import (
    MLServiceError,
    MLServiceUnavailableError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_MATCH_PAYLOAD = {
    "candidate_id": str(uuid.uuid4()),
    "status": "match_found",
    "match_count": 2,
    "ranking_formula": "ranking_score = 60% × accessibility_compatibility + 40% × professional_match_score",
    "top_matches": [
        {
            "rank": 1,
            "job_id": str(uuid.uuid4()),
            "employer_id": str(uuid.uuid4()),
            "job_title": "Senior Python Engineer",
            "scores": {
                "accessibility_compatibility": 100.0,
                "professional_match_score": 83.33,
                "ranking_score": 93.33,
                "accessibility_note": "2_requirements_evaluated",
                "ranking_formula": "ranking_score = 60% × accessibility_compatibility + 40% × professional_match_score",
            },
            "professional_match": {
                "professional_evidence_score": {
                    "status": "available",
                    "value": 83.33,
                }
            },
            "accessibility_match": {
                "requirements": [
                    {"need": "screen_reader", "status": "confirmed"},
                    {"need": "flexible_hours", "status": "confirmed"},
                ]
            },
        },
        {
            "rank": 2,
            "job_id": str(uuid.uuid4()),
            "employer_id": str(uuid.uuid4()),
            "job_title": "Backend Developer",
            "scores": {
                "accessibility_compatibility": 60.0,
                "professional_match_score": 50.0,
                "ranking_score": 56.0,
                "accessibility_note": "1_requirements_evaluated",
                "ranking_formula": "ranking_score = 60% × accessibility_compatibility + 40% × professional_match_score",
            },
            "professional_match": {
                "professional_evidence_score": {
                    "status": "available",
                    "value": 50.0,
                }
            },
            "accessibility_match": {
                "requirements": [
                    {"need": "screen_reader", "status": "unverified"},
                ]
            },
        },
    ],
}

_NO_JOBS_PAYLOAD = {
    "candidate_id": str(uuid.uuid4()),
    "status": "no_jobs_available",
    "match_count": 0,
    "ranking_formula": "ranking_score = 60% × accessibility_compatibility + 40% × professional_match_score",
    "top_matches": [],
}

MATCHES_URL = "/api/v1/candidates/me/matches"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_unauthenticated_request_is_rejected(client: TestClient):
    """No token → 401 or 403."""
    res = client.get(MATCHES_URL)
    assert res.status_code in (401, 403)


def test_employer_cannot_call_matches(client: TestClient, create_employer):
    """EMPLOYER role must not access candidate match endpoint."""
    emp = create_employer()
    res = client.get(MATCHES_URL, headers=emp["headers"])
    assert res.status_code == 403


def test_successful_match_response(client: TestClient, create_candidate):
    """Happy path: ML service returns matches, backend passes them through."""
    cand = create_candidate()

    with patch(
        "app.api.v1.endpoints.matches.request_matches",
        return_value=_VALID_MATCH_PAYLOAD,
    ):
        res = client.get(MATCHES_URL, headers=cand["headers"])

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "match_found"
    assert data["match_count"] == 2
    assert len(data["top_matches"]) == 2


def test_match_response_has_no_overall_score(client: TestClient, create_candidate):
    """The response must never contain an 'overall_score' key at any level."""
    cand = create_candidate()

    with patch(
        "app.api.v1.endpoints.matches.request_matches",
        return_value=_VALID_MATCH_PAYLOAD,
    ):
        res = client.get(MATCHES_URL, headers=cand["headers"])

    assert res.status_code == 200
    import json

    raw = json.dumps(res.json())
    assert "overall_score" not in raw


def test_accessibility_and_professional_scores_are_separate(
    client: TestClient, create_candidate
):
    """Both component scores must be present and separate in every match."""
    cand = create_candidate()

    with patch(
        "app.api.v1.endpoints.matches.request_matches",
        return_value=_VALID_MATCH_PAYLOAD,
    ):
        res = client.get(MATCHES_URL, headers=cand["headers"])

    assert res.status_code == 200
    for match in res.json()["top_matches"]:
        scores = match["scores"]
        assert "accessibility_compatibility" in scores
        assert "professional_match_score" in scores
        assert "ranking_score" in scores
        assert scores["ranking_score"] != scores["accessibility_compatibility"]
        assert scores["ranking_score"] != scores["professional_match_score"]


def test_matches_are_sorted_by_ranking_score_descending(
    client: TestClient, create_candidate
):
    """Matches must be returned in descending ranking_score order."""
    cand = create_candidate()

    with patch(
        "app.api.v1.endpoints.matches.request_matches",
        return_value=_VALID_MATCH_PAYLOAD,
    ):
        res = client.get(MATCHES_URL, headers=cand["headers"])

    assert res.status_code == 200
    scores = [m["scores"]["ranking_score"] for m in res.json()["top_matches"]]
    assert scores == sorted(scores, reverse=True)


def test_ml_service_unavailable_returns_503(client: TestClient, create_candidate):
    """If the ML service is down, the backend returns 503."""
    cand = create_candidate()

    with patch(
        "app.api.v1.endpoints.matches.request_matches",
        side_effect=MLServiceUnavailableError("ML service is down"),
    ):
        res = client.get(MATCHES_URL, headers=cand["headers"])

    assert res.status_code == 503
    # The detail is the forwarded exception message
    assert res.json()["detail"]


def test_ml_service_error_returns_502(client: TestClient, create_candidate):
    """If the ML service returns a 5xx error, the backend returns 502."""
    cand = create_candidate()

    with patch(
        "app.api.v1.endpoints.matches.request_matches",
        side_effect=MLServiceError("ML service returned status 500"),
    ):
        res = client.get(MATCHES_URL, headers=cand["headers"])

    assert res.status_code == 502


def test_no_resume_returns_404(client: TestClient, create_candidate):
    """If the candidate has no active résumé, return 404 with a helpful message."""
    cand = create_candidate()

    with patch(
        "app.api.v1.endpoints.matches.request_matches",
        return_value={
            "candidate_id": str(uuid.uuid4()),
            "status": "no_resume",
            "match_count": 0,
            "ranking_formula": "",
            "top_matches": [],
        },
    ):
        res = client.get(MATCHES_URL, headers=cand["headers"])

    assert res.status_code == 404
    assert "résumé" in res.json()["detail"].lower() or "resume" in res.json()["detail"].lower()


def test_no_jobs_available_returns_empty_list(client: TestClient, create_candidate):
    """If no jobs are in the system, return an empty match list (not an error)."""
    cand = create_candidate()

    with patch(
        "app.api.v1.endpoints.matches.request_matches",
        return_value=_NO_JOBS_PAYLOAD,
    ):
        res = client.get(MATCHES_URL, headers=cand["headers"])

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "no_jobs_available"
    assert data["match_count"] == 0
    assert data["top_matches"] == []


def test_force_reprocess_is_forwarded(client: TestClient, create_candidate):
    """force_reprocess=true must be forwarded to the ML service."""
    cand = create_candidate()
    captured: list[dict] = []

    def _mock_request(candidate_id, *, force_reprocess=False, **kwargs):
        captured.append({"force_reprocess": force_reprocess})
        return _VALID_MATCH_PAYLOAD

    with patch(
        "app.api.v1.endpoints.matches.request_matches",
        side_effect=_mock_request,
    ):
        res = client.get(
            MATCHES_URL + "?force_reprocess=true", headers=cand["headers"]
        )

    assert res.status_code == 200
    assert captured[0]["force_reprocess"] is True


def test_ranking_formula_is_in_response(client: TestClient, create_candidate):
    """ranking_formula must be present in the response root."""
    cand = create_candidate()

    with patch(
        "app.api.v1.endpoints.matches.request_matches",
        return_value=_VALID_MATCH_PAYLOAD,
    ):
        res = client.get(MATCHES_URL, headers=cand["headers"])

    assert res.status_code == 200
    assert "ranking_formula" in res.json()
    assert "60%" in res.json()["ranking_formula"]


def test_ranks_are_1_indexed_and_sequential(client: TestClient, create_candidate):
    """Ranks must start at 1 and increase by 1."""
    cand = create_candidate()

    with patch(
        "app.api.v1.endpoints.matches.request_matches",
        return_value=_VALID_MATCH_PAYLOAD,
    ):
        res = client.get(MATCHES_URL, headers=cand["headers"])

    assert res.status_code == 200
    ranks = [m["rank"] for m in res.json()["top_matches"]]
    assert ranks == list(range(1, len(ranks) + 1))
