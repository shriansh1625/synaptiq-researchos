"""Tests for arXiv source."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.services.sources.arxiv import ArxivSource, build_arxiv_search_queries, build_arxiv_search_query

SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2104.00111</id>
    <title>Sample arXiv Paper</title>
    <summary>An arXiv abstract.</summary>
    <published>2021-04-01T00:00:00Z</published>
    <author><name>Ada Lovelace</name></author>
  </entry>
</feed>
"""


@pytest.mark.asyncio
async def test_arxiv_search_parses_feed() -> None:
    """arXiv search should parse Atom XML entries."""
    source = ArxivSource()
    source._fetch_xml = AsyncMock(return_value=SAMPLE_XML)  # type: ignore[method-assign]

    result = await source.search("sample query", limit=5)

    assert len(result.papers) == 1
    assert result.papers[0].paper_id == "arxiv:2104.00111"
    assert result.papers[0].authors == ["Ada Lovelace"]


def test_build_arxiv_search_query_strips_question_words() -> None:
    """arXiv query builder should keep topical keywords only."""
    query = build_arxiv_search_query(
        "Does intermittent fasting improve insulin sensitivity?"
    )
    assert query == "all:intermittent+all:fasting"


def test_build_arxiv_search_queries_includes_fallbacks() -> None:
    """arXiv should generate broader fallback queries."""
    queries = build_arxiv_search_queries(
        "Does intermittent fasting improve insulin sensitivity?"
    )
    assert queries[0] == "all:intermittent+all:fasting"
    assert any(" OR " in item for item in queries)
