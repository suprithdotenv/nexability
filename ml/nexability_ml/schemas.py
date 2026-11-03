from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ExtractedSkill(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    category: str | None = None
    evidence: list[str] = Field(default_factory=list)


class ResumeExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    professional_summary: str | None = None
    skills: list[ExtractedSkill] = Field(default_factory=list)
    experience: list[dict[str, str | None]] = Field(default_factory=list)
    education: list[dict[str, str | None]] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)


class RequirementEnrichment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    original_requirement: str
    normalized_requirement: str | None = None
    normalized_skill: str | None = None


class JobExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_title: str | None = None
    role_summary: str | None = None
    requirement_enrichments: list[RequirementEnrichment] = Field(default_factory=list)


class JobRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirement: str
    category: str
    priority: str
    normalized_skill: str | None = None


class JobProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str | None = None
    employer_id: str | None = None
    job_title: str | None = None
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    domain_knowledge: list[str] = Field(default_factory=list)
    education_requirements: list[str] = Field(default_factory=list)
    experience_requirements: list[str] = Field(default_factory=list)
    requirements: list[JobRequirement] = Field(default_factory=list)
    requirement_enrichments: list[RequirementEnrichment] = Field(default_factory=list)
    required_qualifications: list[str] = Field(default_factory=list)
    preferred_qualifications: list[str] = Field(default_factory=list)
