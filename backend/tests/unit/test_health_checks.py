"""Tests for infrastructure health checks."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.monitoring.health import check_database, check_redis, collect_dependency_status


@pytest.mark.asyncio
async def test_check_database_returns_true_on_success() -> None:
    """check_database should return True when SELECT 1 succeeds."""
    connection = AsyncMock()
    connection.execute = AsyncMock()
    connect_cm = AsyncMock()
    connect_cm.__aenter__.return_value = connection
    connect_cm.__aexit__.return_value = None

    engine = MagicMock()
    engine.connect.return_value = connect_cm

    with patch("app.monitoring.health.get_engine", return_value=engine):
        assert await check_database() is True


@pytest.mark.asyncio
async def test_check_database_returns_false_on_error() -> None:
    """check_database should return False when the database is unreachable."""
    with patch("app.monitoring.health.get_engine", side_effect=OSError("connection refused")):
        assert await check_database() is False


@pytest.mark.asyncio
async def test_check_redis_returns_true_on_success() -> None:
    """check_redis should return True when Redis health_check passes."""
    redis_client = MagicMock()
    redis_client.health_check = AsyncMock(return_value=True)

    with patch("app.monitoring.health.get_redis_client", return_value=redis_client):
        assert await check_redis() is True


@pytest.mark.asyncio
async def test_collect_dependency_status_reports_all_services() -> None:
    """collect_dependency_status should report database and Redis state."""
    with (
        patch("app.monitoring.health.check_database", AsyncMock(return_value=True)),
        patch("app.monitoring.health.check_redis", AsyncMock(return_value=False)),
    ):
        status = await collect_dependency_status()

    assert status == {"database": "up", "redis": "down"}
