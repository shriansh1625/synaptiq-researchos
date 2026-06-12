"""Tests for LangGraph research state reducers."""

from __future__ import annotations

from app.graphs.state import merge_claims, merge_confidence_scores, merge_papers


def test_merge_papers_keeps_highest_relevance() -> None:
    """merge_papers should deduplicate and keep max relevance_score."""
    existing = [{"paper_id": "ss:1", "title": "A", "relevance_score": 0.5}]
    new = [{"paper_id": "ss:1", "title": "A", "relevance_score": 0.9}]
    merged = merge_papers(existing, new)
    assert len(merged) == 1
    assert merged[0]["relevance_score"] == 0.9


def test_merge_confidence_scores_keeps_maximum() -> None:
    """merge_confidence_scores should keep the highest score per paper."""
    merged = merge_confidence_scores({"ss:1": 0.4}, {"ss:1": 0.8, "ss:2": 0.6})
    assert merged["ss:1"] == 0.8
    assert merged["ss:2"] == 0.6


def test_merge_claims_keeps_highest_confidence() -> None:
    """merge_claims should deduplicate by claim_id and keep max confidence."""
    existing = [{"claim_id": "clm_1", "confidence": 0.5, "text": "A"}]
    new = [{"claim_id": "clm_1", "confidence": 0.9, "text": "A"}]
    merged = merge_claims(existing, new)
    assert len(merged) == 1
    assert merged[0]["confidence"] == 0.9
