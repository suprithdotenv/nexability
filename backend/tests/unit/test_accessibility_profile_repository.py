from __future__ import annotations

import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.accommodation_preference import AccommodationPreference
from app.models.candidate_profile import CandidateProfile
from app.models.employer_accessibility_capability import (
    AvailabilityStatus,
    EmployerAccessibilityCapability,
)
from app.models.employer_profile import EmployerProfile
from app.models.user import User, UserRole
from app.repositories.accessibility_profile_repository import (
    AccessibilityProfileRepository,
)


def test_accessibility_reader_returns_existing_columns_and_unknown_completion():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    candidate_user_id = uuid.uuid4()
    employer_user_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    employer_id = uuid.uuid4()
    with sessions.begin() as session:
        session.add_all(
            [
                User(
                    id=candidate_user_id,
                    email=f"{candidate_user_id}@example.test",
                    role=UserRole.CANDIDATE,
                ),
                User(
                    id=employer_user_id,
                    email=f"{employer_user_id}@example.test",
                    role=UserRole.EMPLOYER,
                ),
            ]
        )
        session.flush()
        session.add_all(
            [
                CandidateProfile(
                    id=candidate_id,
                    user_id=candidate_user_id,
                    full_name="Candidate",
                ),
                EmployerProfile(
                    id=employer_id,
                    user_id=employer_user_id,
                    full_name="Employer",
                    company_name="Test Company",
                    email_domain="example.test",
                ),
            ]
        )
        session.flush()
        session.add_all(
            [
                AccommodationPreference(
                    candidate_profile_id=candidate_id,
                    category="schedule",
                    preference="flexible hours",
                    details="private candidate detail",
                    is_active=True,
                ),
                EmployerAccessibilityCapability(
                    employer_profile_id=employer_id,
                    category="schedule",
                    capability="flexible hours",
                    status=AvailabilityStatus.ON_REQUEST,
                    details="available by request",
                ),
            ]
        )

    repository = AccessibilityProfileRepository(sessions)
    candidate = repository.get_candidate_accessibility_preferences(str(candidate_id))
    employer = repository.get_employer_accessibility_profile(str(employer_id))

    assert candidate == [
        {
            "category": "schedule",
            "preference": "flexible hours",
            "details": "private candidate detail",
        }
    ]
    assert employer["profile_completed"] is None
    assert employer["capabilities"] == [
        {
            "category": "schedule",
            "capability": "flexible hours",
            "status": "ON_REQUEST",
            "details": "available by request",
        }
    ]
    assert not hasattr(repository, "save")
    Base.metadata.drop_all(engine)
    engine.dispose()
