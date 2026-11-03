import uuid
import datetime
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.user import User, UserRole
from app.models.employer_profile import EmployerProfile
from app.models.candidate_profile import CandidateProfile
from app.models.candidate_declaration import CandidateDeclaration
from app.models.employer_accessibility_capability import (
    EmployerAccessibilityCapability,
    AvailabilityStatus,
)

from employer_feature.api.jobs import (
    create_job_endpoint,
    list_my_jobs_endpoint,
    get_my_job_endpoint,
    update_my_job_endpoint,
    delete_my_job_endpoint,
    list_public_jobs_endpoint,
)
from employer_feature.schemas.job import JobCreate, JobUpdate
from employer_feature.api.applications import (
    candidate_apply_job_endpoint,
    candidate_list_applications_endpoint,
    employer_list_applications_endpoint,
    employer_get_application_endpoint,
    employer_update_application_status_endpoint,
)
from employer_feature.schemas.application import (
    JobApplicationCreate,
    JobApplicationStatusUpdate,
)
from employer_feature.api.accommodation import (
    candidate_request_accommodation_endpoint,
    candidate_list_accommodations_endpoint,
    employer_list_accommodations_endpoint,
    employer_get_accommodation_endpoint,
    employer_respond_accommodation_endpoint,
)
from employer_feature.schemas.accommodation import (
    AccommodationCreate,
    AccommodationResponseUpdate,
)
from employer_feature.api.dashboard import get_employer_dashboard_endpoint
from fastapi import HTTPException


@pytest.fixture(scope="module")
def db_engine():
    db_id = uuid.uuid4().hex[:8]
    engine = create_engine(f"sqlite:///d:/sap/nexability/backend/test_{db_id}.db")
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()
    import os
    try:
        os.remove(f"d:/sap/nexability/backend/test_{db_id}.db")
    except Exception:
        pass


@pytest.fixture
def db(db_engine):
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine, expire_on_commit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def employer_one(db):
    user = User(
        email=f"emp1_{uuid.uuid4().hex[:6]}@techcorp.com",
        role=UserRole.EMPLOYER,
        is_active=True,
    )
    db.add(user)
    db.commit()

    profile = EmployerProfile(
        user_id=user.id,
        full_name="Alice Recruiter",
        company_name="TechCorp Inclusive",
        email_domain="techcorp.com",
        website="https://techcorp.com",
        phone="+1234567890",
        verification_status="VERIFIED",
    )
    db.add(profile)
    db.commit()
    return {"user": user, "profile": profile}


@pytest.fixture
def employer_two(db):
    user = User(
        email=f"emp2_{uuid.uuid4().hex[:6]}@otherorg.com",
        role=UserRole.EMPLOYER,
        is_active=True,
    )
    db.add(user)
    db.commit()

    profile = EmployerProfile(
        user_id=user.id,
        full_name="Bob Other",
        company_name="Other Org",
        email_domain="otherorg.com",
        website="https://otherorg.com",
        phone="+1987654321",
        verification_status="PENDING",
    )
    db.add(profile)
    db.commit()
    return {"user": user, "profile": profile}


@pytest.fixture
def candidate_user(db):
    user = User(
        email=f"candidate_{uuid.uuid4().hex[:6]}@example.com",
        role=UserRole.CANDIDATE,
        is_active=True,
    )
    db.add(user)
    db.commit()

    profile = CandidateProfile(
        user_id=user.id,
        full_name="Taylor Swift-Walker",
        phone="+1555444333",
    )
    db.add(profile)
    db.commit()

    decl = CandidateDeclaration(
        candidate_profile_id=profile.id,
        declaration_version="v2024",
    )
    db.add(decl)
    db.commit()
    return {"user": user, "profile": profile, "declaration": decl}


# -------------------------------------------------------------
# 1. Job Management Tests (CRUD & Role Protection)
# -------------------------------------------------------------


def test_employer_job_crud_lifecycle(db, employer_one):
    prof = employer_one["profile"]

    # 1. Create Job
    job = create_job_endpoint(
        JobCreate(
            title="Senior Accessible Frontend Architect",
            description="Leading accessibility design systems and WCAG compliance.",
            location="Remote",
            work_mode="Remote",
            status="ACTIVE",
        ),
        db=db,
        profile=prof,
    )
    assert job.title == "Senior Accessible Frontend Architect"
    assert job.company_name == "TechCorp Inclusive"
    assert job.is_active is True

    # 2. List Employer Jobs
    jobs = list_my_jobs_endpoint(db=db, profile=prof)
    assert any(j.id == job.id for j in jobs)

    # 3. Get Single Job
    fetched = get_my_job_endpoint(job.id, db=db, profile=prof)
    assert fetched.id == job.id

    # 4. Update Job
    updated = update_my_job_endpoint(
        job.id,
        JobUpdate(title="Principal Accessibility Architect", work_mode="Hybrid"),
        db=db,
        profile=prof,
    )
    assert updated.title == "Principal Accessibility Architect"
    assert updated.work_mode == "Hybrid"

    # 5. Public exploration route
    pub_jobs = list_public_jobs_endpoint(db=db)
    assert any(j.id == job.id for j in pub_jobs)

    # 6. Delete Job
    del_res = delete_my_job_endpoint(job.id, db=db, profile=prof)
    assert "deleted successfully" in del_res["message"]

    # 7. Verify deletion
    with pytest.raises(HTTPException) as exc:
        get_my_job_endpoint(job.id, db=db, profile=prof)
    assert exc.value.status_code == 404


