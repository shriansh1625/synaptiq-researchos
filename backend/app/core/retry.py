"""Async retry helpers with exponential backoff."""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.core.exceptions import RateLimitError, UpstreamError

T = TypeVar("T")


async def async_retry(
    operation: Callable[[], Awaitable[T]],
    *,
    max_attempts: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 8.0,
    retry_on: tuple[type[Exception], ...] = (UpstreamError, RateLimitError, asyncio.TimeoutError),
) -> T:
    """Execute an async operation with exponential backoff and jitter."""
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await operation()
        except retry_on as exc:
            last_error = exc
            if attempt >= max_attempts:
                break
            delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
            delay += random.uniform(0, delay * 0.25)
            await asyncio.sleep(delay)
    assert last_error is not None
    raise last_error
