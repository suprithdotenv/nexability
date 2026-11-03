import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CandidateResumeProfile(Base):
    __tablename__ = "candidate_resume_profiles"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'PROCESSING', 'SUCCEEDED', 'FAILED')",
            name="ck_candidate_resume_profiles_status",
        ),
        Index(
            "ix_candidate_resume_profiles_status_next_attempt",
            "status",
            "next_attempt_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    resume_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    profile_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="PENDING",
        server_default="PENDING",
    )
    last_success_provider: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    last_success_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_success_schema_version: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )
    extraction_mode: Mapped[str | None] = mapped_column(String(20), nullable=True)
    llm_skipped_reason: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    next_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
