"""Tests for the cache service."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from app.cache import cache_service as cache_service_module
from app.cache.cache_service import CacheService, delete, exists, get, reset_cache_service, set
from app.cache.redis_client import RedisClient


@pytest.fixture(autouse=True)
def reset_cache() -> None:
    """Reset module-level cache service between tests."""
    reset_cache_service()
    yield
    reset_cache_service()


@pytest.fixture
def redis_client() -> AsyncMock:
    """Provide a mocked Redis client manager."""
    return AsyncMock(spec=RedisClient)


@pytest.fixture
def cache_service(redis_client: AsyncMock) -> CacheService:
    """Provide a cache service backed by a mocked Redis client."""
    return CacheService(redis_client=redis_client)


@pytest.mark.asyncio
async def test_get_returns_deserialized_json(
    cache_service: CacheService,
    redis_client: AsyncMock,
) -> None:
    """get() should deserialize JSON values from Redis."""
    payload = {"status": "healthy", "count": 3}
    async def fake_execute(operation):
        return await operation(_RedisStub(get_value=json.dumps(payload)))

    redis_client.execute = AsyncMock(side_effect=fake_execute)

    result = await cache_service.get("synq:test")

    assert result == payload


@pytest.mark.asyncio
async def test_get_returns_none_for_missing_key(
    cache_service: CacheService,
    redis_client: AsyncMock,
) -> None:
    """get() should return None when the key does not exist."""
    async def fake_execute(operation):
        return await operation(_RedisStub(get_value=None))

    redis_client.execute = AsyncMock(side_effect=fake_execute)

    result = await cache_service.get("synq:missing")

    assert result is None


@pytest.mark.asyncio
async def test_set_serializes_json_without_ttl(
    cache_service: CacheService,
    redis_client: AsyncMock,
) -> None:
    """set() should JSON-encode values and store them without TTL."""
    captured: dict[str, object] = {}
    async def fake_execute(operation):
        return await operation(_RecordingRedis(captured))

    redis_client.execute = AsyncMock(side_effect=fake_execute)

    result = await cache_service.set("synq:test", {"agent": "discovery"})

    assert result is True
    assert captured["key"] == "synq:test"
    assert json.loads(str(captured["value"])) == {"agent": "discovery"}
    assert captured["ttl"] is None


@pytest.mark.asyncio
async def test_set_applies_ttl_in_seconds(
    cache_service: CacheService,
    redis_client: AsyncMock,
) -> None:
    """set() should pass TTL to Redis as expiration seconds."""
    captured: dict[str, object] = {}
    async def fake_execute(operation):
        return await operation(_RecordingRedis(captured))

    redis_client.execute = AsyncMock(side_effect=fake_execute)

    await cache_service.set("synq:test", ["a", "b"], ttl=300)

    assert captured["ttl"] == 300


@pytest.mark.asyncio
async def test_delete_removes_key(
    cache_service: CacheService,
    redis_client: AsyncMock,
) -> None:
    """delete() should remove a key and return the deletion count."""
    redis_client.execute = AsyncMock(return_value=1)

    deleted = await cache_service.delete("synq:test")

    assert deleted == 1
    redis_client.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_exists_returns_true_when_key_present(
    cache_service: CacheService,
    redis_client: AsyncMock,
) -> None:
    """exists() should return True when Redis reports the key exists."""
    redis_client.execute = AsyncMock(return_value=1)

    assert await cache_service.exists("synq:test") is True


@pytest.mark.asyncio
async def test_exists_returns_false_when_key_missing(
    cache_service: CacheService,
    redis_client: AsyncMock,
) -> None:
    """exists() should return False when Redis reports the key is absent."""
    redis_client.execute = AsyncMock(return_value=0)

    assert await cache_service.exists("synq:test") is False


@pytest.mark.asyncio
async def test_module_level_set_delegates_to_cache_service(redis_client: AsyncMock) -> None:
    """Module-level set() should use the shared cache service."""
    cache_service_module._DEFAULT_SERVICE = CacheService(redis_client=redis_client)
    redis_client.execute = AsyncMock(return_value=True)

    result = await set("synq:module", {"ok": True}, ttl=60)

    assert result is True
    redis_client.execute.assert_awaited_once()


class _RecordingRedis:
    """Minimal Redis stub that records set() calls."""

    def __init__(self, captured: dict[str, object]) -> None:
        self._captured = captured

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        self._captured["key"] = key
        self._captured["value"] = value
        self._captured["ttl"] = ex
        return True


class _RedisStub:
    """Minimal Redis stub for get/exists/delete operations."""

    def __init__(self, get_value: str | None = None, exists_value: int = 0) -> None:
        self._get_value = get_value
        self._exists_value = exists_value

    async def get(self, key: str) -> str | None:
        return self._get_value

    async def exists(self, key: str) -> int:
        return self._exists_value

    async def delete(self, key: str) -> int:
        return 1
