import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_role
from app.core.config import settings
from app.db.session import get_db
from app.models.accommodation_preference import AccommodationPreference
from app.models.candidate_profile import CandidateProfile
from app.models.resume import Resume
from app.models.user import User, UserRole
from app.schemas.candidate import (
    AccessibilityPreferenceCreate,
    AccessibilityPreferenceResponse,
    AccessibilityPreferenceUpdate,
    CandidateProfileResponse,
    CandidateProfileUpdate,
    ResumeActionResponse,
    ResumeMetadataResponse,
)
from app.services.storage.storage_service import (
    storage_service,
    validate_document_file,
)

router = APIRouter()


def get_candidate_profile(
    current_user: User = Depends(require_role(UserRole.CANDIDATE)),
    db: Session = Depends(get_db),
) -> CandidateProfile:
    """Helper dependency to retrieve the candidate profile for the authenticated candidate."""
    profile = db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == current_user.id))
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate profile not found.",
        )
    return profile


# -------------------------------------------------------------
# Candidate Profile Endpoints
# -------------------------------------------------------------


@router.get(
    "/me",
    response_model=CandidateProfileResponse,
    summary="Get current candidate profile",
)
def get_my_candidate_profile(
    current_user: User = Depends(require_role(UserRole.CANDIDATE)),
    profile: CandidateProfile = Depends(get_candidate_profile),
) -> CandidateProfileResponse:
    return CandidateProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        email=current_user.email,
        full_name=profile.full_name,
        phone=profile.phone,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@router.patch(
    "/me",
    response_model=CandidateProfileResponse,
    summary="Update current candidate profile",
)
def update_my_candidate_profile(
    payload: CandidateProfileUpdate,
    current_user: User = Depends(require_role(UserRole.CANDIDATE)),
    profile: CandidateProfile = Depends(get_candidate_profile),
    db: Session = Depends(get_db),
) -> CandidateProfileResponse:
    if payload.full_name is not None:
        profile.full_name = payload.full_name.strip()
    if payload.phone is not None:
        profile.phone = payload.phone.strip() if payload.phone else None

    db.add(profile)
    db.commit()
    db.refresh(profile)

    return CandidateProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        email=current_user.email,
        full_name=profile.full_name,
        phone=profile.phone,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


# -------------------------------------------------------------
# Resume Management Endpoints
# -------------------------------------------------------------


@router.post(
    "/me/resume",
    response_model=ResumeMetadataResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload or replace candidate resume",
)
async def upload_candidate_resume(
    file: Annotated[UploadFile, File(description="Resume file (PDF or DOCX)")],
    profile: CandidateProfile = Depends(get_candidate_profile),
    db: Session = Depends(get_db),
) -> ResumeMetadataResponse:
    # 1. Read file content
    content = await file.read()

    # 2. Validate format, size and magic bytes
    clean_filename, mime_type = validate_document_file(file, content)

    # 3. Generate private storage path
    storage_path = storage_service.generate_storage_path(
        prefix="candidates",
        owner_id=profile.id,
        filename=clean_filename,
    )

    bucket = settings.SUPABASE_STORAGE_BUCKET_RESUMES

    # 4. Upload file to private storage
    try:
        storage_service.upload_file(
            bucket=bucket,
            storage_path=storage_path,
            content=content,
            mime_type=mime_type,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Storage upload failed: {str(exc)}",
        ) from exc

    # 5. Persist metadata in PostgreSQL, handling cleanup if DB fails
    try:
        # Mark previous active resumes as inactive
        previous_resumes = db.scalars(
            select(Resume).where(
                Resume.candidate_profile_id == profile.id,
                Resume.is_active.is_(True),
            )
        ).all()
        for prev in previous_resumes:
            prev.is_active = False

        resume_record = Resume(
            candidate_profile_id=profile.id,
            original_filename=clean_filename,
            storage_path=storage_path,
            mime_type=mime_type,
            file_size_bytes=len(content),
            is_active=True,
        )
        db.add(resume_record)
        db.commit()
        db.refresh(resume_record)

        # Automated pgvector pipeline: extract text, chunk, generate 768-d embeddings, and save to Neon
        try:
            from app.automated_pipeline.processor import process_candidate_resume
            process_candidate_resume(resume_record.id, db=db, content=content)
        except Exception as exc:
            import logging
            logging.getLogger("api.candidates").error("Automated pipeline resume processing error: %s", exc)
    except Exception:
        db.rollback()
        # Clean up storage so orphaned files are not left behind
        storage_service.safe_delete_file(bucket=bucket, storage_path=storage_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record resume metadata in database. Upload has been cancelled.",
        ) from None

    # 6. Generate signed URL for authorized access
    download_url = None
    try:
        download_url = storage_service.get_signed_url(bucket=bucket, storage_path=storage_path)
    except Exception:
        pass

    return ResumeMetadataResponse(
        id=resume_record.id,
        candidate_profile_id=resume_record.candidate_profile_id,
        original_filename=resume_record.original_filename,
        storage_path=resume_record.storage_path,
        mime_type=resume_record.mime_type,
        file_size_bytes=resume_record.file_size_bytes,
        is_active=resume_record.is_active,
        download_url=download_url,
        created_at=resume_record.created_at,
        updated_at=resume_record.updated_at,
    )


