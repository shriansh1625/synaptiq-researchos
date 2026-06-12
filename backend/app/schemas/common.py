"""Shared Pydantic models for the research pipeline."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.enums import PaperSource


class PaperRef(BaseModel):
    """Normalized paper metadata from external sources."""

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
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    relevance_reason: str | None = None


class ChunkMetadata(BaseModel):
    """Metadata preserved for each embedded chunk."""

    chunk_id: str
    paper_id: str
    title: str
    source: PaperSource
    doi: str | None = None
    url: str | None = None
    section: str = "abstract"
    chunk_index: int = 0
    char_start: int = 0
    char_end: int = 0


class RetrievedChunk(BaseModel):
    """A retrieved text chunk with citation context."""

    chunk_id: str
    paper_id: str
    text: str
    score: float = Field(ge=0.0, le=1.0)
    metadata: ChunkMetadata
    citation_key: str


class Citation(BaseModel):
    """Citation reference tied to a retrieved chunk."""

    citation_id: str
    paper_id: str
    chunk_id: str
    title: str
    text_span: str
    source: PaperSource
    doi: str | None = None
    url: str | None = None


class Span(BaseModel):
    """Evidence span used by downstream verification."""

    span_id: str
    chunk_id: str
    paper_id: str
    text: str
    score: float = Field(ge=0.0, le=1.0)
    sent_start: int = 0
    sent_end: int = 0
