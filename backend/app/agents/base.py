"""Base agent with retry, logging, and structured error handling."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

from app.core.exceptions import AgentExecutionError
from app.core.retry import async_retry
from app.models.enums import AgentName
from app.monitoring.logger import get_logger
from app.schemas.agent_io import AgentError, AgentMessage


class BaseAgent(ABC):
    """Common agent execution wrapper."""

    agent_name: AgentName

    def __init__(self, max_attempts: int = 3) -> None:
        self._max_attempts = max_attempts
        self._logger = get_logger(self.__class__.__name__)

    @abstractmethod
    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        """Agent-specific implementation."""

    async def run(self, **kwargs: Any) -> dict[str, Any]:
        """Execute the agent with retries and structured logging."""
        started = time.perf_counter()
        messages: list[AgentMessage] = []
        errors: list[AgentError] = []

        messages.append(
            AgentMessage(
                agent=self.agent_name,
                status="running",
                message=f"{self.agent_name.value} started",
                progress=0.1,
            )
        )

        try:
            result = await async_retry(
                lambda: self._execute(**kwargs),
                max_attempts=self._max_attempts,
                retry_on=(AgentExecutionError,),
            )
            latency_ms = int((time.perf_counter() - started) * 1000)
            messages.append(
                AgentMessage(
                    agent=self.agent_name,
                    status="success",
                    message=f"{self.agent_name.value} completed",
                    progress=1.0,
                )
            )
            self._logger.info(
                f"{self.agent_name.value} completed",
                latency_ms=latency_ms,
            )
            result.setdefault("messages", []).extend(
                [message.model_dump(mode="json") for message in messages]
            )
            agent_log = dict(result.get("agent_log") or {})
            agent_log.setdefault("agent_name", self.agent_name.value)
            agent_log["latency"] = latency_ms
            agent_log.setdefault("status", "success")
            result["agent_log"] = agent_log
            return result
        except Exception as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            agent_error = AgentError(
                agent=self.agent_name,
                error_type=exc.__class__.__name__,
                message=str(exc),
                retryable=True,
            )
            errors.append(agent_error)
            self._logger.error(
                f"{self.agent_name.value} failed",
                error=str(exc),
                latency_ms=latency_ms,
            )
            return {
                "errors": [error.model_dump(mode="json") for error in errors],
                "messages": [message.model_dump(mode="json") for message in messages],
                "agent_log": {
                    "agent_name": self.agent_name.value,
                    "latency": latency_ms,
                    "status": "error",
                    "error": str(exc),
                },
            }
