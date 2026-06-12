"""Sentence-transformer embedding service."""

from __future__ import annotations

import asyncio
from functools import lru_cache

import numpy as np

from app.core.discovery_config import get_discovery_config


@lru_cache
def _load_model(model_name: str):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


class Embedder:
    """Generate dense embeddings using Sentence Transformers."""

    def __init__(self, model_name: str | None = None) -> None:
        config = get_discovery_config()
        self._model_name = model_name or config.embedding_model

    @property
    def dimension(self) -> int:
        model = _load_model(self._model_name)
        return int(model.get_sentence_embedding_dimension())

    async def embed_texts(self, texts: list[str]) -> np.ndarray:
        """Embed a batch of texts without blocking the event loop."""
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)

        def _encode() -> np.ndarray:
            model = _load_model(self._model_name)
            vectors = model.encode(
                texts,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            return np.asarray(vectors, dtype=np.float32)

        return await asyncio.to_thread(_encode)

    async def embed_text(self, text: str) -> np.ndarray:
        """Embed a single text."""
        matrix = await self.embed_texts([text])
        return matrix[0]
