from sqlalchemy import create_engine, pool

from alembic import context

# Import application configuration
from app.core.config import settings

# Import SQLAlchemy Base
from app.db.base import Base

# Import models so SQLAlchemy registers their tables
from app.models import (
    accommodation_preference,
    candidate_declaration,
    candidate_profile,
    email_otp,
    email_verification,
    employer_accessibility_capability,
    employer_profile,
    job_document,
    refresh_token,
    resume,
    user,
)
from employer_feature.models import (
    accommodation_request,
    job_application,
    job_posting,
)

config = context.config

# Connect Alembic with SQLAlchemy model metadata
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = settings.DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(
        settings.DATABASE_URL,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
