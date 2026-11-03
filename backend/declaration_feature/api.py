import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.candidate_profile import CandidateProfile
from app.models.candidate_declaration import CandidateDeclaration
from app.api.v1.endpoints.candidates import get_candidate_profile
from .schemas.declaration import (
    DeclarationCreate,
    DeclarationResponse,
    DeclarationDeleteResponse,
)

router = APIRouter(prefix="/candidates/me/declaration", tags=["candidate-declaration"])


@router.get(
    "",
    response_model=DeclarationResponse,
    summary="Get candidate's voluntary disability declaration status",
)
def get_candidate_declaration(
    candidate: CandidateProfile = Depends(get_candidate_profile),
    db: Session = Depends(get_db),
) -> DeclarationResponse:
    decl = db.scalar(
        select(CandidateDeclaration)
        .where(
            CandidateDeclaration.candidate_profile_id == candidate.id,
            CandidateDeclaration.withdrawn_at.is_(None),
        )
        .order_by(CandidateDeclaration.accepted_at.desc())
    )
    if not decl:
        return DeclarationResponse(
            accepted=False,
            declaration_version=None,
            message="No active declaration on file.",
        )

    return DeclarationResponse(
        id=decl.id,
        candidate_profile_id=decl.candidate_profile_id,
        declaration_version=decl.declaration_version,
        accepted_at=decl.accepted_at,
        withdrawn_at=decl.withdrawn_at,
        accepted=True,
        message="Active voluntary declaration on file.",
    )


@router.post(
    "",
    response_model=DeclarationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record or update candidate's voluntary disability declaration",
)
@router.put(
    "",
    response_model=DeclarationResponse,
    summary="Update or set candidate's voluntary disability declaration",
)
def save_candidate_declaration(
    payload: DeclarationCreate,
    candidate: CandidateProfile = Depends(get_candidate_profile),
    db: Session = Depends(get_db),
) -> DeclarationResponse:
    if not payload.accepted:
        # If set to false, treat as withdrawal
        decl = db.scalar(
            select(CandidateDeclaration)
            .where(
                CandidateDeclaration.candidate_profile_id == candidate.id,
                CandidateDeclaration.withdrawn_at.is_(None),
            )
        )
        if decl:
            decl.withdrawn_at = datetime.now(timezone.utc)
            db.commit()
        return DeclarationResponse(
            accepted=False,
            message="Declaration withdrawn or not accepted.",
        )

    # Check if active declaration already exists
    decl = db.scalar(
        select(CandidateDeclaration)
        .where(
            CandidateDeclaration.candidate_profile_id == candidate.id,
            CandidateDeclaration.withdrawn_at.is_(None),
        )
    )

    now = datetime.now(timezone.utc)
    if decl:
        decl.declaration_version = payload.declaration_version
        decl.accepted_at = now
    else:
        decl = CandidateDeclaration(
            candidate_profile_id=candidate.id,
            declaration_version=payload.declaration_version,
            accepted_at=now,
            withdrawn_at=None,
        )
        db.add(decl)

    db.commit()
    db.refresh(decl)

    return DeclarationResponse(
        id=decl.id,
        candidate_profile_id=decl.candidate_profile_id,
        declaration_version=decl.declaration_version,
        accepted_at=decl.accepted_at,
        withdrawn_at=decl.withdrawn_at,
        accepted=True,
        message="Voluntary declaration recorded successfully.",
    )


@router.delete(
    "",
    response_model=DeclarationDeleteResponse,
    summary="Withdraw candidate's voluntary disability declaration",
)
def withdraw_candidate_declaration(
    candidate: CandidateProfile = Depends(get_candidate_profile),
    db: Session = Depends(get_db),
) -> DeclarationDeleteResponse:
    decl = db.scalar(
        select(CandidateDeclaration)
        .where(
            CandidateDeclaration.candidate_profile_id == candidate.id,
            CandidateDeclaration.withdrawn_at.is_(None),
        )
    )
    if decl:
        decl.withdrawn_at = datetime.now(timezone.utc)
        db.commit()

    return DeclarationDeleteResponse(
        message="Declaration withdrawn successfully.",
        accepted=False,
    )
