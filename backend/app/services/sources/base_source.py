"""Abstract paper source connector."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from app.core.exceptions import SourceUnavailableError
from app.models.enums import PaperSource
from app.schemas.common import PaperRef


@dataclass
class SourceSearchResult:
    """Result envelope from a paper source search."""

    papers: list[PaperRef]
    source: PaperSource
    partial: bool = False
    warnings: list[str] = field(default_factory=list)


@dataclass
class _CircuitState:
    failures: int = 0
    opened_until: datetime | None = None


class CircuitBreaker:
    """Simple circuit breaker for upstream sources."""

    def __init__(self, failure_threshold: int = 5, cooldown_seconds: int = 60) -> None:
        self._failure_threshold = failure_threshold
        self._cooldown = timedelta(seconds=cooldown_seconds)
        self._state = _CircuitState()

    def record_success(self) -> None:
        self._state.failures = 0
        self._state.opened_until = None

    def record_failure(self) -> None:
        self._state.failures += 1
        if self._state.failures >= self._failure_threshold:
            self._state.opened_until = datetime.now(UTC) + self._cooldown

    def ensure_closed(self) -> None:
        if self._state.opened_until and datetime.now(UTC) < self._state.opened_until:
            raise SourceUnavailableError("Circuit breaker is open for source")
        if self._state.opened_until and datetime.now(UTC) >= self._state.opened_until:
            self._state.failures = 0
            self._state.opened_until = None


class PaperSourceConnector(ABC):
    """Base class for async paper source integrations."""

    source: PaperSource

    def __init__(self) -> None:
        self._breaker = CircuitBreaker()

    @abstractmethod
    async def search(self, query: str, *, limit: int = 20) -> SourceSearchResult:
        """Search papers by query string."""

    @abstractmethod
    async def fetch_metadata(self, paper_id: str) -> PaperRef:
        """Fetch metadata for a single paper."""

    async def safe_search(self, query: str, *, limit: int = 20) -> SourceSearchResult:
        """Search with circuit breaker protection."""
        self._breaker.ensure_closed()
        try:
            result = await self.search(query, limit=limit)
            self._breaker.record_success()
            return result
        except Exception:
            self._breaker.record_failure()
            raise
