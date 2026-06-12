"""Unified paper retrieval, deduplication, and ranking service."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence

from app.core.discovery_config import get_discovery_config
from app.core.exceptions import SourceUnavailableError
from app.models.enums import PaperSource
from app.schemas.common import PaperRef
from app.services.sources.arxiv import ArxivSource
from app.services.sources.base_source import PaperSourceConnector, SourceSearchResult
from app.services.sources.semantic_scholar import SemanticScholarSource


def _normalize_title(title: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()
    return re.sub(r"\s+", " ", cleaned)


def _title_fingerprint(title: str) -> str:
    return hashlib.sha1(_normalize_title(title).encode("utf-8")).hexdigest()


class PaperRetrievalService:
    """Merge, deduplicate, and rank papers from multiple sources."""

    def __init__(
        self,
        sources: Sequence[PaperSourceConnector] | None = None,
    ) -> None:
        self._sources: list[PaperSourceConnector] = list(
            sources
            or [
                SemanticScholarSource(),
                ArxivSource(),
            ]
        )
        self._config = get_discovery_config()

    async def close(self) -> None:
        for source in self._sources:
            close = getattr(source, "close", None)
            if callable(close):
                await close()

    async def search(
        self,
        query: str,
        *,
        limit: int | None = None,
        known_paper_ids: set[str] | None = None,
    ) -> tuple[list[PaperRef], dict[str, object]]:
        """Search all sources and return normalized, deduplicated papers."""
        max_results = limit or self._config.max_papers
        known = known_paper_ids or set()
        merged: list[PaperRef] = []
        warnings: list[str] = []
        sources_used: list[PaperSource] = []
        partial = False

        per_source_limit = max(5, max_results // max(len(self._sources), 1))

        for source in self._sources:
            try:
                result: SourceSearchResult = await source.safe_search(
                    query,
                    limit=per_source_limit,
                )
                merged.extend(result.papers)
                sources_used.append(result.source)
                warnings.extend(result.warnings)
                partial = partial or result.partial
            except SourceUnavailableError as exc:
                partial = True
                warnings.append(f"{source.source.value} unavailable: {exc}")
            except Exception as exc:  # noqa: BLE001
                partial = True
                warnings.append(f"{source.source.value} failed: {exc}")

        deduped = self.deduplicate(merged, known_paper_ids=known)
        ranked = self.rank(deduped, query)
        return ranked[:max_results], {
            "sources_used": sources_used,
            "partial_sources": partial,
            "warnings": warnings,
        }

    def deduplicate(
        self,
        papers: Sequence[PaperRef],
        *,
        known_paper_ids: set[str] | None = None,
    ) -> list[PaperRef]:
        """Deduplicate by paper_id, DOI, or near-identical title."""
        known = known_paper_ids or set()
        by_id: dict[str, PaperRef] = {}
        doi_index: dict[str, str] = {}
        title_index: dict[str, str] = {}

        for paper in papers:
            if paper.paper_id in known:
                continue

            if paper.paper_id in by_id:
                self._keep_better(by_id, paper)
                continue

            if paper.doi:
                doi_key = paper.doi.lower()
                existing_id = doi_index.get(doi_key)
                if existing_id:
                    self._keep_better(by_id, paper, existing_id=existing_id)
                    continue

            title_key = _title_fingerprint(paper.title)
            existing_id = title_index.get(title_key)
            if existing_id:
                self._keep_better(by_id, paper, existing_id=existing_id)
                continue

            by_id[paper.paper_id] = paper
            if paper.doi:
                doi_index[paper.doi.lower()] = paper.paper_id
            title_index[title_key] = paper.paper_id

        return list(by_id.values())

    def rank(self, papers: Sequence[PaperRef], query: str) -> list[PaperRef]:
        """Rank papers using lexical overlap and citation count."""
        query_terms = set(_normalize_title(query).split())

        def score(paper: PaperRef) -> float:
            title_terms = set(_normalize_title(paper.title).split())
            abstract_terms = set(_normalize_title(paper.abstract).split())
            overlap = len(query_terms & title_terms) * 2 + len(query_terms & abstract_terms)
            lexical = overlap / max(len(query_terms), 1)
            citation_boost = min(paper.citation_count / 1000.0, 0.2)
            return lexical + citation_boost + paper.relevance_score

        return sorted(papers, key=score, reverse=True)

    @staticmethod
    def _keep_better(
        by_id: dict[str, PaperRef],
        candidate: PaperRef,
        *,
        existing_id: str | None = None,
    ) -> None:
        current_id = existing_id or candidate.paper_id
        current = by_id.get(current_id)
        if current is None:
            by_id[candidate.paper_id] = candidate
            return
        if len(candidate.abstract) > len(current.abstract):
            del by_id[current.paper_id]
            by_id[candidate.paper_id] = candidate
        elif candidate.citation_count > current.citation_count:
            del by_id[current.paper_id]
            by_id[candidate.paper_id] = candidate
