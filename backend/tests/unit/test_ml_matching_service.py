"""
Unit tests for app/services/matching/ml_matching_service.py

Tests the HTTP client wrapper that calls the ML matching service.
All HTTP calls are intercepted with httpx.MockTransport — no live network.
"""
from __future__ import annotations

import json
from unittest.mock import patch

import httpx
import pytest

from app.services.matching.ml_matching_service import (
    MLServiceError,
    MLServiceUnavailableError,
    request_matches,
)


CANDIDATE_ID = "3fa85f64-5717-4562-b3fc-2c963f66afa6"

_GOOD_PAYLOAD = {
    "candidate_id": CANDIDATE_ID,
    "status": "match_found",
    "match_count": 1,
    "ranking_formula": "ranking_score = 60% × accessibility_compatibility + 40% × professional_match_score",
    "top_matches": [
        {
            "rank": 1,
            "job_id": "abc",
            "employer_id": "emp1",
            "job_title": "Engineer",
            "scores": {
                "accessibility_compatibility": 100.0,
                "professional_match_score": 75.0,
                "ranking_score": 90.0,
                "accessibility_note": "no_requirements",
                "ranking_formula": "...",
            },
            "professional_match": {},
            "accessibility_match": {"requirements": []},
        }
    ],
}


def _make_mock_transport(status_code: int, body: dict | None = None) -> httpx.MockTransport:
    def _handler(request: httpx.Request) -> httpx.Response:
        content = json.dumps(body or {}).encode()
        return httpx.Response(status_code, content=content)

    return httpx.MockTransport(_handler)


def test_successful_response_is_returned():
    """A 200 response from the ML service is returned as a dict."""
    transport = _make_mock_transport(200, _GOOD_PAYLOAD)
    with patch("app.services.matching.ml_matching_service.httpx.Client") as mock_cls:
        mock_cls.return_value.__enter__.return_value.get.return_value = httpx.Response(
            200, json=_GOOD_PAYLOAD
        )
        result = request_matches(CANDIDATE_ID)

    assert result["status"] == "match_found"
    assert result["match_count"] == 1


def test_internal_service_key_is_sent_in_header():
    """The X-Internal-Service-Key and X-Candidate-Id headers must be sent."""
    sent_headers: dict = {}

    def _capture_get(url, *, headers=None, params=None, **kwargs):
        sent_headers.update(headers or {})
        return httpx.Response(200, json=_GOOD_PAYLOAD)

    with patch("app.services.matching.ml_matching_service.httpx.Client") as mock_cls:
        mock_cls.return_value.__enter__.return_value.get.side_effect = _capture_get
        request_matches(CANDIDATE_ID)

    assert "X-Internal-Service-Key" in sent_headers
    assert sent_headers["X-Candidate-Id"] == CANDIDATE_ID


def test_404_from_ml_service_returns_no_resume_dict():
    """A 404 from ML (no active résumé) should return a clean no_resume dict."""
    with patch("app.services.matching.ml_matching_service.httpx.Client") as mock_cls:
        mock_cls.return_value.__enter__.return_value.get.return_value = httpx.Response(
            404, json={"detail": "Active résumé not found for the candidate."}
        )
        result = request_matches(CANDIDATE_ID)

    assert result["status"] == "no_resume"
    assert result["match_count"] == 0
    assert result["top_matches"] == []


def test_503_from_ml_service_raises_ml_service_error():
    """A 5xx from ML raises MLServiceError."""
    with patch("app.services.matching.ml_matching_service.httpx.Client") as mock_cls:
        mock_cls.return_value.__enter__.return_value.get.return_value = httpx.Response(
            503, json={"detail": "Backend unreachable"}
        )
        with pytest.raises(MLServiceError):
            request_matches(CANDIDATE_ID)


def test_connect_error_raises_ml_service_unavailable():
    """A network connection error raises MLServiceUnavailableError."""
    with patch("app.services.matching.ml_matching_service.httpx.Client") as mock_cls:
        mock_cls.return_value.__enter__.return_value.get.side_effect = httpx.ConnectError(
            "Connection refused"
        )
        with pytest.raises(MLServiceUnavailableError):
            request_matches(CANDIDATE_ID)


def test_timeout_raises_ml_service_unavailable():
    """A timeout raises MLServiceUnavailableError."""
    with patch("app.services.matching.ml_matching_service.httpx.Client") as mock_cls:
        mock_cls.return_value.__enter__.return_value.get.side_effect = httpx.TimeoutException(
            "Timeout"
        )
        with pytest.raises(MLServiceUnavailableError):
            request_matches(CANDIDATE_ID)


def test_force_reprocess_is_added_to_params():
    """When force_reprocess=True, the query param must be forwarded."""
    sent_params: dict = {}

    def _capture_get(url, *, headers=None, params=None, **kwargs):
        sent_params.update(params or {})
        return httpx.Response(200, json=_GOOD_PAYLOAD)

    with patch("app.services.matching.ml_matching_service.httpx.Client") as mock_cls:
        mock_cls.return_value.__enter__.return_value.get.side_effect = _capture_get
        request_matches(CANDIDATE_ID, force_reprocess=True)

    assert sent_params.get("force_reprocess") == "true"


def test_force_reprocess_false_sends_no_param():
    """When force_reprocess=False (default), the param should not be sent."""
    sent_params: dict = {}

    def _capture_get(url, *, headers=None, params=None, **kwargs):
        sent_params.update(params or {})
        return httpx.Response(200, json=_GOOD_PAYLOAD)

    with patch("app.services.matching.ml_matching_service.httpx.Client") as mock_cls:
        mock_cls.return_value.__enter__.return_value.get.side_effect = _capture_get
        request_matches(CANDIDATE_ID, force_reprocess=False)

    assert "force_reprocess" not in sent_params
