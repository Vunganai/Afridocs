"""
Alembic migrations environment.
Supports both offline (SQL generation) and online (live DB) modes.
Uses async SQLAlchemy to match the application engine.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

# Load app config and all models so Alembic sees them
from app.core.config import get_settings
from app.db.base import Base
import app.models  # noqa: F401 — registers all models on Base.metadata

# Alembic Config object — gives access to alembic.ini values
config = context.config

# Set up Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The metadata Alembic will compare against
target_metadata = Base.metadata


def get_database_url() -> str:
    settings = get_settings()
    return settings.database_url


def run_migrations_offline() -> None:
    """
    Run migrations without a live database connection.
    Produces a SQL script for manual review/application.
    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations against a live database using an async engine."""
    connectable = create_async_engine(
        get_database_url(),
        poolclass=pool.NullPool,  # NullPool avoids connection reuse issues in migrations
        connect_args={"statement_cache_size": 0},  # required for Supabase Session mode pooler
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
