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
from app.models.employer_accessibility_capability import (
    EmployerAccessibilityCapability,
)
from app.models.employer_profile import EmployerProfile
from app.models.job_document import JobDocument
from app.models.user import User, UserRole
from app.schemas.employer import (
    EmployerAccessibilityCreate,
    EmployerAccessibilityResponse,
    EmployerAccessibilityUpdate,
    EmployerProfileResponse,
    EmployerProfileUpdate,
    JobDocumentActionResponse,
    JobDocumentResponse,
)
from app.services.storage.storage_service import (
    storage_service,
    validate_document_file,
)

router = APIRouter()


def get_employer_profile(
    current_user: User = Depends(require_role(UserRole.EMPLOYER)),
    db: Session = Depends(get_db),
) -> EmployerProfile:
    """Helper dependency to retrieve the employer profile for the authenticated employer."""
    profile = db.scalar(select(EmployerProfile).where(EmployerProfile.user_id == current_user.id))
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employer profile not found.",
        )
    return profile


# -------------------------------------------------------------
# Employer / Company Profile Endpoints
# -------------------------------------------------------------


@router.get(
    "/me",
    response_model=EmployerProfileResponse,
    summary="Get current employer company profile",
)
def get_my_employer_profile(
    current_user: User = Depends(require_role(UserRole.EMPLOYER)),
    profile: EmployerProfile = Depends(get_employer_profile),
) -> EmployerProfileResponse:
    return EmployerProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        email=current_user.email,
        full_name=profile.full_name,
        company_name=profile.company_name,
        email_domain=profile.email_domain,
        website=profile.website,
        phone=profile.phone,
        verification_status=profile.verification_status,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@router.patch(
    "/me",
    response_model=EmployerProfileResponse,
    summary="Update employer company profile",
)
def update_my_employer_profile(
    payload: EmployerProfileUpdate,
    current_user: User = Depends(require_role(UserRole.EMPLOYER)),
    profile: EmployerProfile = Depends(get_employer_profile),
    db: Session = Depends(get_db),
) -> EmployerProfileResponse:
    if payload.full_name is not None:
        profile.full_name = payload.full_name.strip()
    if payload.company_name is not None:
        profile.company_name = payload.company_name.strip()
    if payload.website is not None:
        profile.website = payload.website.strip() if payload.website else None
    if payload.phone is not None:
        profile.phone = payload.phone.strip() if payload.phone else None

    # Preserves existing verification_status - employers cannot self-verify!
    db.add(profile)
    db.commit()
    db.refresh(profile)

    return EmployerProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        email=current_user.email,
        full_name=profile.full_name,
        company_name=profile.company_name,
        email_domain=profile.email_domain,
        website=profile.website,
        phone=profile.phone,
        verification_status=profile.verification_status,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


# -------------------------------------------------------------
# Job Description Document Endpoints
# -------------------------------------------------------------


@router.post(
    "/me/job-documents",
    response_model=JobDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload job description document (PDF or DOCX)",
)
async def upload_job_document(
    file: Annotated[UploadFile, File(description="Job description document (PDF or DOCX)")],
    profile: EmployerProfile = Depends(get_employer_profile),
    db: Session = Depends(get_db),
) -> JobDocumentResponse:
    # 1. Read file content
    content = await file.read()

    # 2. Validate format, size and magic bytes
    clean_filename, mime_type = validate_document_file(file, content)

    # 3. Generate private storage path
    storage_path = storage_service.generate_storage_path(
        prefix="employers",
        owner_id=profile.id,
        filename=clean_filename,
    )

    bucket = settings.SUPABASE_STORAGE_BUCKET_JOB_DOCS

    # 4. Upload file to private Supabase storage
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

    # 5. Persist document metadata in PostgreSQL, handling cleanup if DB fails
    try:
        doc_record = JobDocument(
            employer_profile_id=profile.id,
            original_filename=clean_filename,
            storage_path=storage_path,
            mime_type=mime_type,
            file_size_bytes=len(content),
            status="UPLOADED",
        )
        db.add(doc_record)
        db.commit()
        db.refresh(doc_record)

        # Automated pgvector pipeline: extract text, chunk, generate 768-d embeddings, and save to Neon
        try:
            from app.automated_pipeline.processor import process_job_document
            process_job_document(doc_record.id, db=db, content=content)
        except Exception as exc:
            import logging
            logging.getLogger("api.employers").error("Automated pipeline job processing error: %s", exc)
    except Exception:
        db.rollback()
        # Clean up storage so orphaned files are not left behind
        storage_service.safe_delete_file(bucket=bucket, storage_path=storage_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record document metadata in database. Upload has been cancelled.",
        ) from None

    # 6. Generate signed URL for authorized access
    download_url = None
    try:
        download_url = storage_service.get_signed_url(bucket=bucket, storage_path=storage_path)
    except Exception:
        pass

    return JobDocumentResponse(
        id=doc_record.id,
        employer_profile_id=doc_record.employer_profile_id,
        original_filename=doc_record.original_filename,
        storage_path=doc_record.storage_path,
        mime_type=doc_record.mime_type,
        file_size_bytes=doc_record.file_size_bytes,
        status=doc_record.status,
        download_url=download_url,
        created_at=doc_record.created_at,
        updated_at=doc_record.updated_at,
    )


