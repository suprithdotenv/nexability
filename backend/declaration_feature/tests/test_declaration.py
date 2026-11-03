import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.user import User, UserRole
from app.models.candidate_profile import CandidateProfile
from app.models.candidate_declaration import CandidateDeclaration
from declaration_feature.schemas.declaration import DeclarationCreate
from declaration_feature.api import (
    get_candidate_declaration,
    save_candidate_declaration,
    withdraw_candidate_declaration,
)


@pytest.fixture(scope="module")
def db_engine():
    db_id = uuid.uuid4().hex[:8]
    engine = create_engine(f"sqlite:///d:/sap/nexability/backend/test_decl_{db_id}.db")
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()
    import os
    try:
        os.remove(f"d:/sap/nexability/backend/test_decl_{db_id}.db")
    except OSError:
        pass


@pytest.fixture
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


def test_declaration_flow(db_session):
    # 1. Create candidate user & profile
    user = User(
        id=uuid.uuid4(),
        email=f"candidate_{uuid.uuid4().hex[:6]}@example.com",
        role=UserRole.CANDIDATE,
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    candidate = CandidateProfile(
        id=uuid.uuid4(),
        user_id=user.id,
        full_name="Alex Accessibility",
    )
    db_session.add(candidate)
    db_session.commit()

    # 2. Initially no declaration
    res_initial = get_candidate_declaration(candidate=candidate, db=db_session)
    assert res_initial.accepted is False

    # 3. Save declaration
    payload = DeclarationCreate(declaration_version="v1", accepted=True)
    res_saved = save_candidate_declaration(payload=payload, candidate=candidate, db=db_session)
    assert res_saved.accepted is True
    assert res_saved.declaration_version == "v1"

    # 4. Get active declaration
    res_active = get_candidate_declaration(candidate=candidate, db=db_session)
    assert res_active.accepted is True
    assert res_active.declaration_version == "v1"

    # 5. Withdraw declaration
    res_withdrawn = withdraw_candidate_declaration(candidate=candidate, db=db_session)
    assert res_withdrawn.accepted is False

    # 6. Check status after withdrawal
    res_after = get_candidate_declaration(candidate=candidate, db=db_session)
    assert res_after.accepted is False
