"""Embedding service facade (local Sentence-Transformers or Gemini API)."""

from __future__ import annotations

import os
from typing import Protocol

import numpy as np

from app.core.discovery_config import get_discovery_config
from app.services.embeddings.gemini_embedder import GeminiEmbedder
from app.services.embeddings.local_embedder import LocalEmbedder


class EmbeddingBackend(Protocol):
    """Protocol implemented by embedding backends."""

    @property
    def dimension(self) -> int: ...

    async def embed_texts(self, texts: list[str]) -> np.ndarray: ...

    async def embed_text(self, text: str) -> np.ndarray: ...


def create_embedder(model_name: str | None = None) -> EmbeddingBackend:
    """Return the configured embedding backend."""
    provider = os.getenv("EMBEDDING_PROVIDER", get_discovery_config().embedding_provider).strip().lower()
    if provider == "gemini":
        return GeminiEmbedder()
    return LocalEmbedder(model_name=model_name)


class Embedder:
    """Generate dense embeddings using the configured backend."""

    def __init__(self, model_name: str | None = None, backend: EmbeddingBackend | None = None) -> None:
        self._backend = backend or create_embedder(model_name)

    @property
    def dimension(self) -> int:
        return self._backend.dimension

    async def embed_texts(self, texts: list[str]) -> np.ndarray:
        """Embed a batch of texts without blocking the event loop."""
        return await self._backend.embed_texts(texts)

    async def embed_text(self, text: str) -> np.ndarray:
        """Embed a single text."""
        return await self._backend.embed_text(text)
