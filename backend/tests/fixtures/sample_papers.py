"""Sample paper fixtures for discovery tests."""

from __future__ import annotations

from app.models.enums import PaperSource
from app.schemas.common import PaperRef

SAMPLE_PAPERS = [
    PaperRef(
        paper_id="ss:paper-1",
        title="Intermittent Fasting and Insulin Sensitivity",
        authors=["A. Rao"],
        year=2021,
        venue="Cell Metab",
        doi="10.1016/test.1",
        abstract="RCT showing improved insulin sensitivity under intermittent fasting.",
        citation_count=120,
        source=PaperSource.SEMANTIC_SCHOLAR,
        url="https://example.com/1",
    ),
    PaperRef(
        paper_id="arxiv:2104.00111",
        title="Time-Restricted Eating and Glycemic Control",
        authors=["K. Lin"],
        year=2020,
        venue="arXiv",
        doi=None,
        abstract="Study of glucose metabolism with time-restricted eating.",
        citation_count=45,
        source=PaperSource.ARXIV,
        url="https://arxiv.org/abs/2104.00111",
    ),
    PaperRef(
        paper_id="ss:paper-2",
        title="Intermittent Fasting and Insulin Sensitivity",
        authors=["A. Rao"],
        year=2021,
        venue="Cell Metab",
        doi="10.1016/test.1",
        abstract="Duplicate title for dedup testing.",
        citation_count=100,
        source=PaperSource.SEMANTIC_SCHOLAR,
        url="https://example.com/dup",
    ),
]
