"""Tests for FAISS vector store."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from app.schemas.common import ChunkMetadata
from app.models.enums import PaperSource
from app.vector_store.faiss_store import FaissVectorStore


@pytest.mark.asyncio
async def test_faiss_store_persists_and_searches(tmp_path: Path) -> None:
    """FAISS store should persist vectors and return top matches."""
    store = FaissVectorStore(index_dir=tmp_path, dimension=4)
    await store.initialize(4)

    metadata = [
        ChunkMetadata(
            chunk_id="chunk:1",
            paper_id="ss:1",
            title="Insulin sensitivity study",
            source=PaperSource.SEMANTIC_SCHOLAR,
        ),
        ChunkMetadata(
            chunk_id="chunk:2",
            paper_id="ss:2",
            title="Unrelated segmentation paper",
            source=PaperSource.SEMANTIC_SCHOLAR,
        ),
    ]
    vectors = np.array(
        [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
        ],
        dtype=np.float32,
    )
    await store.upsert(vectors, metadata)

    hits = await store.similarity_search(
        np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32),
        top_k=1,
    )
    assert len(hits) == 1
    assert hits[0][1].chunk_id == "chunk:1"
