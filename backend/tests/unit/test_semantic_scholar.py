"""Tests for Semantic Scholar source."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.sources.semantic_scholar import SemanticScholarSource


@pytest.mark.asyncio
async def test_semantic_scholar_search_parses_results() -> None:
    """Semantic Scholar search should normalize paper payloads."""
    source = SemanticScholarSource(client=MagicMock())
    source._request = AsyncMock(  # type: ignore[method-assign]
        return_value={
            "data": [
                {
                    "paperId": "abc123",
                    "title": "Test Paper",
                    "authors": [{"name": "Jane Doe"}],
                    "year": 2024,
                    "abstract": "An abstract.",
                    "citationCount": 10,
                    "url": "https://example.com",
                    "externalIds": {"DOI": "10.1000/test"},
                }
            ]
        }
    )

    result = await source.search("test query", limit=5)

    assert len(result.papers) == 1
    assert result.papers[0].paper_id == "ss:abc123"
    assert result.papers[0].doi == "10.1000/test"
