"""Tests for curated corpus fallback."""

from __future__ import annotations

from app.services.benchmark.curated_corpus import load_curated_papers, pick_topic_key


def test_pick_topic_key_multi_agent() -> None:
    key = pick_topic_key(
        "What are the main approaches to multi-agent LLM orchestration for research?"
    )
    assert key == "multi_agent"


def test_load_curated_papers_for_multi_agent_query() -> None:
    papers = load_curated_papers(
        "What are the main approaches to multi-agent LLM orchestration for research?"
    )
    assert len(papers) >= 2
    assert all(paper.paper_id for paper in papers)
    assert all(paper.abstract for paper in papers)
