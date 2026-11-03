"""Pydantic schemas for the Candidate Disability Self‑Declaration feature.

These schemas are placed in a separate feature folder so they do not interfere
with the existing `backend/app/schemas` package.  They import only standard
pydantic types and reference the existing SQLAlchemy model indirectly via the
service layer.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DeclarationCreate(BaseModel):
    """Payload for the POST /me/declaration endpoint.

    Only the version identifier of the declaration text is required.  The
    frontend will send a short string such as ``"v1.0"``.
    """

    declaration_version: str = Field(
        ...,
        max_length=30,
        description="Version identifier of the declaration text the candidate accepts",
    )

    model_config = ConfigDict(extra="forbid")


class DeclarationResponse(BaseModel):
    """Response model for GET /me/declaration.

    Mirrors the fields of the existing ``CandidateDeclaration`` ORM model.
    """

    id: UUID
    candidate_profile_id: UUID
    declaration_version: str
    accepted_at: datetime
    withdrawn_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class DeclarationDeleteResponse(BaseModel):
    """Simple confirmation returned after a successful DELETE.
    """

    message: str = "Declaration withdrawn successfully."

