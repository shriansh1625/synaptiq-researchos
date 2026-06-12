"""Coverage matrix builder for gap detection."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.schemas.intelligence import VerifiedClaim


def build_coverage_matrix(
    claims: list[VerifiedClaim],
    papers_meta: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Build topic x dimension coverage cells from verified claims."""
    cells: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"count": 0, "years_present": [], "methods": []}
    )

    paper_years = {
        paper.get("paper_id"): paper.get("year")
        for paper in papers_meta
        if paper.get("paper_id")
    }

    for claim in claims:
        topic = claim.topic or "general"
        dimension = "general"
        key = f"{topic}|{dimension}"
        cell = cells[key]
        cell["count"] += 1
        year = paper_years.get(claim.paper_id)
        if year and year not in cell["years_present"]:
            cell["years_present"].append(year)

    return dict(cells)


def papers_meta_from_state(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert paper state dicts to gap-agent metadata."""
    return [
        {
            "paper_id": paper.get("paper_id"),
            "year": paper.get("year"),
            "venue": paper.get("venue"),
            "methods": paper.get("source"),
        }
        for paper in papers
    ]
