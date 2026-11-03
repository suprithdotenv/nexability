"""Pydantic schemas for the Candidate Disability Self‑Declaration feature.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DeclarationCreate(BaseModel):
    """Payload for creating or updating candidate voluntary disability declaration."""

    declaration_version: str = Field(
        default="v1",
        max_length=30,
        description="Version identifier of the declaration text the candidate accepts",
    )
    accepted: bool = Field(
        default=True,
        description="Whether candidate voluntarily declares disability status",
    )

    model_config = ConfigDict(extra="ignore")


class DeclarationResponse(BaseModel):
    """Response model for GET/POST/PUT /candidates/me/declaration."""

    id: UUID | None = None
    candidate_profile_id: UUID | None = None
    declaration_version: str | None = None
    accepted_at: datetime | None = None
    withdrawn_at: datetime | None = None
    accepted: bool = True
    message: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DeclarationDeleteResponse(BaseModel):
    """Confirmation returned after a successful DELETE/withdrawal."""

    message: str = "Declaration withdrawn successfully."
    accepted: bool = False