@router.get(
    "/me/job-documents",
    response_model=list[JobDocumentResponse],
    summary="List uploaded job description documents for current employer",
)
def list_my_job_documents(
    profile: EmployerProfile = Depends(get_employer_profile),
    db: Session = Depends(get_db),
) -> list[JobDocumentResponse]:
    docs = db.scalars(
        select(JobDocument)
        .where(JobDocument.employer_profile_id == profile.id)
        .order_by(JobDocument.created_at.desc())
    ).all()

    result = []
    bucket = settings.SUPABASE_STORAGE_BUCKET_JOB_DOCS
    for doc in docs:
        download_url = None
        try:
            download_url = storage_service.get_signed_url(
                bucket=bucket, storage_path=doc.storage_path
            )
        except Exception:
            pass
        result.append(
            JobDocumentResponse(
                id=doc.id,
                employer_profile_id=doc.employer_profile_id,
                original_filename=doc.original_filename,
                storage_path=doc.storage_path,
                mime_type=doc.mime_type,
                file_size_bytes=doc.file_size_bytes,
                status=doc.status,
                download_url=download_url,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
            )
        )
    return result


@router.get(
    "/me/job-documents/{document_id}",
    response_model=JobDocumentResponse,
    summary="Get metadata and signed URL for a specific job document",
)
def get_my_job_document(
    document_id: uuid.UUID,
    profile: EmployerProfile = Depends(get_employer_profile),
    db: Session = Depends(get_db),
) -> JobDocumentResponse:
    doc = db.scalar(
        select(JobDocument).where(
            JobDocument.id == document_id,
            JobDocument.employer_profile_id == profile.id,
        )
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job document not found or access denied.",
        )

    download_url = None
    try:
        download_url = storage_service.get_signed_url(
            bucket=settings.SUPABASE_STORAGE_BUCKET_JOB_DOCS,
            storage_path=doc.storage_path,
        )
    except Exception:
        pass

    return JobDocumentResponse(
        id=doc.id,
        employer_profile_id=doc.employer_profile_id,
        original_filename=doc.original_filename,
        storage_path=doc.storage_path,
        mime_type=doc.mime_type,
        file_size_bytes=doc.file_size_bytes,
        status=doc.status,
        download_url=download_url,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.get(
    "/me/job-documents/{document_id}/download",
    summary="Download job document directly through authenticated endpoint",
)
def download_my_job_document_direct(
    document_id: uuid.UUID,
    profile: EmployerProfile = Depends(get_employer_profile),
    db: Session = Depends(get_db),
):
    doc = db.scalar(
        select(JobDocument).where(
            JobDocument.id == document_id,
            JobDocument.employer_profile_id == profile.id,
        )
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job document not found or access denied.",
        )

    try:
        content = storage_service.download_file(
            bucket=settings.SUPABASE_STORAGE_BUCKET_JOB_DOCS,
            storage_path=doc.storage_path,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not download file from storage: {str(exc)}",
        ) from exc

    return Response(
        content=content,
        media_type=doc.mime_type,
        headers={"Content-Disposition": f'attachment; filename="{doc.original_filename}"'},
    )


@router.delete(
    "/me/job-documents/{document_id}",
    response_model=JobDocumentActionResponse,
    summary="Delete an uploaded job description document",
)
def delete_my_job_document(
    document_id: uuid.UUID,
    profile: EmployerProfile = Depends(get_employer_profile),
    db: Session = Depends(get_db),
) -> JobDocumentActionResponse:
    doc = db.scalar(
        select(JobDocument).where(
            JobDocument.id == document_id,
            JobDocument.employer_profile_id == profile.id,
        )
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job document not found or access denied.",
        )

    # Delete file from storage
    storage_service.safe_delete_file(
        bucket=settings.SUPABASE_STORAGE_BUCKET_JOB_DOCS,
        storage_path=doc.storage_path,
    )

    db.delete(doc)
    db.commit()

    return JobDocumentActionResponse(message="Job document deleted successfully.")


# -------------------------------------------------------------
# Employer Accessibility Capabilities Endpoints
# -------------------------------------------------------------


@router.get(
    "/me/accessibility",
    response_model=list[EmployerAccessibilityResponse],
    summary="List company accessibility capabilities",
)
def list_company_accessibility_capabilities(
    profile: EmployerProfile = Depends(get_employer_profile),
    db: Session = Depends(get_db),
) -> list[EmployerAccessibilityResponse]:
    capabilities = db.scalars(
        select(EmployerAccessibilityCapability)
        .where(EmployerAccessibilityCapability.employer_profile_id == profile.id)
        .order_by(EmployerAccessibilityCapability.created_at.asc())
    ).all()
    return [EmployerAccessibilityResponse.model_validate(c) for c in capabilities]


@router.post(
    "/me/accessibility",
    response_model=EmployerAccessibilityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a company accessibility capability",
)
def create_company_accessibility_capability(
    payload: EmployerAccessibilityCreate,
    profile: EmployerProfile = Depends(get_employer_profile),
    db: Session = Depends(get_db),
) -> EmployerAccessibilityResponse:
    cap = EmployerAccessibilityCapability(
        employer_profile_id=profile.id,
        category=payload.category.strip(),
        capability=payload.capability.strip(),
        status=payload.status,
        details=payload.details.strip() if payload.details else None,
    )
    db.add(cap)
    db.commit()
    db.refresh(cap)
    return EmployerAccessibilityResponse.model_validate(cap)


@router.patch(
    "/me/accessibility/{capability_id}",
    response_model=EmployerAccessibilityResponse,
    summary="Update a company accessibility capability",
)
def update_company_accessibility_capability(
    capability_id: uuid.UUID,
    payload: EmployerAccessibilityUpdate,
    profile: EmployerProfile = Depends(get_employer_profile),
    db: Session = Depends(get_db),
) -> EmployerAccessibilityResponse:
    cap = db.scalar(
        select(EmployerAccessibilityCapability).where(
            EmployerAccessibilityCapability.id == capability_id,
            EmployerAccessibilityCapability.employer_profile_id == profile.id,
        )
    )
    if not cap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Accessibility capability not found or access denied.",
        )

    if payload.category is not None:
        cap.category = payload.category.strip()
    if payload.capability is not None:
        cap.capability = payload.capability.strip()
    if payload.status is not None:
        cap.status = payload.status
    if payload.details is not None:
        cap.details = payload.details.strip() if payload.details else None

    db.add(cap)
    db.commit()
    db.refresh(cap)
    return EmployerAccessibilityResponse.model_validate(cap)


@router.delete(
    "/me/accessibility/{capability_id}",
    response_model=dict,
    summary="Delete a company accessibility capability",
)
def delete_company_accessibility_capability(
    capability_id: uuid.UUID,
    profile: EmployerProfile = Depends(get_employer_profile),
    db: Session = Depends(get_db),
) -> dict:
    cap = db.scalar(
        select(EmployerAccessibilityCapability).where(
            EmployerAccessibilityCapability.id == capability_id,
            EmployerAccessibilityCapability.employer_profile_id == profile.id,
        )
    )
    if not cap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Accessibility capability not found or access denied.",
        )

    db.delete(cap)
    db.commit()
    return {"message": "Accessibility capability deleted successfully."}
