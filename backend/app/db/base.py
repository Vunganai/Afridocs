"""
SQLAlchemy async engine and session factory.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


def create_engine():
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        echo=not settings.is_production,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        connect_args={"statement_cache_size": 0},  # required for Supabase Session mode pooler
    )


engine = create_engine()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)
