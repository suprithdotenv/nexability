"""create employer feature jobs applications and accommodations

Revision ID: 9eb22bbff6c0
Revises: 60526278fede
Create Date: 2026-11-03 16:54:10.384804

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9eb22bbff6c0'
down_revision: Union[str, Sequence[str], None] = '60526278fede'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema safely by creating employer feature tables only."""
    op.create_table(
        'job_postings',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('employer_profile_id', sa.Uuid(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('responsibilities', sa.Text(), nullable=True),
        sa.Column('requirements', sa.Text(), nullable=True),
        sa.Column('location', sa.String(length=200), nullable=True),
        sa.Column('work_mode', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['employer_profile_id'], ['employer_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_job_postings_employer_profile_id'), 'job_postings', ['employer_profile_id'], unique=False)

    op.create_table(
        'accommodation_requests',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('job_posting_id', sa.Uuid(), nullable=False),
        sa.Column('candidate_profile_id', sa.Uuid(), nullable=False),
        sa.Column('facility', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('response_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['candidate_profile_id'], ['candidate_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_posting_id'], ['job_postings.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_accommodation_requests_candidate_profile_id'), 'accommodation_requests', ['candidate_profile_id'], unique=False)
    op.create_index(op.f('ix_accommodation_requests_job_posting_id'), 'accommodation_requests', ['job_posting_id'], unique=False)

    op.create_table(
        'job_applications',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('job_posting_id', sa.Uuid(), nullable=False),
        sa.Column('candidate_profile_id', sa.Uuid(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('cover_note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['candidate_profile_id'], ['candidate_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_posting_id'], ['job_postings.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_job_applications_candidate_profile_id'), 'job_applications', ['candidate_profile_id'], unique=False)
    op.create_index(op.f('ix_job_applications_job_posting_id'), 'job_applications', ['job_posting_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema safely."""
    op.drop_index(op.f('ix_job_applications_job_posting_id'), table_name='job_applications')
    op.drop_index(op.f('ix_job_applications_candidate_profile_id'), table_name='job_applications')
    op.drop_table('job_applications')

    op.drop_index(op.f('ix_accommodation_requests_job_posting_id'), table_name='accommodation_requests')
    op.drop_index(op.f('ix_accommodation_requests_candidate_profile_id'), table_name='accommodation_requests')
    op.drop_table('accommodation_requests')

    op.drop_index(op.f('ix_job_postings_employer_profile_id'), table_name='job_postings')
    op.drop_table('job_postings')