@router.get(
    "/me/resume",
    response_model=ResumeMetadataResponse,
    summary="Get current active resume metadata and signed URL",
)
def get_candidate_resume(
    profile: CandidateProfile = Depends(get_candidate_profile),
    db: Session = Depends(get_db),
) -> ResumeMetadataResponse:
    resume_record = db.scalar(
        select(Resume)
        .where(
            Resume.candidate_profile_id == profile.id,
            Resume.is_active.is_(True),
        )
        .order_by(Resume.created_at.desc())
    )
    if not resume_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active resume found for this candidate.",
        )

    download_url = None
    try:
        download_url = storage_service.get_signed_url(
            bucket=settings.SUPABASE_STORAGE_BUCKET_RESUMES,
            storage_path=resume_record.storage_path,
        )
    except Exception:
        pass

    return ResumeMetadataResponse(
        id=resume_record.id,
        candidate_profile_id=resume_record.candidate_profile_id,
        original_filename=resume_record.original_filename,
        storage_path=resume_record.storage_path,
        mime_type=resume_record.mime_type,
        file_size_bytes=resume_record.file_size_bytes,
        is_active=resume_record.is_active,
        download_url=download_url,
        created_at=resume_record.created_at,
        updated_at=resume_record.updated_at,
    )


@router.get(
    "/me/resume/download",
    summary="Download candidate resume directly through authenticated endpoint",
)
def download_candidate_resume_direct(
    profile: CandidateProfile = Depends(get_candidate_profile),
    db: Session = Depends(get_db),
):
    resume_record = db.scalar(
        select(Resume)
        .where(
            Resume.candidate_profile_id == profile.id,
            Resume.is_active.is_(True),
        )
        .order_by(Resume.created_at.desc())
    )
    if not resume_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active resume found for this candidate.",
        )

    try:
        content = storage_service.download_file(
            bucket=settings.SUPABASE_STORAGE_BUCKET_RESUMES,
            storage_path=resume_record.storage_path,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not download file from storage: {str(exc)}",
        ) from exc

    return Response(
        content=content,
        media_type=resume_record.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{resume_record.original_filename}"'
        },
    )


@router.delete(
    "/me/resume",
    response_model=ResumeActionResponse,
    summary="Delete candidate's active resume",
)
def delete_candidate_resume(
    profile: CandidateProfile = Depends(get_candidate_profile),
    db: Session = Depends(get_db),
) -> ResumeActionResponse:
    resume_record = db.scalar(
        select(Resume)
        .where(
            Resume.candidate_profile_id == profile.id,
            Resume.is_active.is_(True),
        )
        .order_by(Resume.created_at.desc())
    )
    if not resume_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active resume found to delete.",
        )

    # Delete from storage
    storage_service.safe_delete_file(
        bucket=settings.SUPABASE_STORAGE_BUCKET_RESUMES,
        storage_path=resume_record.storage_path,
    )

    db.delete(resume_record)
    db.commit()

    return ResumeActionResponse(message="Resume deleted successfully.")


# -------------------------------------------------------------
# Candidate Accessibility Preferences Endpoints
# -------------------------------------------------------------


@router.get(
    "/me/accessibility",
    response_model=list[AccessibilityPreferenceResponse],
    summary="List candidate's accessibility preferences",
)
def list_candidate_accessibility_preferences(
    profile: CandidateProfile = Depends(get_candidate_profile),
    db: Session = Depends(get_db),
) -> list[AccessibilityPreferenceResponse]:
    preferences = db.scalars(
        select(AccommodationPreference)
        .where(AccommodationPreference.candidate_profile_id == profile.id)
        .order_by(AccommodationPreference.created_at.asc())
    ).all()
    return [AccessibilityPreferenceResponse.model_validate(p) for p in preferences]


@router.post(
    "/me/accessibility",
    response_model=AccessibilityPreferenceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an accessibility preference",
)
def create_candidate_accessibility_preference(
    payload: AccessibilityPreferenceCreate,
    profile: CandidateProfile = Depends(get_candidate_profile),
    db: Session = Depends(get_db),
) -> AccessibilityPreferenceResponse:
    preference = AccommodationPreference(
        candidate_profile_id=profile.id,
        category=payload.category.strip(),
        preference=payload.preference.strip(),
        details=payload.details.strip() if payload.details else None,
        is_active=payload.is_active,
    )
    db.add(preference)
    db.commit()
    db.refresh(preference)
    return AccessibilityPreferenceResponse.model_validate(preference)


@router.patch(
    "/me/accessibility/{preference_id}",
    response_model=AccessibilityPreferenceResponse,
    summary="Update an accessibility preference",
)
def update_candidate_accessibility_preference(
    preference_id: uuid.UUID,
    payload: AccessibilityPreferenceUpdate,
    profile: CandidateProfile = Depends(get_candidate_profile),
    db: Session = Depends(get_db),
) -> AccessibilityPreferenceResponse:
    preference = db.scalar(
        select(AccommodationPreference).where(
            AccommodationPreference.id == preference_id,
            AccommodationPreference.candidate_profile_id == profile.id,
        )
    )
    if not preference:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Accessibility preference not found.",
        )

    if payload.category is not None:
        preference.category = payload.category.strip()
    if payload.preference is not None:
        preference.preference = payload.preference.strip()
    if payload.details is not None:
        preference.details = payload.details.strip() if payload.details else None
    if payload.is_active is not None:
        preference.is_active = payload.is_active

    db.add(preference)
    db.commit()
    db.refresh(preference)
    return AccessibilityPreferenceResponse.model_validate(preference)


@router.delete(
    "/me/accessibility/{preference_id}",
    response_model=dict,
    summary="Delete an accessibility preference",
)
def delete_candidate_accessibility_preference(
    preference_id: uuid.UUID,
    profile: CandidateProfile = Depends(get_candidate_profile),
    db: Session = Depends(get_db),
) -> dict:
    preference = db.scalar(
        select(AccommodationPreference).where(
            AccommodationPreference.id == preference_id,
            AccommodationPreference.candidate_profile_id == profile.id,
        )
    )
    if not preference:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Accessibility preference not found.",
        )

    db.delete(preference)
    db.commit()
    return {"message": "Accessibility preference deleted successfully."}
