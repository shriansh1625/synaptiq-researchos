"""Tests for Gemini API embeddings."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.services.embeddings.embedder import create_embedder
from app.services.embeddings.gemini_embedder import GeminiEmbedder


def test_create_embedder_uses_gemini_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """EMBEDDING_PROVIDER=gemini should avoid loading local models."""
    monkeypatch.setenv("EMBEDDING_PROVIDER", "gemini")
    embedder = create_embedder()
    assert isinstance(embedder, GeminiEmbedder)


@pytest.mark.asyncio
async def test_gemini_embedder_normalizes_vectors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Gemini embeddings should be L2-normalized for FAISS inner product search."""
    from config.settings import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/synaptiq")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

    fake_embedding = [3.0, 4.0]
    with patch("app.services.embeddings.gemini_embedder.genai.embed_content") as mock_embed:
        mock_embed.return_value = {"embedding": fake_embedding}
        embedder = GeminiEmbedder()
        vector = await embedder.embed_text("retrieval test")

    assert vector.shape == (2,)
    assert pytest.approx(float(np.linalg.norm(vector)), rel=1e-5) == 1.0