def test_employer_cannot_mutate_another_organization_job(db, employer_one, employer_two):
    prof1 = employer_one["profile"]
    prof2 = employer_two["profile"]

    job = create_job_endpoint(
        JobCreate(title="Confidential Role", description="Secret description"),
        db=db,
        profile=prof1,
    )

    # Employer 2 cannot get Employer 1's job
    with pytest.raises(HTTPException) as exc1:
        get_my_job_endpoint(job.id, db=db, profile=prof2)
    assert exc1.value.status_code == 404

    # Employer 2 cannot update Employer 1's job
    with pytest.raises(HTTPException) as exc2:
        update_my_job_endpoint(job.id, JobUpdate(title="Hacked"), db=db, profile=prof2)
    assert exc2.value.status_code == 404

    # Employer 2 cannot delete Employer 1's job
    with pytest.raises(HTTPException) as exc3:
        delete_my_job_endpoint(job.id, db=db, profile=prof2)
    assert exc3.value.status_code == 404


# -------------------------------------------------------------
# 2. Candidate Application & Strict Privacy Protection Tests
# -------------------------------------------------------------


def test_candidate_apply_and_strict_employer_privacy(db, employer_one, employer_two, candidate_user):
    prof1 = employer_one["profile"]
    prof2 = employer_two["profile"]
    cand = candidate_user["profile"]

    # 1. Employer 1 posts a job
    job = create_job_endpoint(
        JobCreate(title="Accessibility Specialist", description="Auditing web applications"),
        db=db,
        profile=prof1,
    )

    # 2. Candidate applies
    app = candidate_apply_job_endpoint(
        job.id,
        JobApplicationCreate(cover_note="Experienced with JAWS and NVDA."),
        db=db,
        candidate=cand,
    )
    assert app.job_title == "Accessibility Specialist"
    assert app.candidate_name == "Taylor Swift-Walker"
    assert app.has_declaration is True
    assert app.declaration_version == "v2024"

    # Candidate sees application in their own list
    cand_apps = candidate_list_applications_endpoint(db=db, candidate=cand)
    assert any(a.id == app.id for a in cand_apps)

    # 3. Employer 1 sees this application
    emp1_apps = employer_list_applications_endpoint(db=db, profile=prof1)
    assert any(a.id == app.id for a in emp1_apps)

    # Employer 1 updates status
    status_updated = employer_update_application_status_endpoint(
        app.id,
        JobApplicationStatusUpdate(status="REVIEWING"),
        db=db,
        profile=prof1,
    )
    assert status_updated.status == "REVIEWING"

    # 4. STRICT PRIVACY RULE: Employer 2 MUST NOT see or access this candidate's application!
    emp2_apps = employer_list_applications_endpoint(db=db, profile=prof2)
    assert not any(a.id == app.id for a in emp2_apps)

    with pytest.raises(HTTPException) as exc:
        employer_get_application_endpoint(app.id, db=db, profile=prof2)
    assert exc.value.status_code == 404


# -------------------------------------------------------------
# 3. Accommodation Request & Management Tests
# -------------------------------------------------------------


def test_accommodation_request_workflow_and_isolation(db, employer_one, employer_two, candidate_user):
    prof1 = employer_one["profile"]
    prof2 = employer_two["profile"]
    cand = candidate_user["profile"]

    job = create_job_endpoint(
        JobCreate(title="Product Designer", description="Inclusive design lead"),
        db=db,
        profile=prof1,
    )

    # Candidate requests accommodation
    acc = candidate_request_accommodation_endpoint(
        job.id,
        AccommodationCreate(
            facility="Live Captions during Interview",
            description="Need CART or automated real-time captions for the interview stages.",
        ),
        db=db,
        candidate=cand,
    )
    assert acc.facility == "Live Captions during Interview"
    assert acc.status == "PENDING"

    # Candidate lists accommodations
    cand_accs = candidate_list_accommodations_endpoint(db=db, candidate=cand)
    assert any(a.id == acc.id for a in cand_accs)

    # Employer 1 inbox lists request
    emp1_accs = employer_list_accommodations_endpoint(db=db, profile=prof1)
    assert any(a.id == acc.id for a in emp1_accs)

    # Employer 1 responds
    responded = employer_respond_accommodation_endpoint(
        acc.id,
        AccommodationResponseUpdate(
            status="APPROVED",
            response_message="CART live captioner will be scheduled for all rounds.",
        ),
        db=db,
        profile=prof1,
    )
    assert responded.status == "APPROVED"
    assert "CART" in responded.response_message

    # STRICT ISOLATION: Employer 2 CANNOT access request
    emp2_accs = employer_list_accommodations_endpoint(db=db, profile=prof2)
    assert not any(a.id == acc.id for a in emp2_accs)

    with pytest.raises(HTTPException) as exc:
        employer_get_accommodation_endpoint(acc.id, db=db, profile=prof2)
    assert exc.value.status_code == 404


# -------------------------------------------------------------
# 4. Employer Dashboard Summary Tests
# -------------------------------------------------------------


def test_employer_dashboard_summary(db, employer_one):
    user = employer_one["user"]
    prof = employer_one["profile"]

    # Add accessibility capability
    cap = EmployerAccessibilityCapability(
        employer_profile_id=prof.id,
        category="MOBILITY",
        capability="Wheelchair accessible facility and entrances",
        status=AvailabilityStatus.AVAILABLE,
        details="Elevators and ramp access verified on-site.",
    )
    db.add(cap)
    db.commit()

    dash = get_employer_dashboard_endpoint(current_user=user, profile=prof, db=db)
    assert dash.profile.company_name == "TechCorp Inclusive"
    assert dash.stats.verification_status == "VERIFIED"
    assert dash.stats.accessibility_capabilities_count >= 1
    assert len(dash.accessibility_capabilities) >= 1
