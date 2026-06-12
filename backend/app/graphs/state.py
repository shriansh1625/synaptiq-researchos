"""LangGraph research state definition and reducers."""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from app.schemas.agent_io import ControlState


def merge_papers(
    existing: list[dict[str, Any]] | None,
    new: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Merge paper lists, deduplicating by paper_id and keeping max relevance."""
    merged: dict[str, dict[str, Any]] = {}
    for paper in (existing or []) + (new or []):
        paper_id = paper["paper_id"]
        current = merged.get(paper_id)
        if current is None or paper.get("relevance_score", 0) >= current.get(
            "relevance_score",
            0,
        ):
            merged[paper_id] = paper
    return list(merged.values())


def merge_confidence_scores(
    existing: dict[str, float] | None,
    new: dict[str, float] | None,
) -> dict[str, float]:
    """Merge confidence score maps keeping the maximum per key."""
    result = dict(existing or {})
    for key, score in (new or {}).items():
        result[key] = max(result.get(key, 0.0), score)
    return result


def merge_claims(
    existing: list[dict[str, Any]] | None,
    new: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Merge verified claims by claim_id, keeping the highest confidence."""
    merged: dict[str, dict[str, Any]] = {}
    for claim in (existing or []) + (new or []):
        claim_id = claim["claim_id"]
        current = merged.get(claim_id)
        if current is None or claim.get("confidence", 0) >= current.get("confidence", 0):
            merged[claim_id] = claim
    return list(merged.values())


class ResearchState(TypedDict, total=False):
    """Shared LangGraph state for the research pipeline."""

    # Input
    session_id: str
    query_id: str
    user_id: str
    query: str
    question: str
    filters: dict[str, Any]
    options: dict[str, Any]

    # Control / plan
    plan: dict[str, Any]
    control: ControlState | dict[str, Any]

    # Discovery outputs
    papers: Annotated[list[dict[str, Any]], merge_papers]
    retrieved_chunks: Annotated[list[dict[str, Any]], operator.add]
    citations: Annotated[list[dict[str, Any]], operator.add]
    confidence_scores: Annotated[dict[str, float], merge_confidence_scores]
    chunks_indexed: Annotated[list[str], operator.add]

    # Intelligence outputs
    verified_claims: Annotated[list[dict[str, Any]], merge_claims]
    comparisons: dict[str, Any]
    research_gaps: Annotated[list[dict[str, Any]], operator.add]
    contradictions: Annotated[list[dict[str, Any]], operator.add]

    # Sprint 5 outputs
    executive_brief: dict[str, Any]
    knowledge_graph: dict[str, Any]
    report_id: str
    explainability: dict[str, Any]

    # Trace
    messages: Annotated[list[dict[str, Any]], operator.add]
    errors: Annotated[list[dict[str, Any]], operator.add]
    trace_id: str
