"""API request and response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Create a new research session from a user query."""

    query: str = Field(min_length=3, max_length=4000)
    filters: dict[str, Any] = Field(default_factory=dict)
    options: dict[str, Any] = Field(default_factory=dict)


class QueryResponse(BaseModel):
    """Response after creating a research session."""

    session_id: uuid.UUID
    query: str
    status: str


class AnalyzeRequest(BaseModel):
    """Trigger full pipeline analysis."""

    session_id: uuid.UUID | None = None
    query: str | None = Field(default=None, min_length=3, max_length=4000)
    filters: dict[str, Any] = Field(default_factory=dict)
    options: dict[str, Any] = Field(default_factory=dict)


class AnalyzeResponse(BaseModel):
    """Response after analysis completes or starts."""

    session_id: uuid.UUID
    status: str
    report_id: uuid.UUID | None = None
    overall_confidence: float | None = None
    knowledge_graph_url: str | None = None
    report_url: str | None = None
    errors: list[dict[str, Any]] = Field(default_factory=list)
    async_mode: bool = False


class AnalyzeStartResponse(BaseModel):
    """Immediate response when analysis is started in the background."""

    session_id: uuid.UUID
    status: str = "running"
    poll_url: str
    message: str = "Analysis started. Poll session endpoint for progress."


class SessionResponse(BaseModel):
    """Research session status and summary."""

    session_id: uuid.UUID
    query: str
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    paper_count: int = 0
    verified_claim_count: int = 0
    contradiction_count: int = 0
    research_gap_count: int = 0
    report_id: uuid.UUID | None = None
    overall_confidence: float | None = None
    agent_logs: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)


class ReportResponse(BaseModel):
    """Executive report metadata."""

    report_id: uuid.UUID
    session_id: uuid.UUID
    summary: str
    recommendations: dict[str, Any]
    citations: list[Any]
    created_at: datetime | None = None
    pdf_available: bool = False


class KnowledgeGraphResponse(BaseModel):
    """Knowledge graph export for a session."""

    session_id: uuid.UUID
    summary: dict[str, Any]
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    communities: list[dict[str, Any]]
    html_available: bool = False
