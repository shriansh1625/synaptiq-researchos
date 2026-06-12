"""FAISS vector store with persistent metadata."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import faiss
import numpy as np

from app.core.discovery_config import get_discovery_config
from app.schemas.common import ChunkMetadata


class FaissVectorStore:
    """Persistent FAISS index with chunk metadata sidecar."""

    def __init__(self, index_dir: Path | None = None, dimension: int | None = None) -> None:
        config = get_discovery_config()
        self._index_dir = index_dir or config.faiss_index_dir
        self._index_dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self._index_dir / "index.faiss"
        self._meta_path = self._index_dir / "metadata.json"
        self._dimension = dimension
        self._index: faiss.IndexFlatIP | None = None
        self._metadata: list[ChunkMetadata] = []
        self._id_map: dict[str, int] = {}

    @property
    def dimension(self) -> int:
        if self._dimension is None:
            raise RuntimeError("FAISS index dimension is not initialized")
        return self._dimension

    async def initialize(self, dimension: int) -> None:
        """Create or load the FAISS index."""
        self._dimension = dimension

        def _init() -> None:
            if self._index_path.exists() and self._meta_path.exists():
                self._index = faiss.read_index(str(self._index_path))
                raw = json.loads(self._meta_path.read_text(encoding="utf-8"))
                self._metadata = [ChunkMetadata.model_validate(item) for item in raw]
                self._id_map = {
                    meta.chunk_id: idx for idx, meta in enumerate(self._metadata)
                }
            else:
                self._index = faiss.IndexFlatIP(dimension)
                self._metadata = []
                self._id_map = {}

        await asyncio.to_thread(_init)

    async def upsert(
        self,
        vectors: np.ndarray,
        metadata: list[ChunkMetadata],
    ) -> None:
        """Add vectors and metadata to the index."""
        if self._index is None:
            raise RuntimeError("FAISS index not initialized")
        if vectors.shape[0] != len(metadata):
            raise ValueError("Vectors and metadata length mismatch")

        def _add() -> None:
            assert self._index is not None
            new_vectors: list[np.ndarray] = []
            new_metadata: list[ChunkMetadata] = []
            for vector, meta in zip(vectors, metadata, strict=True):
                if meta.chunk_id in self._id_map:
                    continue
                new_vectors.append(vector.reshape(1, -1))
                new_metadata.append(meta)
            if not new_vectors:
                return
            batch = np.vstack(new_vectors).astype(np.float32)
            self._index.add(batch)
            start = len(self._metadata)
            self._metadata.extend(new_metadata)
            for offset, meta in enumerate(new_metadata):
                self._id_map[meta.chunk_id] = start + offset
            self._persist()

        await asyncio.to_thread(_add)

    async def similarity_search(
        self,
        query_vector: np.ndarray,
        *,
        top_k: int = 10,
    ) -> list[tuple[float, ChunkMetadata]]:
        """Return top-k similar chunks with scores."""
        if self._index is None:
            raise RuntimeError("FAISS index not initialized")
        if self._index.ntotal == 0:
            return []

        def _search() -> list[tuple[float, ChunkMetadata]]:
            assert self._index is not None
            query = query_vector.reshape(1, -1).astype(np.float32)
            scores, indices = self._index.search(query, min(top_k, self._index.ntotal))
            results: list[tuple[float, ChunkMetadata]] = []
            for score, idx in zip(scores[0], indices[0], strict=True):
                if idx < 0 or idx >= len(self._metadata):
                    continue
                results.append((float(score), self._metadata[idx]))
            return results

        return await asyncio.to_thread(_search)

    async def persist(self) -> None:
        """Persist index and metadata to disk."""
        await asyncio.to_thread(self._persist)

    def _persist(self) -> None:
        if self._index is None:
            return
        faiss.write_index(self._index, str(self._index_path))
        payload = [meta.model_dump(mode="json") for meta in self._metadata]
        self._meta_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
