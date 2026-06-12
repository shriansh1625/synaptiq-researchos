"""Semantic and hybrid retrieval pipeline."""

from __future__ import annotations

import re

from app.core.discovery_config import get_discovery_config
from app.schemas.common import Citation, RetrievedChunk
from app.services.chunking.chunker import normalize_whitespace
from app.services.embeddings.embedder import Embedder
from app.vector_store.faiss_store import FaissVectorStore


class RetrievalPipeline:
    """Retrieve relevant chunks and preserve citation metadata."""

    def __init__(
        self,
        embedder: Embedder | None = None,
        vector_store: FaissVectorStore | None = None,
    ) -> None:
        self._embedder = embedder or Embedder()
        self._vector_store = vector_store or FaissVectorStore()
        self._config = get_discovery_config()

    @property
    def vector_store(self) -> FaissVectorStore:
        return self._vector_store

    async def initialize(self) -> None:
        await self._vector_store.initialize(self._embedder.dimension)

    async def retrieve(
        self,
        query: str,
        *,
        top_k: int | None = None,
    ) -> tuple[list[RetrievedChunk], list[Citation], dict[str, float]]:
        """Run semantic retrieval with lexical hybrid re-ranking."""
        k = top_k or self._config.default_top_k
        query_vector = await self._embedder.embed_text(query)
        faiss_hits = await self._vector_store.similarity_search(query_vector, top_k=k * 2)

        query_terms = set(normalize_whitespace(query).lower().split())
        scored: list[RetrievedChunk] = []
        confidence_scores: dict[str, float] = {}

        for semantic_score, metadata in faiss_hits:
            text = metadata.title
            lexical = self._lexical_score(query_terms, text)
            hybrid_score = min(1.0, (semantic_score * 0.7) + (lexical * 0.3))
            chunk = RetrievedChunk(
                chunk_id=metadata.chunk_id,
                paper_id=metadata.paper_id,
                text=text,
                score=hybrid_score,
                metadata=metadata,
                citation_key=metadata.chunk_id,
            )
            scored.append(chunk)
            current = confidence_scores.get(metadata.paper_id, 0.0)
            confidence_scores[metadata.paper_id] = max(current, hybrid_score)

        scored.sort(key=lambda item: item.score, reverse=True)
        top_chunks = scored[:k]
        citations = [
            Citation(
                citation_id=f"cite:{chunk.chunk_id}",
                paper_id=chunk.paper_id,
                chunk_id=chunk.chunk_id,
                title=chunk.metadata.title,
                text_span=chunk.text[:240],
                source=chunk.metadata.source,
                doi=chunk.metadata.doi,
                url=chunk.metadata.url,
            )
            for chunk in top_chunks
        ]
        return top_chunks, citations, confidence_scores

    @staticmethod
    def _lexical_score(query_terms: set[str], text: str) -> float:
        if not query_terms:
            return 0.0
        doc_terms = set(re.findall(r"[a-z0-9]+", text.lower()))
        overlap = len(query_terms & doc_terms)
        return overlap / len(query_terms)
