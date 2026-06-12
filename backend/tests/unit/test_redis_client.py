"""Tests for the async Redis client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from app.cache.redis_client import RedisClient, get_redis_client
from config.settings import Settings, get_settings

VALID_SETTINGS = {
    "database_url": "postgresql+asyncpg://user:pass@localhost:5432/synaptiq",
    "redis_url": "redis://localhost:6379/0",
    "gemini_api_key": "test-gemini-key",
}


@pytest.fixture(autouse=True)
async def reset_redis_singleton() -> None:
    """Ensure Redis singleton does not leak between tests."""
    await RedisClient.reset_instance()
    get_settings.cache_clear()
    yield
    await RedisClient.reset_instance()
    get_settings.cache_clear()


@pytest.fixture
def settings() -> Settings:
    """Provide test settings."""
    return Settings(**VALID_SETTINGS)


def test_get_redis_client_returns_singleton(settings: Settings) -> None:
    """get_redis_client should return the same manager instance."""
    first = get_redis_client(settings=settings)
    second = get_redis_client()

    assert first is second


@pytest.mark.asyncio
async def test_connect_uses_settings_redis_url(settings: Settings) -> None:
    """connect should initialize Redis.from_url with configured URL."""
    fake_redis = AsyncMock()
    fake_from_url = MagicMock(return_value=fake_redis)

    with patch("app.cache.redis_client.Redis.from_url", fake_from_url):
        client = RedisClient(settings=settings)
        redis = await client.connect()

    fake_from_url.assert_called_once()
    assert fake_from_url.call_args.kwargs["decode_responses"] is True
    assert fake_from_url.call_args.args[0] == settings.redis_url
    assert redis is fake_redis


@pytest.mark.asyncio
async def test_health_check_returns_true_on_ping(settings: Settings) -> None:
    """health_check should return True when Redis responds to PING."""
    fake_redis = AsyncMock()
    fake_redis.ping = AsyncMock(return_value=True)

    client = RedisClient(settings=settings)
    client._redis = fake_redis

    assert await client.health_check() is True
    fake_redis.ping.assert_awaited_once()


@pytest.mark.asyncio
async def test_health_check_returns_false_on_error(settings: Settings) -> None:
    """health_check should return False when Redis is unavailable."""
    fake_redis = AsyncMock()
    fake_redis.ping = AsyncMock(side_effect=RedisConnectionError("down"))

    client = RedisClient(settings=settings)
    client._redis = fake_redis

    assert await client.health_check() is False


@pytest.mark.asyncio
async def test_reconnect_closes_and_recreates_client(settings: Settings) -> None:
    """reconnect should close the old client and create a new connection."""
    old_redis = AsyncMock()
    new_redis = AsyncMock()

    client = RedisClient(settings=settings)
    client._redis = old_redis

    with patch("app.cache.redis_client.Redis.from_url", return_value=new_redis) as fake_from_url:
        redis = await client.reconnect()

    old_redis.aclose.assert_awaited_once()
    fake_from_url.assert_called_once()
    assert redis is new_redis
    assert client._redis is new_redis


@pytest.mark.asyncio
async def test_execute_reconnects_on_connection_error(settings: Settings) -> None:
    """execute should reconnect once and retry after a connection failure."""
    failing_redis = AsyncMock()
    failing_redis.get = AsyncMock(side_effect=RedisConnectionError("lost connection"))
    failing_redis.aclose = AsyncMock()

    recovered_redis = AsyncMock()
    recovered_redis.get = AsyncMock(return_value="cached-value")

    client = RedisClient(settings=settings)
    client._redis = failing_redis

    with patch("app.cache.redis_client.Redis.from_url", return_value=recovered_redis):
        result = await client.execute(lambda redis: redis.get("synq:key"))

    assert result == "cached-value"
    failing_redis.aclose.assert_awaited_once()
    recovered_redis.get.assert_awaited_once_with("synq:key")


@pytest.mark.asyncio
async def test_close_releases_connection(settings: Settings) -> None:
    """close should shut down the underlying Redis client."""
    fake_redis = AsyncMock()
    client = RedisClient(settings=settings)
    client._redis = fake_redis

    await client.close()

    fake_redis.aclose.assert_awaited_once()
    assert client._redis is None
