import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_token
from app.db.session import get_db
from app.models.accommodation_preference import AccommodationPreference
from app.models.employer_accessibility_capability import EmployerAccessibilityCapability
from app.models.employer_profile import EmployerProfile
from app.models.job_document import JobDocument
from app.models.resume import Resume
from app.models.user import User, UserRole
from app.schemas.ml_access import (
    MLDocumentMetadataResponse,
    MLPendingQueueResponse,
)
from app.services.storage.storage_service import storage_service
from app.automated_pipeline.processor import _find_local_document

router = APIRouter()


def require_ml_authorization(
    x_internal_service_key: str | None = Header(None, alias="X-Internal-Service-Key"),
    authorization: str | None = Header(None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> bool:
    """
    Service-to-service authorization for internal ML components.
    Authorizes either via matching X-Internal-Service-Key or an ADMIN Bearer JWT.
    """
    if x_internal_service_key and settings.INTERNAL_ML_API_KEY:
        if x_internal_service_key == settings.INTERNAL_ML_API_KEY:
            return True

    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ", 1)[1]
        try:
            payload = decode_token(token)
            if payload.get("type") == "access":
                user_id = uuid.UUID(payload["sub"])
                user = db.scalar(select(User).where(User.id == user_id))
                if user and user.is_active and user.role == UserRole.ADMIN:
                    return True
        except Exception:
            pass

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=(
            "Unauthorized ML service access. Provide a valid internal service key or admin"
            " credentials."
        ),
    )


@router.get(
    "/resumes/{resume_id}",
    response_model=MLDocumentMetadataResponse,
    summary="[Internal ML] Retrieve resume metadata and signed access URL",
)
def get_ml_resume_metadata(
    resume_id: uuid.UUID,
    is_authorized: bool = Depends(require_ml_authorization),
    db: Session = Depends(get_db),
) -> MLDocumentMetadataResponse:
    resume = db.scalar(select(Resume).where(Resume.id == resume_id))
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found.",
        )

    signed_url = None
    try:
        signed_url = storage_service.get_signed_url(
            bucket=settings.SUPABASE_STORAGE_BUCKET_RESUMES,
            storage_path=resume.storage_path,
        )
    except Exception:
        pass

    return MLDocumentMetadataResponse(
        document_id=resume.id,
        document_type="RESUME",
        owner_id=resume.candidate_profile_id,
        original_filename=resume.original_filename,
        storage_path=resume.storage_path,
        mime_type=resume.mime_type,
        file_size_bytes=resume.file_size_bytes,
        signed_download_url=signed_url,
        created_at=resume.created_at,
    )


@router.get(
    "/resumes/{resume_id}/content",
    summary="[Internal ML] Download raw resume binary for document parsing pipeline",
)
def get_ml_resume_content(
    resume_id: uuid.UUID,
    is_authorized: bool = Depends(require_ml_authorization),
    db: Session = Depends(get_db),
):
    resume = db.scalar(select(Resume).where(Resume.id == resume_id))
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found.",
        )

    try:
        content = storage_service.download_file(
            bucket=settings.SUPABASE_STORAGE_BUCKET_RESUMES,
            storage_path=resume.storage_path,
        )
    except Exception as exc:
        content = _find_local_document(resume.original_filename)
        if not content:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not retrieve resume from private storage: {str(exc)}",
            ) from exc
        try:
            storage_service.upload_file(
                bucket=settings.SUPABASE_STORAGE_BUCKET_RESUMES,
                storage_path=resume.storage_path,
                content=content,
                mime_type=resume.mime_type,
            )
        except Exception:
            pass

    return Response(
        content=content,
        media_type=resume.mime_type,
        headers={"Content-Disposition": f'attachment; filename="{resume.original_filename}"'},
    )


@router.get(
    "/job-documents/{document_id}",
    response_model=MLDocumentMetadataResponse,
    summary="[Internal ML] Retrieve job document metadata and signed access URL",
)
def get_ml_job_document_metadata(
    document_id: uuid.UUID,
    is_authorized: bool = Depends(require_ml_authorization),
    db: Session = Depends(get_db),
) -> MLDocumentMetadataResponse:
    job_doc = db.scalar(select(JobDocument).where(JobDocument.id == document_id))
    if not job_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job document not found.",
        )

    signed_url = None
    try:
        signed_url = storage_service.get_signed_url(
            bucket=settings.SUPABASE_STORAGE_BUCKET_JOB_DOCS,
            storage_path=job_doc.storage_path,
        )
    except Exception:
        pass

    return MLDocumentMetadataResponse(
        document_id=job_doc.id,
        document_type="JOB_DOCUMENT",
        owner_id=job_doc.employer_profile_id,
        original_filename=job_doc.original_filename,
        storage_path=job_doc.storage_path,
        mime_type=job_doc.mime_type,
        file_size_bytes=job_doc.file_size_bytes,
        signed_download_url=signed_url,
        created_at=job_doc.created_at,
    )


