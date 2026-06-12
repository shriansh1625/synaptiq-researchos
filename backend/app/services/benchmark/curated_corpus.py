"""Curated research corpus for resilient discovery when external APIs fail."""

from __future__ import annotations

import copy
import json
import re
from typing import Any

from app.models.enums import PaperSource
from app.resources.benchmark import HERO_BUNDLE_PATH
from app.schemas.common import PaperRef


def normalize_query(query: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", query.lower()).strip()


def pick_topic_key(query: str) -> str:
    normalized = normalize_query(query)
    if any(k in normalized for k in ("multi agent", "multi-agent", "orchestration", "langgraph")):
        return "multi_agent"
    if any(k in normalized for k in ("rag", "hallucination", "retrieval augmented")):
        return "rag_hallucination"
    return "default"


def load_hero_bundle(query: str = "") -> dict[str, Any]:
    if not HERO_BUNDLE_PATH.is_file():
        raise FileNotFoundError(f"Hero bundle not found: {HERO_BUNDLE_PATH}")
    bundle = json.loads(HERO_BUNDLE_PATH.read_text(encoding="utf-8"))
    topic_key = pick_topic_key(query)
    template = (bundle.get("topic_templates") or {}).get(topic_key)
    if template:
        merged = copy.deepcopy(bundle)
        for key in ("papers", "verified_claims", "contradictions", "research_gaps", "executive_brief"):
            if key in template:
                merged[key] = copy.deepcopy(template[key])
        return merged
    return bundle


def _parse_source(raw: str) -> PaperSource:
    normalized = raw.lower().replace("-", "_")
    for candidate in (normalized, "arxiv", "semantic_scholar"):
        try:
            return PaperSource(candidate)
        except ValueError:
            continue
    return PaperSource.ARXIV


def load_curated_papers(query: str) -> list[PaperRef]:
    """Return topic-matched curated papers from the shipped hero bundle."""
    try:
        bundle = load_hero_bundle(query)
    except FileNotFoundError:
        return []

    papers: list[PaperRef] = []
    for raw in bundle.get("papers") or []:
        if not raw.get("paper_id"):
            continue
        papers.append(
            PaperRef(
                paper_id=str(raw["paper_id"]),
                title=str(raw.get("title", "")),
                authors=list(raw.get("authors") or []),
                year=raw.get("year"),
                venue=raw.get("venue"),
                doi=raw.get("doi"),
                abstract=str(raw.get("abstract", "")),
                citation_count=int(raw.get("citation_count") or 0),
                source=_parse_source(str(raw.get("source", "arxiv"))),
                url=raw.get("url"),
                relevance_score=float(raw.get("relevance_score") or 0.85),
                relevance_reason="Curated corpus fallback for resilient analysis.",
            )
        )
    return papers
