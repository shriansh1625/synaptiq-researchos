"""Async SQLAlchemy engine and session management."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config.settings import Settings, get_settings

_engine: AsyncEngine | None = None
SessionLocal: async_sessionmaker[AsyncSession] | None = None


def to_async_database_url(database_url: str) -> str:
    """Normalize a PostgreSQL URL for async SQLAlchemy with asyncpg."""
    url = make_url(database_url)
    if url.drivername in {
        "postgresql",
        "postgresql+psycopg",
        "postgresql+psycopg2",
        "postgresql+asyncpg",
    }:
        return url.set(drivername="postgresql+asyncpg").render_as_string(hide_password=False)
    return database_url


def asyncpg_connect_args(database_url: str) -> dict[str, Any]:
    """Return asyncpg connect args for managed Postgres hosts."""
    host = make_url(database_url).host or ""
    if host.endswith(".render.com"):
        return {"ssl": True}
    return {}


def create_engine_from_settings(settings: Settings | None = None, **engine_kwargs: Any) -> AsyncEngine:
    """Create an async SQLAlchemy engine from application settings."""
    resolved_settings = settings or get_settings()
    async_url = to_async_database_url(resolved_settings.database_url)
    connect_args = asyncpg_connect_args(async_url)
    if connect_args:
        engine_kwargs = {**engine_kwargs, "connect_args": connect_args}
    return create_async_engine(
        async_url,
        pool_pre_ping=True,
        **engine_kwargs,
    )


def get_engine(settings: Settings | None = None, **engine_kwargs: Any) -> AsyncEngine:
    """Return the shared async engine, creating it on first use."""
    global _engine
    if _engine is None:
        _engine = create_engine_from_settings(settings=settings, **engine_kwargs)
    return _engine


def get_session_local(
    settings: Settings | None = None,
    **engine_kwargs: Any,
) -> async_sessionmaker[AsyncSession]:
    """Return the shared async session factory, creating it on first use."""
    global SessionLocal
    if SessionLocal is None:
        SessionLocal = async_sessionmaker(
            bind=get_engine(settings=settings, **engine_kwargs),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
    return SessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session."""
    session_factory = get_session_local()
    session = session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def close_db() -> None:
    """Dispose the shared engine and reset session factory state."""
    global _engine, SessionLocal
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    SessionLocal = None


async def reset_database_state() -> None:
    """Reset database globals. Intended for tests."""
    await close_db()
