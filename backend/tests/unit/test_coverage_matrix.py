"""Unit tests for coverage matrix builder."""

from __future__ import annotations

from app.models.enums import Verdict
from app.schemas.intelligence import VerifiedClaim
from app.services.intelligence.coverage_matrix import build_coverage_matrix, papers_meta_from_state


def test_build_coverage_matrix_counts_topics() -> None:
    """Coverage matrix should aggregate claims by topic."""
    claims = [
        VerifiedClaim(
            claim_id="clm_1",
            paper_id="ss:paper-1",
            text="Claim A",
            topic="insulin_sensitivity",
            verdict=Verdict.SUPPORTED,
            confidence=0.9,
            reason="ok",
        ),
        VerifiedClaim(
            claim_id="clm_2",
            paper_id="ss:paper-2",
            text="Claim B",
            topic="insulin_sensitivity",
            verdict=Verdict.SUPPORTED,
            confidence=0.8,
            reason="ok",
        ),
    ]
    papers_meta = [
        {"paper_id": "ss:paper-1", "year": 2021},
        {"paper_id": "ss:paper-2", "year": 2020},
    ]

    matrix = build_coverage_matrix(claims, papers_meta)

    assert matrix["insulin_sensitivity|general"]["count"] == 2
    assert 2021 in matrix["insulin_sensitivity|general"]["years_present"]


def test_papers_meta_from_state() -> None:
    """papers_meta_from_state should normalize paper dicts."""
    papers = [{"paper_id": "ss:1", "year": 2022, "venue": "Nature", "source": "semantic_scholar"}]
    meta = papers_meta_from_state(papers)
    assert meta[0]["paper_id"] == "ss:1"
    assert meta[0]["methods"] == "semantic_scholar"
