import io
import re
import uuid
import zipfile
from pathlib import Path

import httpx
from fastapi import HTTPException, UploadFile, status

from app.core.config import settings

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def sanitize_filename(filename: str) -> str:
    """Sanitize the uploaded filename to prevent directory traversal and harmful characters."""
    clean_name = Path(filename).name
    # Remove any non-alphanumeric, dot, underscore, hyphen characters
    clean_name = re.sub(r"[^a-zA-Z0-9._-]", "_", clean_name)
    if not clean_name or clean_name.startswith("."):
        clean_name = f"document{clean_name}"
    return clean_name[:200]


def validate_document_file(file: UploadFile, content: bytes) -> tuple[str, str]:
    """
    Validate file extension, size, and magic bytes/content structure.
    Returns (sanitized_filename, mime_type).
    Raises HTTPException on validation failure.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must have a filename",
        )

    clean_filename = sanitize_filename(file.filename)
    extension = Path(clean_filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file extension '{extension}'. Only PDF and DOCX files are accepted."
            ),
        )

    file_size = len(content)
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    max_mb = settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
    if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum allowed size of {max_mb}MB.",
        )

    # Magic byte validation
    if extension == ".pdf":
        if not content.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid PDF content: file header does not match PDF format.",
            )
        mime_type = "application/pdf"
    elif extension == ".docx":
        if not content.startswith(b"PK\x03\x04"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid DOCX content: file header does not match DOCX/ZIP format.",
            )
        # Deep inspection of docx zip structure
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                namelist = zf.namelist()
                if not any("[Content_Types].xml" in name or "word/" in name for name in namelist):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            "Invalid DOCX file structure: required Office Open XML contents"
                            " missing."
                        ),
                    )
        except zipfile.BadZipFile as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Corrupted DOCX archive.",
            ) from exc
        mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{extension}'.",
        )

    return clean_filename, mime_type


class StorageService:
    """
    Storage Service managing private uploads, signed URLs, and downloads
    with Supabase Storage, with fallback to an in-memory/mock store for unit testing.
    """

    def __init__(self):
        self.supabase_url = settings.SUPABASE_URL.rstrip("/") if settings.SUPABASE_URL else ""
        self.service_key = settings.SUPABASE_SERVICE_ROLE_KEY
        # In-memory mock store for local/testing environments when Supabase is not configured
        self._local_storage: dict[str, dict[str, bytes]] = {}

    @property
    def is_supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.service_key)

    def generate_storage_path(self, prefix: str, owner_id: str | uuid.UUID, filename: str) -> str:
        """Generate unique storage path: {prefix}/{owner_id}/{uuid4}_{filename}"""
        unique_id = uuid.uuid4().hex[:12]
        return f"{prefix}/{owner_id}/{unique_id}_{filename}"

    def upload_file(
        self,
        bucket: str,
        storage_path: str,
        content: bytes,
        mime_type: str,
    ) -> str:
        """
        Upload file content to private storage bucket.
        Returns the storage path.
        """
        if self.is_supabase_configured:
            url = f"{self.supabase_url}/storage/v1/object/{bucket}/{storage_path}"
            headers = {
                "apikey": self.service_key,
                "Authorization": f"Bearer {self.service_key}",
                "Content-Type": mime_type,
            }
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, content=content, headers=headers)
                if response.status_code not in (200, 201):
                    msg = (
                        f"Failed to upload to Supabase: {response.status_code} {response.text}"
                    )
                    raise RuntimeError(msg)
            return storage_path
        else:
            # Local mock storage
            if bucket not in self._local_storage:
                self._local_storage[bucket] = {}
            self._local_storage[bucket][storage_path] = content
            return storage_path

    def get_signed_url(
        self,
        bucket: str,
        storage_path: str,
        expires_in_seconds: int = 3600,
    ) -> str:
        """
        Generate a short-lived authorized URL to download the private document.
        """
        if self.is_supabase_configured:
            url = f"{self.supabase_url}/storage/v1/object/sign/{bucket}/{storage_path}"
            headers = {
                "apikey": self.service_key,
                "Authorization": f"Bearer {self.service_key}",
                "Content-Type": "application/json",
            }
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    url,
                    json={"expiresIn": expires_in_seconds},
                    headers=headers,
                )
                if response.status_code == 200:
                    data = response.json()
                    signed_part = data.get("signedURL", "")
                    return f"{self.supabase_url}/storage/v1{signed_part}"
                msg = f"Failed to get signed URL: {response.status_code} {response.text}"
                raise RuntimeError(msg)
        else:
            # Fallback signed URL for local/test mode
            return f"/api/v1/storage-fallback/{bucket}/{storage_path}?expires={expires_in_seconds}"

    def download_file(self, bucket: str, storage_path: str) -> bytes:
        """
        Download the original file content from private storage.
        """
        if self.is_supabase_configured:
            url = f"{self.supabase_url}/storage/v1/object/{bucket}/{storage_path}"
            headers = {
                "apikey": self.service_key,
                "Authorization": f"Bearer {self.service_key}",
            }
            with httpx.Client(timeout=30.0) as client:
                response = client.get(url, headers=headers)
                if response.status_code == 200:
                    return response.content
                msg = f"Download failed: {response.status_code} {response.text}"
                raise RuntimeError(msg)
        else:
            bucket_store = self._local_storage.get(bucket, {})
            if storage_path not in bucket_store:
                raise FileNotFoundError(
                    f"File '{storage_path}' not found in storage bucket '{bucket}'."
                )
            return bucket_store[storage_path]

    def delete_file(self, bucket: str, storage_path: str) -> bool:
        """
        Delete file from private storage.
        """
        if self.is_supabase_configured:
            url = f"{self.supabase_url}/storage/v1/object/{bucket}/{storage_path}"
            headers = {
                "apikey": self.service_key,
                "Authorization": f"Bearer {self.service_key}",
            }
            with httpx.Client(timeout=10.0) as client:
                response = client.delete(url, headers=headers)
                return response.status_code in (200, 204)
        else:
            bucket_store = self._local_storage.get(bucket, {})
            if storage_path in bucket_store:
                del bucket_store[storage_path]
                return True
            return False

    def safe_delete_file(self, bucket: str, storage_path: str) -> None:
        """
        Delete file and swallow errors, useful for rollback/cleanup after a DB failure.
        """
        try:
            self.delete_file(bucket, storage_path)
        except Exception:
            pass


storage_service = StorageService()
