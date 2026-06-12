"""Agent observability helpers."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories.agent_log_repository import AgentLogRepository
from app.monitoring.logger import get_logger

logger = get_logger(__name__)


async def persist_agent_log(
    session: AsyncSession,
    *,
    session_id: str | uuid.UUID,
    agent_result: dict[str, Any],
) -> None:
    """Persist agent run metadata to AgentLog when available."""
    agent_log = agent_result.get("agent_log")
    if not agent_log:
        return

    repo = AgentLogRepository(session)
    session_uuid = uuid.UUID(str(session_id))
    input_data = agent_log.get("input_data") or agent_result.get("input_data") or {}
    output_data = agent_log.get("output_data") or agent_result.get("output_data") or agent_result

    try:
        await repo.create(
            session_id=session_uuid,
            agent_name=str(agent_log.get("agent_name", "unknown")),
            input_data=input_data,
            output_data=output_data if isinstance(output_data, dict) else {"result": output_data},
            latency=int(agent_log.get("latency", 0)),
            confidence_score=agent_log.get("confidence_score"),
            status=str(agent_log.get("status", "unknown")),
        )
    except SQLAlchemyError as exc:
        await session.rollback()
        logger.error(
            "Agent log persistence failed",
            agent_name=agent_log.get("agent_name"),
            error=str(exc),
        )
        return
    logger.info(
        "Agent log persisted",
        agent_name=agent_log.get("agent_name"),
        latency_ms=agent_log.get("latency"),
        status=agent_log.get("status"),
    )
