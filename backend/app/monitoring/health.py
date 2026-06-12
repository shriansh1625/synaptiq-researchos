"""Infrastructure health checks for readiness probes."""

from __future__ import annotations

from sqlalchemy import text

from app.cache.redis_client import get_redis_client
from app.database.session import get_engine


async def check_database() -> bool:
    """Return True when PostgreSQL accepts connections."""
    try:
        engine = get_engine()
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def check_redis() -> bool:
    """Return True when Redis responds to PING."""
    try:
        return await get_redis_client().health_check()
    except Exception:
        return False


async def collect_dependency_status() -> dict[str, str]:
    """Evaluate database and Redis connectivity."""
    database_ok = await check_database()
    redis_ok = await check_redis()

    return {
        "database": "up" if database_ok else "down",
        "redis": "up" if redis_ok else "down",
    }
