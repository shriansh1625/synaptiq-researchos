"""High-level cache operations with JSON serialization and TTL support."""

from __future__ import annotations

import json
from typing import Any

from app.cache.redis_client import RedisClient, get_redis_client

_DEFAULT_SERVICE: CacheService | None = None


class CacheService:
    """JSON-backed cache helper built on the async Redis client."""

    def __init__(self, redis_client: RedisClient | None = None) -> None:
        self._redis_client = redis_client or get_redis_client()

    async def get(self, key: str) -> Any | None:
        """Return a deserialized cache value, or None when the key is absent."""
        raw_value = await self._redis_client.execute(lambda redis: redis.get(key))
        if raw_value is None:
            return None
        return json.loads(raw_value)

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Serialize and store a value. Optional ttl is in seconds."""
        payload = json.dumps(value)
        if ttl is not None:
            result = await self._redis_client.execute(
                lambda redis: redis.set(key, payload, ex=ttl)
            )
        else:
            result = await self._redis_client.execute(lambda redis: redis.set(key, payload))
        return bool(result)

    async def delete(self, key: str) -> int:
        """Delete a cache key. Returns the number of keys removed."""
        deleted = await self._redis_client.execute(lambda redis: redis.delete(key))
        return int(deleted)

    async def exists(self, key: str) -> bool:
        """Return True when the cache key exists."""
        count = await self._redis_client.execute(lambda redis: redis.exists(key))
        return bool(count)


def get_cache_service(redis_client: RedisClient | None = None) -> CacheService:
    """Return the shared cache service instance."""
    global _DEFAULT_SERVICE
    if redis_client is not None:
        return CacheService(redis_client=redis_client)
    if _DEFAULT_SERVICE is None:
        _DEFAULT_SERVICE = CacheService()
    return _DEFAULT_SERVICE


def reset_cache_service() -> None:
    """Reset the shared cache service. Intended for tests."""
    global _DEFAULT_SERVICE
    _DEFAULT_SERVICE = None


async def get(key: str) -> Any | None:
    """Fetch and deserialize a cached value."""
    return await get_cache_service().get(key)


async def set(key: str, value: Any, ttl: int | None = None) -> bool:
    """Serialize and store a cached value."""
    return await get_cache_service().set(key, value, ttl=ttl)


async def delete(key: str) -> int:
    """Delete a cached value."""
    return await get_cache_service().delete(key)


async def exists(key: str) -> bool:
    """Return whether a cache key exists."""
    return await get_cache_service().exists(key)
