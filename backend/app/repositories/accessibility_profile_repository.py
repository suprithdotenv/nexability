from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models.accommodation_preference import AccommodationPreference
from app.models.employer_accessibility_capability import EmployerAccessibilityCapability


class AccessibilityProfileRepository:
    """Read-only repository for internal matching inputs; it exposes no write methods."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def get_candidate_accessibility_preferences(
        self, candidate_id: str
    ) -> list[dict[str, Any]]:
        candidate_profile_id = uuid.UUID(candidate_id)
        with self._session_factory() as session:
            records = session.scalars(
                select(AccommodationPreference).where(
                    AccommodationPreference.candidate_profile_id == candidate_profile_id,
                    AccommodationPreference.is_active.is_(True),
                )
            ).all()
            return [
                {
                    "category": record.category,
                    "preference": record.preference,
                    "details": record.details,
                }
                for record in records
            ]

    def get_employer_accessibility_profile(
        self, employer_id: str
    ) -> dict[str, Any]:
        employer_profile_id = uuid.UUID(employer_id)
        with self._session_factory() as session:
            records = session.scalars(
                select(EmployerAccessibilityCapability).where(
                    EmployerAccessibilityCapability.employer_profile_id
                    == employer_profile_id
                )
            ).all()
            return {
                "profile_completed": None,
                "capabilities": [
                    {
                        "category": record.category,
                        "capability": record.capability,
                        "status": record.status.value,
                        "details": record.details,
                    }
                    for record in records
                ],
            }
