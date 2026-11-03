"""create job document profiles

Revision ID: b7e5d03f9a14
Revises: a6c1d9e742bf
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "b7e5d03f9a14"
down_revision: str | Sequence[str] | None = "a6c1d9e742bf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "job_document_profiles",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("document_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("profile_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="PENDING", nullable=False),
        sa.Column("last_success_provider", sa.String(length=50), nullable=True),
        sa.Column("last_success_model", sa.String(length=255), nullable=True),
        sa.Column("last_success_schema_version", sa.String(length=30), nullable=True),
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
            name="ck_job_document_profiles_status",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["job_documents.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", name="uq_job_document_profiles_document_id"),
    )
def downgrade() -> None:
    op.drop_table("job_document_profiles")
