from datetime import datetime
import uuid
from sqlalchemy import DateTime, ForeignKey, String, Text, func, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class JobApplication(Base):
    __tablename__ = "job_applications"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_posting_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("job_postings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50), default="APPLIED", nullable=False
    )  # APPLIED, REVIEWING, SHORTLISTED, REJECTED, ACCEPTED
    cover_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    job_posting = relationship("JobPosting", back_populates="applications")
    candidate_profile = relationship("CandidateProfile", lazy="joined")
