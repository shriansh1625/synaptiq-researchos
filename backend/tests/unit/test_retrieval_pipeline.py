"""Tests for retrieval pipeline."""

from __future__ import annotations

import numpy as np
import pytest

from app.models.enums import PaperSource
from app.schemas.common import ChunkMetadata
from app.services.retrieval.retrieval_pipeline import RetrievalPipeline
from app.vector_store.faiss_store import FaissVectorStore
from tests.fixtures.fake_embedder import FakeEmbedder


@pytest.mark.asyncio
async def test_retrieval_pipeline_returns_chunks_and_citations(tmp_path) -> None:
    """Retrieval pipeline should return ranked chunks and citations."""
    embedder = FakeEmbedder()
    store = FaissVectorStore(index_dir=tmp_path, dimension=embedder.dimension)
    await store.initialize(embedder.dimension)

    metadata = ChunkMetadata(
        chunk_id="chunk:1",
        paper_id="ss:1",
        title="Intermittent fasting insulin sensitivity",
        source=PaperSource.SEMANTIC_SCHOLAR,
        doi="10.1000/test",
        url="https://example.com",
    )
    vector = await embedder.embed_text(metadata.title)
    await store.upsert(np.asarray([vector]), [metadata])

    pipeline = RetrievalPipeline(embedder=embedder, vector_store=store)
    chunks, citations, scores = await pipeline.retrieve(
        "intermittent fasting insulin",
        top_k=1,
    )

    assert len(chunks) == 1
    assert len(citations) == 1
    assert scores["ss:1"] > 0
