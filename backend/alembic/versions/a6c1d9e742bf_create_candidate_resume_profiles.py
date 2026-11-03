"""create candidate resume profiles

Revision ID: a6c1d9e742bf
Revises: 60526278fede
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "a6c1d9e742bf"
down_revision: str | Sequence[str] | None = "60526278fede"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "candidate_resume_profiles",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("resume_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("profile_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column(
            "last_success_provider",
            sa.String(length=50),
            nullable=True,
        ),
        sa.Column("last_success_model", sa.String(length=255), nullable=True),
        sa.Column(
            "last_success_schema_version",
            sa.String(length=30),
            nullable=True,
        ),
        sa.Column("extraction_mode", sa.String(length=20), nullable=True),
        sa.Column("llm_skipped_reason", sa.String(length=50), nullable=True),
        sa.Column("error_details", sa.Text(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'PROCESSING', 'SUCCEEDED', 'FAILED')",
            name="ck_candidate_resume_profiles_status",
        ),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("resume_id", name="uq_candidate_resume_profiles_resume_id"),
    )
    op.create_index(
        "ix_candidate_resume_profiles_status_next_attempt",
        "candidate_resume_profiles",
        ["status", "next_attempt_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_candidate_resume_profiles_status_next_attempt",
        table_name="candidate_resume_profiles",
    )
    op.drop_table("candidate_resume_profiles")
