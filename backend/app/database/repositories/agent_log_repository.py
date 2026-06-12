"""Repository for persisting agent execution logs."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.agent_log import AgentLog

_MAX_STATUS_LENGTH = 20
_STATUS_ALIASES = {
    "insufficient_evidence": "insufficient",
    "insufficient_context": "insufficient",
    "insufficient_claims": "insufficient",
}


def normalize_agent_log_status(status: str) -> str:
    """Normalize agent status values to fit the persisted schema."""
    normalized = (status or "unknown").strip() or "unknown"
    normalized = _STATUS_ALIASES.get(normalized, normalized)
    return normalized[:_MAX_STATUS_LENGTH]


class AgentLogRepository:
    """Persist agent observability records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        session_id: uuid.UUID,
        agent_name: str,
        input_data: dict[str, Any],
        output_data: dict[str, Any],
        latency: int,
        confidence_score: float | None,
        status: str,
    ) -> AgentLog:
        """Create an agent log row."""
        entry = AgentLog(
            session_id=session_id,
            agent_name=agent_name,
            input_data=input_data,
            output_data=output_data,
            latency=latency,
            confidence_score=confidence_score,
            status=normalize_agent_log_status(status),
        )
        self._session.add(entry)
        await self._session.flush()
        return entry
