"""
Pydantic schemas for candidate job-matching responses.

These schemas support professional-first matching ranked by candidate-to-job
compatibility (skills, experience, and pgvector semantic similarity), while
keeping accessibility requirements and evaluations completely separate.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator


class CompanyInfo(BaseModel):
    """Employer and company profile information."""

    employer_id: str | None = None
    company_name: str | None = Field(default="Innovative Tech Employer", description="Company or employer name.")
    company_domain: str | None = None
    website: str | None = None
    phone: str | None = None
    verification_status: str | None = "VERIFIED"


class JobInfo(BaseModel):
    """Job listing and document information."""

    job_id: str | None = None
    job_title: str | None = None
    overview: str | None = None
    original_filename: str | None = None
    required_skills: list[str] = Field(default_factory=list)


class AccessibilityRequirementEvaluation(BaseModel):
    """Candidate accessibility requirement compared against employer capabilities."""

    preference: str = Field(description="Candidate accommodation requirement.")
    category: str = Field(default="general", description="Accommodation category.")
    employer_status: str = Field(
        description="Exact status: AVAILABLE | ON_REQUEST | NOT_SPECIFIED | UNAVAILABLE"
    )
    employer_capability: str | None = Field(
        default=None, description="Matching employer capability text if provided."
    )
    details: str | None = Field(
        default=None, description="Clarification or notes regarding this accommodation."
    )
    is_gap: bool = Field(
        default=False, description="True if status is NOT_SPECIFIED or UNAVAILABLE."
    )
    can_request: bool = Field(
        default=True, description="True if candidate can submit an accommodation request."
    )


class MatchScores(BaseModel):
    """
    Component scores.
    Professional compatibility determines ranking.
    Accessibility is evaluated separately and does NOT reduce the professional score.
    """

    professional_match_score: float = Field(
        description="Professional résumé match score (0–100) based on skills and semantic embeddings."
    )
    accessibility_compatibility: float = Field(
        default=100.0,
        description="Informational accessibility compatibility percentage (0–100)."
    )
    ranking_score: float = Field(
        description="Final ranking score, equal to professional_match_score (ranked by professional compatibility)."
    )
    accessibility_note: str = Field(
        default="Evaluated separately",
        description="Human-readable note explaining accessibility is evaluated independently."
    )
    ranking_formula: str = Field(
        default="Ranked strictly by professional compatibility: skills (55%) + vector semantic similarity (45%). Accessibility evaluated separately.",
        description="Ranking formula used."
    )


class JobMatch(BaseModel):
    """A single job match result ranked by professional compatibility."""

    rank: int = Field(description="1-based rank position based on professional match score.")
    job_id: str | None = Field(default=None, description="Job document UUID.")
    employer_id: str | None = Field(default=None, description="Employer profile UUID.")
    job_title: str | None = Field(default=None, description="Job title.")
    company_info: CompanyInfo = Field(default_factory=CompanyInfo)
    job_info: JobInfo = Field(default_factory=JobInfo)
    professional_match_score: float = Field(
        default=0.0,
        description="Primary professional match score (0–100)."
    )
    scores: MatchScores = Field(description="Scores block for backward compatibility.")
    professional_match: dict[str, Any] = Field(
        default_factory=dict,
        description="Detailed professional evidence breakdown (skills, experience, vector similarity)."
    )
    accessibility_match: dict[str, Any] = Field(
        default_factory=dict,
        description="Detailed accessibility compatibility breakdown."
    )
    accessibility_requirements: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of candidate requirements with exact employer statuses.",
    )
    accessibility_gaps: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Subset of requirements with status NOT_SPECIFIED or UNAVAILABLE.",
    )
    can_request_accommodation: bool = Field(
        default=False,
        description="True if any accommodation gap exists that can be requested.",
    )

    @model_validator(mode="before")
    @classmethod
    def populate_defaults(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "professional_match_score" not in data and "scores" in data:
                data["professional_match_score"] = data["scores"].get("professional_match_score", 0.0)
        return data


class CandidateMatchResponse(BaseModel):
    """Ranked job matches for a candidate."""

    candidate_id: str
    status: str = Field(
        description=(
            "match_found | no_jobs_available | no_resume | "
            "resume_not_processed | processing_in_progress"
        )
    )
    match_count: int
    ranking_formula: str = Field(
        default="Ranked by professional compatibility. Accessibility evaluated separately."
    )
    ranking_strategy: str = Field(
        default="professional_compatibility_first"
    )
    top_matches: list[JobMatch]
