from typing import Any
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MLDocumentMetadataResponse(BaseModel):
    document_id: UUID
    document_type: str  # "RESUME" or "JOB_DOCUMENT"
    owner_id: UUID
    original_filename: str
    storage_path: str
    mime_type: str
    file_size_bytes: int
    signed_download_url: str | None = None
    created_at: datetime
    parsed_profile: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)


class MLPendingQueueResponse(BaseModel):
    pending_job_documents: list[MLDocumentMetadataResponse]
    active_resumes: list[MLDocumentMetadataResponse]
