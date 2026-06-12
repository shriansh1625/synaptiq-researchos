"""Discovery-layer configuration (Sprint 3) without modifying core settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class DiscoveryConfig:
    """Runtime configuration for discovery, embeddings, and retrieval."""

    embedding_model: str
    embedding_provider: str
    faiss_index_dir: Path
    chunk_size: int
    chunk_overlap: int
    default_top_k: int
    min_papers: int
    max_papers: int
    source_max_attempts: int
    semantic_scholar_base_url: str
    arxiv_base_url: str
    gemini_model: str
    gemini_temperature: float


@lru_cache
def get_discovery_config() -> DiscoveryConfig:
    """Load discovery configuration from environment variables."""
    backend_dir = Path(__file__).resolve().parents[2]
    default_faiss = backend_dir / "data" / "faiss"
    return DiscoveryConfig(
        embedding_model=os.getenv(
            "EMBEDDING_MODEL",
            "sentence-transformers/all-MiniLM-L6-v2",
        ),
        embedding_provider=os.getenv("EMBEDDING_PROVIDER", "local"),
        faiss_index_dir=Path(os.getenv("FAISS_INDEX_DIR", str(default_faiss))),
        chunk_size=int(os.getenv("CHUNK_SIZE", "512")),
        chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "64")),
        default_top_k=int(os.getenv("RETRIEVAL_TOP_K", "10")),
        min_papers=int(os.getenv("DISCOVERY_MIN_PAPERS", "8")),
        max_papers=int(os.getenv("DISCOVERY_MAX_PAPERS", "40")),
        source_max_attempts=int(os.getenv("SOURCE_MAX_ATTEMPTS", "3")),
        semantic_scholar_base_url=os.getenv(
            "SEMANTIC_SCHOLAR_BASE_URL",
            "https://api.semanticscholar.org/graph/v1",
        ),
        arxiv_base_url=os.getenv(
            "ARXIV_BASE_URL",
            "https://export.arxiv.org/api/query",
        ),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        gemini_temperature=float(os.getenv("GEMINI_TEMPERATURE", "0.2")),
    )
