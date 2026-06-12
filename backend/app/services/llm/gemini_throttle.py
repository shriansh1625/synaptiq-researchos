"""Lightweight Gemini request throttling to reduce quota / rate-limit hits."""

from __future__ import annotations

import asyncio
import os
import time

_semaphore: asyncio.Semaphore | None = None
_last_request_at = 0.0
_lock = asyncio.Lock()


def _max_concurrent() -> int:
    return max(1, int(os.getenv("GEMINI_MAX_CONCURRENT", "2")))


def _min_interval_sec() -> float:
    return max(0.0, float(os.getenv("GEMINI_MIN_INTERVAL_SEC", "0.4")))


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(_max_concurrent())
    return _semaphore


class GeminiThrottle:
    """Serialize Gemini calls with a small gap between requests."""

    async def __aenter__(self) -> GeminiThrottle:
        self._sem = _get_semaphore()
        await self._sem.acquire()
        global _last_request_at
        async with _lock:
            wait = _min_interval_sec() - (time.monotonic() - _last_request_at)
            if wait > 0:
                await asyncio.sleep(wait)
            _last_request_at = time.monotonic()
        return self

    async def __aexit__(self, *args: object) -> None:
        self._sem.release()
