"""Fake embedder for fast offline tests."""

from __future__ import annotations

import hashlib

import numpy as np


class FakeEmbedder:
    """Deterministic low-dimensional embedder."""

    dimension = 16

    async def embed_texts(self, texts: list[str]) -> np.ndarray:
        vectors = []
        for text in texts:
            seed = int(hashlib.sha1(text.encode("utf-8")).hexdigest()[:8], 16)
            rng = np.random.default_rng(seed)
            vector = rng.random(self.dimension).astype(np.float32)
            vector /= np.linalg.norm(vector) + 1e-9
            vectors.append(vector)
        return np.vstack(vectors) if vectors else np.empty((0, self.dimension), dtype=np.float32)

    async def embed_text(self, text: str) -> np.ndarray:
        matrix = await self.embed_texts([text])
        return matrix[0]
