"""Async Redis client with singleton access and graceful reconnect."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError  # used by health_check

from config.settings import Settings, get_settings

T = TypeVar("T")


class RedisClient:
    """Singleton async Redis connection manager."""

    _instance: RedisClient | None = None

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._redis: Redis | None = None
        self._connection_lock = asyncio.Lock()

    @classmethod
    def get_instance(cls, settings: Settings | None = None) -> RedisClient:
        """Return the shared Redis client manager."""
        if cls._instance is None:
            cls._instance = cls(settings=settings)
        return cls._instance

    @property
    def redis_url(self) -> str:
        """Configured Redis connection URL."""
        return self._settings.redis_url

    async def connect(self) -> Redis:
        """Create or return the active Redis connection."""
        async with self._connection_lock:
            return await self._connect_unlocked()

    async def _connect_unlocked(self) -> Redis:
        """Initialize the Redis client without acquiring the connection lock."""
        if self._redis is None:
            self._redis = Redis.from_url(
                self.redis_url,
                decode_responses=True,
                health_check_interval=30,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )
        return self._redis

    async def get_client(self) -> Redis:
        """Return a connected Redis client."""
        if self._redis is None:
            return await self.connect()
        return self._redis

    async def health_check(self) -> bool:
        """Return True when Redis responds to PING."""
        try:
            client = await self.get_client()
            response = await client.ping()
            return bool(response)
        except RedisError:
            return False

    async def reconnect(self) -> Redis:
        """Close the current connection and establish a new one."""
        async with self._connection_lock:
            await self._close_unlocked()
            return await self._connect_unlocked()

    async def execute(
        self,
        operation: Callable[[Redis], Awaitable[T]],
        *,
        retry_on_connection_error: bool = True,
    ) -> T:
        """Execute a Redis operation with optional graceful reconnect."""
        try:
            client = await self.get_client()
            return await operation(client)
        except RedisConnectionError:
            if not retry_on_connection_error:
                raise
            client = await self.reconnect()
            return await operation(client)

    async def close(self) -> None:
        """Close the Redis connection and release resources."""
        async with self._connection_lock:
            await self._close_unlocked()

    async def _close_unlocked(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None

    @classmethod
    async def reset_instance(cls) -> None:
        """Reset the singleton. Intended for tests and application shutdown."""
        if cls._instance is not None:
            await cls._instance.close()
            cls._instance = None


def get_redis_client(settings: Settings | None = None) -> RedisClient:
    """Return the singleton Redis client manager."""
    return RedisClient.get_instance(settings=settings)


async def get_redis() -> Redis:
    """FastAPI-style helper that returns a connected Redis client."""
    return await get_redis_client().get_client()
