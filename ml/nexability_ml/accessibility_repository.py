from __future__ import annotations

from typing import Any, Protocol


class AccessibilityProfileRepository(Protocol):
    """Backend boundary for ID-scoped candidate and employer accessibility data."""

    def get_candidate_accessibility_preferences(
        self, candidate_id: str
    ) -> list[dict[str, Any]]: ...

    def get_employer_accessibility_profile(self, employer_id: str) -> dict[str, Any]:
        """Return profile_completed and a capabilities list."""
        ...
