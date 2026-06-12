"""Shared domain enumerations."""

from __future__ import annotations

from enum import StrEnum


class PaperSource(StrEnum):
    """External paper provider."""

    SEMANTIC_SCHOLAR = "semantic_scholar"
    ARXIV = "arxiv"


class AgentName(StrEnum):
    """Registered pipeline agents."""

    DISCOVERY = "discovery"
    VERIFICATION = "verification"
    COMPARATIVE = "comparative"
    GAP = "gap"
    BRIEF = "brief"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    REPORT = "report"


class JobStatus(StrEnum):
    """Pipeline execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DEGRADED = "degraded"


class DiscoveryStatus(StrEnum):
    """Discovery agent result status."""

    OK = "ok"
    NO_CANDIDATES = "no_candidates"
    PARTIAL = "partial"


class Sufficiency(StrEnum):
    """Discovery sufficiency verdict."""

    SUFFICIENT = "sufficient"
    INSUFFICIENT = "insufficient"


class Verdict(StrEnum):
    """Claim verification verdict."""

    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    CONTRADICTED = "CONTRADICTED"


class VerificationStage(StrEnum):
    """Verification prompt stage."""

    EXTRACT = "extract"
    VERIFY = "verify"


class RelationType(StrEnum):
    """Comparative relation between claims."""

    AGREES = "AGREES"
    CONTRADICTS = "CONTRADICTS"
    EXTENDS = "EXTENDS"
    METHOD_DIFFERS = "METHOD_DIFFERS"
    INCONCLUSIVE = "INCONCLUSIVE"


class GapType(StrEnum):
    """Research gap classification."""

    UNDERSTUDIED = "UNDERSTUDIED"
    UNRESOLVED_CONTRADICTION = "UNRESOLVED_CONTRADICTION"
    TEMPORAL = "TEMPORAL"
    METHODOLOGICAL = "METHODOLOGICAL"


class IntelligenceStatus(StrEnum):
    """Generic intelligence agent status."""

    OK = "ok"
    INSUFFICIENT_CLAIMS = "insufficient_claims"
    NO_COMPARABLE_PAIRS = "no_comparable_pairs"
    NO_MAJOR_GAPS = "no_major_gaps"
    INSUFFICIENT_CONTEXT = "insufficient_context"
    NO_EVIDENCE = "no_evidence"
    CLAIM_ERROR = "claim_error"


class BriefStatus(StrEnum):
    """Executive brief agent status."""

    OK = "ok"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class KGNodeType(StrEnum):
    """Knowledge graph node types."""

    PAPER = "paper"
    AUTHOR = "author"
    TOPIC = "topic"
    METHOD = "method"
    DATASET = "dataset"
    CLAIM = "claim"


class KGEdgeType(StrEnum):
    """Knowledge graph edge types."""

    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    REFERENCES = "references"
    USES = "uses"
    BELONGS_TO = "belongs_to"
