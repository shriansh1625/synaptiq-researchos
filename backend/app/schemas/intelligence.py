"""Pydantic schemas for Sprint 4 intelligence agents."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.enums import (
    GapType,
    IntelligenceStatus,
    RelationType,
    Verdict,
    VerificationStage,
)


class ExtractedClaim(BaseModel):
    """Atomic claim extracted from a paper."""

    claim_id: str
    paper_id: str
    text: str
    topic: str


class VerificationExtractOutput(BaseModel):
    """Stage A verification output."""

    agent: str = "verification"
    stage: VerificationStage = VerificationStage.EXTRACT
    paper_id: str
    claims: list[ExtractedClaim] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class EvidenceSpanRef(BaseModel):
    """Reference to a supporting evidence span."""

    span_id: str
    chunk_id: str
    score: float = Field(ge=0.0, le=1.0)


class VerificationVerifyOutput(BaseModel):
    """Stage B verification output."""

    agent: str = "verification"
    stage: VerificationStage = VerificationStage.VERIFY
    status: IntelligenceStatus = IntelligenceStatus.OK
    claim_id: str
    paper_id: str
    text: str
    verdict: Verdict
    confidence: float = Field(ge=0.0, le=1.0)
    supporting_spans: list[EvidenceSpanRef] = Field(default_factory=list)
    reason: str
    needs_review: bool = False
    topic: str
    warnings: list[str] = Field(default_factory=list)


class VerifiedClaim(BaseModel):
    """Verified claim stored in ResearchState."""

    claim_id: str
    paper_id: str
    text: str
    topic: str
    verdict: Verdict
    confidence: float = Field(ge=0.0, le=1.0)
    supporting_spans: list[EvidenceSpanRef] = Field(default_factory=list)
    reason: str
    needs_review: bool = False


class ClaimRelation(BaseModel):
    """Relationship between two verified claims."""

    relation_id: str
    relation_type: RelationType
    claim_a: str
    claim_b: str
    dimension: str
    rationale: str
    confidence: float = Field(ge=0.0, le=1.0)
    needs_review: bool = False


class ClaimCluster(BaseModel):
    """Topic cluster with inter-claim relations."""

    cluster_id: str
    topic: str
    member_claim_ids: list[str] = Field(default_factory=list)
    cluster_confidence: float = Field(ge=0.0, le=1.0)
    relations: list[ClaimRelation] = Field(default_factory=list)


class ComparativeOutput(BaseModel):
    """Comparative analysis agent output."""

    agent: str = "comparative"
    status: IntelligenceStatus = IntelligenceStatus.OK
    clusters: list[ClaimCluster] = Field(default_factory=list)
    contradictions_count: int = 0
    warnings: list[str] = Field(default_factory=list)


class ResearchGapItem(BaseModel):
    """Detected research gap."""

    gap_id: str
    gap_type: GapType
    topic: str
    description: str
    evidence: list[str] = Field(default_factory=list)
    related_claims: list[str] = Field(default_factory=list)
    impact_score: float = Field(ge=0.0, le=1.0)
    actionability_note: str


class GapDetectionOutput(BaseModel):
    """Research gap detection agent output."""

    agent: str = "gap"
    status: IntelligenceStatus = IntelligenceStatus.OK
    gaps: list[ResearchGapItem] = Field(default_factory=list)
    analysis_confidence: float = Field(ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)


class ContradictionRecord(BaseModel):
    """Normalized contradiction extracted from comparative analysis."""

    relation_id: str
    claim_a: str
    claim_b: str
    topic: str
    rationale: str
    confidence: float = Field(ge=0.0, le=1.0)
