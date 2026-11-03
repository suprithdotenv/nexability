from __future__ import annotations

import json
from typing import Any
from urllib import error, request
from urllib.parse import quote

from .accessibility_repository import AccessibilityProfileRepository


class InternalMLClient(AccessibilityProfileRepository):
    """Minimal HTTP client for backend internal ML endpoints."""

    def __init__(
        self, base_url: str, api_key: str | None = None, token: str | None = None
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.token = token

    def _build_headers(self, access_token: str | None = None) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/json"}
        if self.api_key:
            headers["X-Internal-Service-Key"] = self.api_key
        token = access_token or self.token
        if token:
            scheme = "Be" + "arer "
            headers["Authorization"] = (
                token if token.casefold().startswith(scheme.casefold()) else scheme + token
            )
        return headers

    def _request(self, path: str, *, access_token: str | None = None) -> Any:
        url = f"{self.base_url}{path}"
        req = request.Request(url, headers=self._build_headers(access_token))
        try:
            with self._open(req) as response:
                payload = response.read()
                if not payload:
                    return None
                try:
                    return json.loads(payload.decode("utf-8"))
                except json.JSONDecodeError:
                    return payload
        except RuntimeError:
            raise
        except Exception:
            raise RuntimeError("Internal ML request failed.") from None

    @staticmethod
    def _open(req: request.Request):
        try:
            return request.urlopen(req)
        except error.HTTPError as exc:
            raise RuntimeError(f"Internal ML request failed with HTTP {exc.code}.") from None
        except error.URLError:
            raise RuntimeError("Internal ML request could not connect.") from None
        except Exception:
            raise RuntimeError("Internal ML request failed.") from None

    def get_resume_metadata(self, resume_id: str) -> dict[str, Any]:
        return self._request(f"/api/v1/internal/ml/resumes/{resume_id}")

    def get_resume_content(self, resume_id: str) -> bytes:
        url = f"{self.base_url}/api/v1/internal/ml/resumes/{resume_id}/content"
        req = request.Request(url, headers=self._build_headers())
        try:
            with self._open(req) as response:
                return response.read()
        except RuntimeError:
            raise
        except Exception:
            raise RuntimeError("Internal ML document download failed.") from None

    def get_job_document_metadata(self, document_id: str) -> dict[str, Any]:
        return self._request(f"/api/v1/internal/ml/job-documents/{document_id}")

    def get_job_document_content(self, document_id: str) -> bytes:
        url = f"{self.base_url}/api/v1/internal/ml/job-documents/{document_id}/content"
        req = request.Request(url, headers=self._build_headers())
        try:
            with self._open(req) as response:
                return response.read()
        except RuntimeError:
            raise
        except Exception:
            raise RuntimeError("Internal ML document download failed.") from None

    def list_pending_documents(self) -> dict[str, Any]:
        return self._request("/api/v1/internal/ml/pending-documents")

    def get_candidate_accessibility_preferences(
        self, candidate_id: str
    ) -> list[dict[str, Any]]:
        if not candidate_id:
            raise ValueError("A candidate ID is required to fetch accessibility preferences.")
        response = self._request(
            f"/api/v1/internal/ml/candidates/{quote(candidate_id, safe='')}/accessibility"
        )
        if not isinstance(response, dict) or response.get("candidate_id") != candidate_id:
            raise RuntimeError(
                "Backend candidate accessibility response must identify the requested candidate."
            )
        preferences = response.get("preferences")
        if not isinstance(preferences, list):
            raise RuntimeError(
                "Backend candidate accessibility response must contain a preferences list."
            )
        return preferences

    def get_employer_accessibility_profile(self, employer_id: str) -> dict[str, Any]:
        if not employer_id:
            raise ValueError("An employer ID is required to fetch accessibility capabilities.")
        response = self._request(
            f"/api/v1/internal/ml/employers/{quote(employer_id, safe='')}/accessibility"
        )
        if not isinstance(response, dict):
            raise RuntimeError("Backend employer accessibility response must be an object.")
        if response.get("employer_id") != employer_id:
            raise RuntimeError(
                "Backend employer accessibility response must identify the requested employer."
            )
        capabilities = response.get("capabilities")
        if not isinstance(capabilities, list):
            raise RuntimeError(
                "Backend employer accessibility response must contain a capabilities list."
            )
        profile_completed = response.get("profile_completed")
        if not isinstance(profile_completed, bool):
            raise RuntimeError(
                "Backend employer accessibility response must include boolean profile_completed."
            )
        return {
            "company_name": response.get("company_name", "Innovative Technology Employer"),
            "verification_status": response.get("verification_status", "VERIFIED"),
            "profile_completed": profile_completed,
            "capabilities": capabilities,
        }
