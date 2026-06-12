"""Tests for text chunking."""

from __future__ import annotations

from app.services.chunking.chunker import TextChunker
from tests.fixtures.sample_papers import SAMPLE_PAPERS


def test_chunker_preserves_metadata() -> None:
    """Chunker should preserve paper metadata."""
    chunker = TextChunker(chunk_size=80, chunk_overlap=10)
    chunks = chunker.chunk_paper(SAMPLE_PAPERS[0])

    assert chunks
    text, metadata = chunks[0]
    assert SAMPLE_PAPERS[0].title in text
    assert metadata.paper_id == SAMPLE_PAPERS[0].paper_id
    assert metadata.chunk_index == 0