@router.get(
    "/job-documents/{document_id}/content",
    summary="[Internal ML] Download raw job document binary for document parsing pipeline",
)
def get_ml_job_document_content(
    document_id: uuid.UUID,
    is_authorized: bool = Depends(require_ml_authorization),
    db: Session = Depends(get_db),
):
    job_doc = db.scalar(select(JobDocument).where(JobDocument.id == document_id))
    if not job_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job document not found.",
        )

    try:
        content = storage_service.download_file(
            bucket=settings.SUPABASE_STORAGE_BUCKET_JOB_DOCS,
            storage_path=job_doc.storage_path,
        )
    except Exception as exc:
        content = _find_local_document(job_doc.original_filename)
        if not content:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not retrieve job document from private storage: {str(exc)}",
            ) from exc
        try:
            storage_service.upload_file(
                bucket=settings.SUPABASE_STORAGE_BUCKET_JOB_DOCS,
                storage_path=job_doc.storage_path,
                content=content,
                mime_type=job_doc.mime_type,
            )
        except Exception:
            pass

    return Response(
        content=content,
        media_type=job_doc.mime_type,
        headers={"Content-Disposition": f'attachment; filename="{job_doc.original_filename}"'},
    )


@router.get(
    "/pending-documents",
    response_model=MLPendingQueueResponse,
    summary="[Internal ML] List pending documents ready for intelligent ML extraction",
)
def list_ml_pending_documents(
    is_authorized: bool = Depends(require_ml_authorization),
    db: Session = Depends(get_db),
) -> MLPendingQueueResponse:
    # Retrieve job descriptions with status "UPLOADED"
    pending_jobs = db.scalars(
        select(JobDocument)
        .where(JobDocument.status.in_(["UPLOADED", "PROCESSED"]))
        .order_by(JobDocument.created_at.asc())
    ).all()

    # Retrieve active resumes
    active_resumes = db.scalars(
        select(Resume).where(Resume.is_active.is_(True)).order_by(Resume.created_at.desc())
    ).all()

    from app.models.job_document_profile import JobDocumentProfile
    from app.models.candidate_resume_profile import CandidateResumeProfile

    job_profiles_map = {
        p.document_id: p.profile_json
        for p in db.scalars(
            select(JobDocumentProfile).where(
                JobDocumentProfile.document_id.in_([j.id for j in pending_jobs]),
                JobDocumentProfile.status == "SUCCEEDED",
            )
        ).all()
        if p.profile_json
    }

    resume_profiles_map = {
        p.resume_id: p.profile_json
        for p in db.scalars(
            select(CandidateResumeProfile).where(
                CandidateResumeProfile.resume_id.in_([r.id for r in active_resumes]),
                CandidateResumeProfile.status == "SUCCEEDED",
            )
        ).all()
        if p.profile_json
    }

    return MLPendingQueueResponse(
        pending_job_documents=[
            MLDocumentMetadataResponse(
                document_id=j.id,
                document_type="JOB_DOCUMENT",
                owner_id=j.employer_profile_id,
                original_filename=j.original_filename,
                storage_path=j.storage_path,
                mime_type=j.mime_type,
                file_size_bytes=j.file_size_bytes,
                created_at=j.created_at,
                parsed_profile=job_profiles_map.get(j.id),
            )
            for j in pending_jobs
        ],
        active_resumes=[
            MLDocumentMetadataResponse(
                document_id=r.id,
                document_type="RESUME",
                owner_id=r.candidate_profile_id,
                original_filename=r.original_filename,
                storage_path=r.storage_path,
                mime_type=r.mime_type,
                file_size_bytes=r.file_size_bytes,
                created_at=r.created_at,
                parsed_profile=resume_profiles_map.get(r.id),
            )
            for r in active_resumes
        ],
    )

@router.get(
    "/candidates/{candidate_id}/accessibility",
    summary="[Internal ML] Retrieve candidate accessibility preferences",
)
def get_ml_candidate_accessibility(
    candidate_id: uuid.UUID,
    is_authorized: bool = Depends(require_ml_authorization),
    db: Session = Depends(get_db),
):
    prefs = db.scalars(
        select(AccommodationPreference).where(
            AccommodationPreference.candidate_profile_id == candidate_id,
            AccommodationPreference.is_active.is_(True),
        )
    ).all()
    return {
        "candidate_id": str(candidate_id),
        "preferences": [
            {
                "category": p.category,
                "preference": p.preference,
                "details": p.details,
                "is_active": p.is_active,
            }
            for p in prefs
        ],
    }


@router.get(
    "/employers/{employer_id}/accessibility",
    summary="[Internal ML] Retrieve employer accessibility capabilities",
)
def get_ml_employer_accessibility(
    employer_id: uuid.UUID,
    is_authorized: bool = Depends(require_ml_authorization),
    db: Session = Depends(get_db),
):
    emp_prof = db.scalar(select(EmployerProfile).where(EmployerProfile.id == employer_id))
    company_name = emp_prof.company_name if emp_prof and emp_prof.company_name else "Innovative Technology Employer"
    verification_status = emp_prof.verification_status if emp_prof and emp_prof.verification_status else "VERIFIED"

    caps = db.scalars(
        select(EmployerAccessibilityCapability).where(
            EmployerAccessibilityCapability.employer_profile_id == employer_id
        )
    ).all()
    return {
        "employer_id": str(employer_id),
        "company_name": company_name,
        "verification_status": verification_status,
        "email_domain": emp_prof.email_domain if emp_prof else None,
        "website": emp_prof.website if emp_prof else None,
        "phone": emp_prof.phone if emp_prof else None,
        "profile_completed": len(caps) > 0,
        "capabilities": [
            {
                "category": c.category,
                "capability": c.capability,
                "status": c.status.value if hasattr(c.status, "value") else str(c.status),
                "details": c.details,
            }
            for c in caps
        ],
    }
