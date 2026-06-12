"""Agent input/output schemas."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from app.models.enums import AgentName, DiscoveryStatus, JobStatus, PaperSource, Sufficiency
from app.schemas.common import PaperRef


class ControlState(BaseModel):
    """Pipeline control metadata."""

    current_agent: AgentName | None = None
    status: JobStatus = JobStatus.PENDING
    iteration: int = 0
    max_iterations: int = 2
    sufficiency: Sufficiency | None = None
    avg_confidence: float | None = None
    retries: dict[str, int] = Field(default_factory=dict)


class AgentError(BaseModel):
    """Structured agent error for state accumulation."""

    agent: AgentName
    error_type: str
    message: str
    retryable: bool = True
    ts: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AgentMessage(BaseModel):
    """Progress message emitted by agents."""

    agent: AgentName
    status: str
    message: str
    progress: float = 0.0
    ts: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DiscoveryPaperOutput(BaseModel):
    """Paper record in discovery agent JSON output."""

    paper_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str | None = None
    doi: str | None = None
    abstract: str = ""
    citation_count: int = 0
    source: PaperSource
    url: str | None = None
    relevance_score: float = Field(ge=0.0, le=1.0)
    relevance_reason: str | None = None

    def to_paper_ref(self) -> PaperRef:
        """Convert to canonical PaperRef."""
        return PaperRef(
            paper_id=self.paper_id,
            title=self.title,
            authors=self.authors,
            year=self.year,
            venue=self.venue,
            doi=self.doi,
            abstract=self.abstract,
            citation_count=self.citation_count,
            source=self.source,
            url=self.url,
            relevance_score=self.relevance_score,
            relevance_reason=self.relevance_reason,
        )


class DiscoveryOutput(BaseModel):
    """Structured discovery agent response."""

    agent: str = "discovery"
    status: DiscoveryStatus = DiscoveryStatus.OK
    query_plan: list[str] = Field(default_factory=list)
    papers: list[DiscoveryPaperOutput] = Field(default_factory=list)
    sources_used: list[PaperSource] = Field(default_factory=list)
    partial_sources: bool = False
    sufficiency: Sufficiency = Sufficiency.INSUFFICIENT
    discovery_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    suggested_followup_queries: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
