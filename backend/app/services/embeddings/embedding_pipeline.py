"""End-to-end embedding pipeline for discovered papers."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from app.schemas.common import ChunkMetadata, PaperRef
from app.services.chunking.chunker import TextChunker
from app.services.embeddings.embedder import Embedder
from app.vector_store.faiss_store import FaissVectorStore


class EmbeddingPipeline:
    """Chunk papers, generate embeddings, and upsert into FAISS."""

    def __init__(
        self,
        embedder: Embedder | None = None,
        chunker: TextChunker | None = None,
        vector_store: FaissVectorStore | None = None,
    ) -> None:
        self._embedder = embedder or Embedder()
        self._chunker = chunker or TextChunker()
        self._vector_store = vector_store or FaissVectorStore()

    @property
    def vector_store(self) -> FaissVectorStore:
        return self._vector_store

    async def initialize(self) -> None:
        await self._vector_store.initialize(self._embedder.dimension)

    async def index_papers(self, papers: Sequence[PaperRef]) -> list[str]:
        """Chunk and embed papers, returning indexed chunk IDs."""
        if not papers:
            return []

        chunk_pairs: list[tuple[str, ChunkMetadata]] = []
        for paper in papers:
            chunk_pairs.extend(self._chunker.chunk_paper(paper))

        if not chunk_pairs:
            return []

        texts = [text for text, _ in chunk_pairs]
        metadata = [meta for _, meta in chunk_pairs]
        vectors = await self._embedder.embed_texts(texts)
        await self._vector_store.upsert(np.asarray(vectors), metadata)
        await self._vector_store.persist()
        return [meta.chunk_id for meta in metadata]
