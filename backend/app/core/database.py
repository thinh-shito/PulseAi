from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


# ── Lazy engine — created on first use, not at import time ───────────────────
# This pattern ensures unit tests can import app modules without asyncpg installed.

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Return (and lazily create) the async engine singleton."""
    global _engine
    if _engine is None:
        kwargs = {
            "echo": settings.environment == "development",
        }
        if "sqlite" not in settings.database_url:
            kwargs.update({
                "pool_pre_ping": True,
                "pool_size": 10,
                "max_overflow": 20,
            })
        _engine = create_async_engine(
            settings.database_url,
            **kwargs
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return (and lazily create) the session factory singleton."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields a database session and closes it after request."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
