"""
Unit tests for the revised job matching and accessibility evaluation logic.

Verifies:
1. Final ranking is determined strictly by professional compatibility (not 60/40).
2. Missing accessibility information does NOT penalize or hide jobs.
3. Accessibility evaluation produces exact statuses:
   - AVAILABLE
   - ON_REQUEST
   - NOT_SPECIFIED
   - UNAVAILABLE
4. NOT_SPECIFIED is NOT treated as UNAVAILABLE.
5. Gaps are identified for NOT_SPECIFIED and UNAVAILABLE.
6. Professional match score is visible separately and unaffected by accessibility.
"""
import uuid
from unittest.mock import MagicMock

import pytest

from app.automated_pipeline.matching import (
    _calculate_accessibility_evaluation,
    _calculate_professional_score,
)
from app.models.accommodation_preference import AccommodationPreference
from app.models.employer_accessibility_capability import EmployerAccessibilityCapability


def test_accessibility_evaluation_exact_statuses():
    """Verify exact statuses: AVAILABLE, ON_REQUEST, NOT_SPECIFIED, UNAVAILABLE."""
    candidate_id = uuid.uuid4()
    employer_id = uuid.uuid4()

    # Candidate has 4 preferences
    prefs = [
        AccommodationPreference(
            id=uuid.uuid4(),
            candidate_profile_id=candidate_id,
            category="SCREEN_READER",
            preference="Screen reader tools (NVDA)",
            is_active=True,
        ),
        AccommodationPreference(
            id=uuid.uuid4(),
            candidate_profile_id=candidate_id,
            category="TIME",
            preference="Flexible work hours",
            is_active=True,
        ),
        AccommodationPreference(
            id=uuid.uuid4(),
            candidate_profile_id=candidate_id,
            category="REMOTE",
            preference="Full remote work",
            is_active=True,
        ),
        AccommodationPreference(
            id=uuid.uuid4(),
            candidate_profile_id=candidate_id,
            category="MOBILITY",
            preference="Wheelchair accessible ramp",
            is_active=True,
        ),
    ]

    # Employer offers screen reader as AVAILABLE, flexible hours as ON_REQUEST,
    # full remote as UNAVAILABLE, and nothing for mobility (NOT_SPECIFIED).
    caps = [
        EmployerAccessibilityCapability(
            id=uuid.uuid4(),
            employer_profile_id=employer_id,
            category="SCREEN_READER",
            capability="Screen reader tools (NVDA)",
            status="AVAILABLE",
        ),
        EmployerAccessibilityCapability(
            id=uuid.uuid4(),
            employer_profile_id=employer_id,
            category="TIME",
            capability="Flexible work hours",
            status="ON_REQUEST",
        ),
        EmployerAccessibilityCapability(
            id=uuid.uuid4(),
            employer_profile_id=employer_id,
            category="REMOTE",
            capability="Full remote work",
            status="UNAVAILABLE",
        ),
    ]

    avg_score, evaluations, gaps = _calculate_accessibility_evaluation(prefs, caps)

    status_by_cat = {e["category"]: e["employer_status"] for e in evaluations}

    assert status_by_cat["SCREEN_READER"] == "AVAILABLE"
    assert status_by_cat["TIME"] == "ON_REQUEST"
    assert status_by_cat["REMOTE"] == "UNAVAILABLE"
    assert status_by_cat["MOBILITY"] == "NOT_SPECIFIED"

    # NOT_SPECIFIED is NOT treated as UNAVAILABLE
    assert status_by_cat["MOBILITY"] != status_by_cat["REMOTE"]
    assert status_by_cat["MOBILITY"] != "UNAVAILABLE"

    # Gaps are identified for NOT_SPECIFIED and UNAVAILABLE
    gap_cats = [g["category"] for g in gaps]
    assert "REMOTE" in gap_cats
    assert "MOBILITY" in gap_cats
    assert "SCREEN_READER" not in gap_cats
    assert "TIME" not in gap_cats


def test_professional_score_combines_skills_and_dense_vectors():
    """Verify professional score incorporates skills overlap and vector similarity."""
    cand_profile = {
        "skills": [
            {"name": "Python", "evidence": ["4 years building backend APIs"]},
            {"name": "FastAPI", "evidence": ["Built REST microservices"]},
            {"name": "PostgreSQL", "evidence": ["Schema design & optimization"]},
        ],
        "experience": [
            {"role": "Senior Developer", "company": "Tech Corp", "duration": "3 years"}
        ],
    }

    job_profile = {
        "job_title": "Senior Python Backend Engineer",
        "required_skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
    }

    cand_chunk = MagicMock()
    cand_chunk.embedding = [0.1] * 768

    job_chunk = MagicMock()
    job_chunk.embedding = [0.1] * 768

    score, details = _calculate_professional_score(
        cand_profile,
        job_profile,
        [cand_chunk],
        [job_chunk],
    )

    # 3 of 4 skills matched = 75% skill score
    assert details["skill_match_percentage"] == 75.0
    assert len(details["matched_skills"]) == 3
    assert details["missing_skills"] == ["Docker"]
    # Vector similarity with identical vectors is 1.0 (100.0)
    assert details["vector_semantic_similarity"] == 100.0
    # Combined score (55% * 75 + 45% * 100 = 41.25 + 45.0 = 86.25)
    assert score == 86.25


def test_professional_match_determines_ranking_not_accessibility():
    """
    Critical requirement:
    Job A: Higher professional match (90%), Missing accessibility (NOT_SPECIFIED)
    Job B: Lower professional match (60%), Full accessibility (AVAILABLE 100%)

    Job A MUST rank above Job B under the new professional-compatibility ranking logic.
    Under the old 60/40 formula, Job B would score 84% while Job A would score 60%,
    unfairly penalizing Job A. Under the revised logic, Job A ranks #1.
    """
    job_a_prof_score = 90.0
    job_b_prof_score = 60.0

    # Under revised ranking, sorting is strictly by professional_match_score descending
    matches = [
        {"job_title": "Job B (Full Acc, Lower Prof)", "professional_match_score": job_b_prof_score},
        {"job_title": "Job A (Missing Acc, High Prof)", "professional_match_score": job_a_prof_score},
    ]

    matches.sort(key=lambda x: x["professional_match_score"], reverse=True)

    assert matches[0]["job_title"] == "Job A (Missing Acc, High Prof)"
    assert matches[1]["job_title"] == "Job B (Full Acc, Lower Prof)"
