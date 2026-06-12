"""Pydantic schemas for the executive brief agent."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.enums import BriefStatus


class BriefTextBlock(BaseModel):
    """Grounded text block with mandatory citations."""

    text: str
    citations: list[str] = Field(default_factory=list)


class BriefGapBlock(BaseModel):
    """Research gap reference block."""

    text: str
    gap_id: str


class BriefReport(BaseModel):
    """Structured executive research brief."""

    report_id: str
    title: str
    executive_summary: str
    key_findings: list[BriefTextBlock] = Field(default_factory=list)
    comparative_insights: list[BriefTextBlock] = Field(default_factory=list)
    consensus: list[BriefTextBlock] = Field(default_factory=list)
    contradictions: list[BriefTextBlock] = Field(default_factory=list)
    research_gaps: list[BriefGapBlock] = Field(default_factory=list)
    future_opportunities: list[BriefTextBlock] = Field(default_factory=list)
    recommendations: list[BriefTextBlock] = Field(default_factory=list)
    limitations: str = ""


class CitationIntegrity(BaseModel):
    """Self-verification result for brief citations."""

    checked: bool = True
    all_citations_valid: bool = True
    uncited_removed: int = 0


class ExplainabilityCitation(BaseModel):
    """Explainability metadata for a cited source."""

    citation_id: str
    claim_id: str | None = None
    gap_id: str | None = None
    paper_id: str | None = None
    title: str = ""
    text_span: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    source: str = ""
    verdict: str | None = None
    reasoning: str = ""


class ExecutiveBriefOutput(BaseModel):
    """Executive brief agent structured output."""

    agent: str = "brief"
    status: BriefStatus = BriefStatus.OK
    report: BriefReport
    overall_confidence: float = Field(ge=0.0, le=1.0)
    citations: list[ExplainabilityCitation] = Field(default_factory=list)
    citation_integrity: CitationIntegrity = Field(default_factory=CitationIntegrity)
    warnings: list[str] = Field(default_factory=list)
