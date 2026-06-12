"""Tests for async database session management."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.database import session as session_module
from app.database.session import (
    close_db,
    create_engine_from_settings,
    get_db,
    get_engine,
    get_session_local,
    to_async_database_url,
)
from config.settings import Settings, get_settings

VALID_SETTINGS = {
    "database_url": "postgresql+asyncpg://user:pass@localhost:5432/synaptiq",
    "redis_url": "redis://localhost:6379/0",
    "gemini_api_key": "test-gemini-key",
}


@pytest.fixture(autouse=True)
def clean_database_state() -> None:
    """Ensure database globals do not leak between tests."""
    session_module._engine = None
    session_module.SessionLocal = None
    get_settings.cache_clear()
    yield
    session_module._engine = None
    session_module.SessionLocal = None
    get_settings.cache_clear()


@pytest.mark.parametrize(
    ("database_url", "expected"),
    [
        (
            "postgresql://user:pass@localhost:5432/synaptiq",
            "postgresql+asyncpg://user:pass@localhost:5432/synaptiq",
        ),
        (
            "postgresql+asyncpg://user:pass@localhost:5432/synaptiq",
            "postgresql+asyncpg://user:pass@localhost:5432/synaptiq",
        ),
        (
            "postgresql+psycopg://user:pass@localhost:5432/synaptiq",
            "postgresql+asyncpg://user:pass@localhost:5432/synaptiq",
        ),
        (
            "postgresql+psycopg2://user:pass@localhost:5432/synaptiq",
            "postgresql+asyncpg://user:pass@localhost:5432/synaptiq",
        ),
    ],
)
def test_to_async_database_url_normalizes_postgresql_urls(
    database_url: str,
    expected: str,
) -> None:
    """PostgreSQL URLs should be normalized for asyncpg."""
    assert to_async_database_url(database_url) == expected


def test_create_engine_from_settings_uses_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Engine creation should use the async database URL from settings."""
    settings = Settings(**VALID_SETTINGS)
    captured: dict[str, object] = {}

    def fake_create_engine(url: str, **kwargs: object) -> MagicMock:
        captured["url"] = url
        captured["kwargs"] = kwargs
        return MagicMock()

    monkeypatch.setattr(session_module, "create_async_engine", fake_create_engine)

    create_engine_from_settings(settings=settings)

    assert make_url(captured["url"]) == make_url(VALID_SETTINGS["database_url"])
    assert captured["kwargs"]["pool_pre_ping"] is True


def test_get_engine_is_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_engine should return the same engine instance."""
    fake_engine = MagicMock()
    monkeypatch.setattr(
        session_module,
        "create_engine_from_settings",
        lambda **_: fake_engine,
    )

    first = get_engine()
    second = get_engine()

    assert first is second
    assert first is fake_engine


def test_get_session_local_returns_async_sessionmaker(monkeypatch: pytest.MonkeyPatch) -> None:
    """Session factory should be an async SQLAlchemy sessionmaker."""
    fake_engine = MagicMock()
    monkeypatch.setattr(session_module, "get_engine", lambda **_: fake_engine)

    session_factory = get_session_local()

    assert isinstance(session_factory, async_sessionmaker)
    assert session_module.SessionLocal is session_factory


@pytest.mark.asyncio
async def test_get_db_commits_and_closes_on_success() -> None:
    """get_db should commit and close the session when no error occurs."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_factory = MagicMock(return_value=mock_session)

    with patch.object(session_module, "get_session_local", return_value=mock_factory):
        db_generator = get_db()
        session = await db_generator.__anext__()

        assert session is mock_session

        with pytest.raises(StopAsyncIteration):
            await db_generator.__anext__()

    mock_session.commit.assert_awaited_once()
    mock_session.rollback.assert_not_awaited()
    mock_session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_db_rolls_back_and_closes_on_error() -> None:
    """get_db should rollback and close the session when an error occurs."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_factory = MagicMock(return_value=mock_session)

    with patch.object(session_module, "get_session_local", return_value=mock_factory):
        db_generator = get_db()
        await db_generator.__anext__()

        with pytest.raises(RuntimeError, match="boom"):
            await db_generator.athrow(RuntimeError("boom"))

    mock_session.rollback.assert_awaited_once()
    mock_session.commit.assert_not_awaited()
    mock_session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_close_db_disposes_engine_and_resets_session_local(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """close_db should dispose the engine and clear session globals."""
    fake_engine = AsyncMock()
    fake_engine.dispose = AsyncMock()
    monkeypatch.setattr(session_module, "_engine", fake_engine)
    session_module.SessionLocal = async_sessionmaker(
        bind=MagicMock(),
        class_=AsyncSession,
        expire_on_commit=False,
    )

    await close_db()

    fake_engine.dispose.assert_awaited_once()
    assert session_module._engine is None
    assert session_module.SessionLocal is None
