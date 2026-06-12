"""Background analysis tasks for non-blocking API responses."""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from app.database.session import get_session_local
from app.services.pipeline.research_pipeline import ResearchPipelineService

logger = logging.getLogger(__name__)

_running: set[str] = set()


def is_analysis_running(session_id: uuid.UUID | str) -> bool:
    return str(session_id) in _running


async def run_analysis_background(
    *,
    session_id: uuid.UUID,
    query: str,
    filters: dict[str, Any] | None = None,
    options: dict[str, Any] | None = None,
) -> None:
    """Execute the pipeline in a detached DB session (for async API)."""
    key = str(session_id)
    if key in _running:
        return
    _running.add(key)
    session_factory = get_session_local()
    try:
        async with session_factory() as db:
            pipeline = ResearchPipelineService(db)
            await pipeline.run_analysis(
                session_id=session_id,
                query=query,
                filters=filters,
                options=options,
            )
    except Exception:
        logger.exception("Background analysis failed", extra={"session_id": key})
    finally:
        _running.discard(key)


def spawn_analysis_background(**kwargs: Any) -> None:
    """Fire-and-forget background analysis."""
    asyncio.create_task(run_analysis_background(**kwargs))
