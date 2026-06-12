"""Unit tests for agent log repository and observability."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.database.repositories.agent_log_repository import (
    AgentLogRepository,
    normalize_agent_log_status,
)
from app.services.agents.observability import persist_agent_log


def test_normalize_agent_log_status_fits_database_column() -> None:
    """Long agent statuses should be normalized before persistence."""
    assert normalize_agent_log_status("insufficient_evidence") == "insufficient"
    assert len(normalize_agent_log_status("x" * 30)) == 20


@pytest.mark.asyncio
async def test_persist_agent_log_creates_entry() -> None:
    """persist_agent_log should delegate to AgentLogRepository.create."""
    session = AsyncMock()
    repo_mock = MagicMock()
    repo_mock.create = AsyncMock()
    session_id = uuid.uuid4()

    original_init = AgentLogRepository.__init__

    def _patched_init(self, _session):
        self._session = _session
        self.create = repo_mock.create

    AgentLogRepository.__init__ = _patched_init  # type: ignore[method-assign]
    try:
        await persist_agent_log(
            session,
            session_id=session_id,
            agent_result={
                "agent_log": {
                    "agent_name": "verification",
                    "input_data": {"query": "test"},
                    "output_data": {"verified_claim_count": 2},
                    "latency": 120,
                    "confidence_score": 0.9,
                    "status": "success",
                }
            },
        )
    finally:
        AgentLogRepository.__init__ = original_init  # type: ignore[method-assign]

    repo_mock.create.assert_awaited_once()
    kwargs = repo_mock.create.await_args.kwargs
    assert kwargs["session_id"] == session_id
    assert kwargs["agent_name"] == "verification"
    assert kwargs["latency"] == 120


@pytest.mark.asyncio
async def test_persist_agent_log_skips_without_log() -> None:
    """persist_agent_log should no-op when agent_log is missing."""
    session = AsyncMock()
    await persist_agent_log(session, session_id=uuid.uuid4(), agent_result={})
    session.add.assert_not_called()
