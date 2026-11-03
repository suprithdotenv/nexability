"""
backend/app/services/matching/ml_matching_service.py
=====================================================

Backend service that coordinates candidate match requests.
Proxies candidate match requests to the standalone ML service on port 8001.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class MLServiceUnavailableError(RuntimeError):
    """Raised when the ML matching service cannot be reached."""


class MLServiceError(RuntimeError):
    """Raised when the ML service returns an unexpected error response."""


def request_matches(
    candidate_profile_id: str,
    *,
    force_reprocess: bool = False,
    min_threshold: float = 60.0,
    timeout_seconds: float = 60.0,
) -> dict[str, Any]:
    """
    Call the ML matching service and return the parsed JSON response.
    """
    url = f"{settings.ML_SERVICE_URL.rstrip('/')}/api/v1/ml/matches"
    headers = {
        "X-Internal-Service-Key": settings.INTERNAL_ML_API_KEY,
        "X-Candidate-Id": candidate_profile_id,
    }
    params: dict[str, str] = {
        "min_threshold": str(min_threshold),
    }
    if force_reprocess:
        params["force_reprocess"] = "true"

    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.get(url, headers=headers, params=params)
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        logger.warning("ML matching service unreachable: %s", exc)
        raise MLServiceUnavailableError(
            "The ML matching service is currently unavailable."
        ) from exc

    if response.status_code == 404:
        return {
            "candidate_id": candidate_profile_id,
            "status": "no_resume",
            "match_count": 0,
            "ranking_formula": "Ranked by professional compatibility. Accessibility evaluated separately.",
            "ranking_strategy": "professional_compatibility_first",
            "top_matches": [],
        }

    if response.status_code >= 400:
        logger.error(
            "ML service returned %d for candidate %s",
            response.status_code,
            candidate_profile_id,
        )
        raise MLServiceError(
            f"ML service returned status {response.status_code}."
        )

    return response.json()
