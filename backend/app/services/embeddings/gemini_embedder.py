"""Gemini API embeddings for low-memory deployments (e.g. Render free tier)."""

from __future__ import annotations

import asyncio

import google.generativeai as genai
import numpy as np

from config.settings import get_settings

_GEMINI_EMBEDDING_MODEL = "models/text-embedding-004"
_GEMINI_EMBEDDING_DIMENSION = 768


class GeminiEmbedder:
    """Generate embeddings via the Gemini API instead of loading local models."""

    @property
    def dimension(self) -> int:
        return _GEMINI_EMBEDDING_DIMENSION

    async def embed_texts(self, texts: list[str]) -> np.ndarray:
        """Embed a batch of texts without blocking the event loop."""
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)

        return await asyncio.to_thread(self._embed_texts_sync, texts)

    async def embed_text(self, text: str) -> np.ndarray:
        """Embed a single text."""
        matrix = await self.embed_texts([text])
        return matrix[0]

    def _embed_texts_sync(self, texts: list[str]) -> np.ndarray:
        settings = get_settings()
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required when EMBEDDING_PROVIDER=gemini")

        genai.configure(api_key=settings.gemini_api_key)
        vectors: list[np.ndarray] = []
        for text in texts:
            result = genai.embed_content(
                model=_GEMINI_EMBEDDING_MODEL,
                content=text,
                task_type="retrieval_document",
            )
            embedding = np.asarray(result["embedding"], dtype=np.float32)
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            vectors.append(embedding)
        return np.vstack(vectors)
