from datetime import datetime
import uuid
from sqlalchemy import DateTime, ForeignKey, String, Text, Boolean, func, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class JobPosting(Base):
    __tablename__ = "job_postings"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    employer_profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("employer_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    responsibilities: Mapped[str | None] = mapped_column(Text, nullable=True)
    requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    work_mode: Mapped[str | None] = mapped_column(
        String(100), default="Hybrid", nullable=True
    )  # Remote, Hybrid, On-site
    status: Mapped[str] = mapped_column(
        String(50), default="ACTIVE", nullable=False
    )  # DRAFT, ACTIVE, CLOSED
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    employer = relationship("EmployerProfile", lazy="joined")
    applications = relationship(
        "JobApplication", back_populates="job_posting", cascade="all, delete-orphan"
    )
    accommodation_requests = relationship(
        "AccommodationRequest",
        back_populates="job_posting",
        cascade="all, delete-orphan",
    )
