"""Tests for unified paper retrieval."""

from __future__ import annotations

import pytest

from app.models.enums import PaperSource
from app.schemas.common import PaperRef
from app.services.sources.base_source import SourceSearchResult
from app.services.sources.paper_retrieval import PaperRetrievalService
from tests.fixtures.sample_papers import SAMPLE_PAPERS


class FakeSource:
    source = PaperSource.SEMANTIC_SCHOLAR

    def __init__(self, papers: list[PaperRef]) -> None:
        self._papers = papers

    async def safe_search(self, query: str, *, limit: int = 20) -> SourceSearchResult:
        return SourceSearchResult(papers=self._papers[:limit], source=self.source)


@pytest.mark.asyncio
async def test_paper_retrieval_deduplicates_and_ranks() -> None:
    """Unified retrieval should deduplicate and rank papers."""
    service = PaperRetrievalService(sources=[FakeSource(SAMPLE_PAPERS)])
    papers, meta = await service.search("intermittent fasting insulin")

    assert len(papers) == 2
    assert meta["partial_sources"] is False
    assert papers[0].title.startswith("Intermittent")


def test_paper_retrieval_deduplicate_by_doi() -> None:
    """Deduplication should collapse DOI duplicates."""
    service = PaperRetrievalService(sources=[])
    deduped = service.deduplicate(SAMPLE_PAPERS)
    assert len(deduped) == 2
