"""Text chunking with metadata preservation."""

from __future__ import annotations

import hashlib
import re

from app.core.discovery_config import get_discovery_config
from app.schemas.common import ChunkMetadata, PaperRef


class TextChunker:
    """Split paper text into overlapping chunks."""

    def __init__(self, chunk_size: int | None = None, chunk_overlap: int | None = None) -> None:
        config = get_discovery_config()
        self._chunk_size = chunk_size or config.chunk_size
        self._chunk_overlap = chunk_overlap or config.chunk_overlap

    def chunk_paper(self, paper: PaperRef) -> list[tuple[str, ChunkMetadata]]:
        """Chunk a paper abstract (and title prefix) into retrievable segments."""
        body = f"{paper.title}\n\n{paper.abstract}".strip()
        if not body:
            return []

        chunks: list[tuple[str, ChunkMetadata]] = []
        start = 0
        index = 0
        while start < len(body):
            end = min(len(body), start + self._chunk_size)
            if end < len(body):
                boundary = body.rfind(" ", start, end)
                if boundary > start + self._chunk_size // 2:
                    end = boundary
            text = body[start:end].strip()
            if text:
                chunk_id = self._chunk_id(paper.paper_id, index, text)
                metadata = ChunkMetadata(
                    chunk_id=chunk_id,
                    paper_id=paper.paper_id,
                    title=paper.title,
                    source=paper.source,
                    doi=paper.doi,
                    url=paper.url,
                    section="abstract",
                    chunk_index=index,
                    char_start=start,
                    char_end=end,
                )
                chunks.append((text, metadata))
                index += 1
            if end >= len(body):
                break
            start = max(end - self._chunk_overlap, start + 1)
        return chunks

    @staticmethod
    def _chunk_id(paper_id: str, index: int, text: str) -> str:
        digest = hashlib.sha1(f"{paper_id}:{index}:{text[:64]}".encode("utf-8")).hexdigest()[:12]
        return f"chunk:{paper_id}:{index}:{digest}"


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace for lexical scoring."""
    return re.sub(r"\s+", " ", text).strip()
