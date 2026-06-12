"""arXiv paper source connector."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

import httpx

from app.core.discovery_config import get_discovery_config
from app.core.exceptions import RateLimitError, UpstreamError
from app.core.retry import async_retry
from app.models.enums import PaperSource
from app.schemas.common import PaperRef
from app.services.sources.base_source import PaperSourceConnector, SourceSearchResult

_ATOM_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
_ARXIV_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "of",
        "to",
        "in",
        "on",
        "for",
        "with",
        "does",
        "do",
        "is",
        "are",
        "was",
        "were",
        "can",
        "how",
        "what",
        "why",
        "when",
        "which",
        "who",
        "improve",
        "affect",
        "impact",
        "help",
    }
)


def build_arxiv_search_query(query: str) -> str:
    """Convert a natural-language question into an arXiv API search expression."""
    terms = _extract_search_terms(query)
    if len(terms) >= 2:
        return f"all:{terms[0]}+all:{terms[1]}"
    if terms:
        return f"all:{terms[0]}"
    return f"all:{query.strip()[:120]}"


def build_arxiv_search_queries(query: str) -> list[str]:
    """Build progressively broader arXiv queries until results are found."""
    terms = _extract_search_terms(query)
    if not terms:
        return [f"all:{query.strip()[:120]}"]

    queries: list[str] = []
    if len(terms) >= 2:
        queries.append(f"all:{terms[0]}+all:{terms[1]}")
        queries.append(f"ti:{terms[0]}+{terms[1]}")
    if len(terms) >= 3:
        queries.append(
            " AND ".join(f"all:{term}" for term in terms[:3]),
        )
    queries.append(" OR ".join(f"all:{term}" for term in terms[:4]))
    queries.append(f"all:{terms[0]}")
    # Preserve order while deduplicating.
    seen: set[str] = set()
    ordered: list[str] = []
    for item in queries:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def _extract_search_terms(query: str) -> list[str]:
    terms = [
        token
        for token in re.findall(r"[a-z0-9]+", query.lower())
        if len(token) > 2 and token not in _ARXIV_STOP_WORDS
    ]
    if not terms:
        terms = [token for token in re.findall(r"[a-z0-9]+", query.lower()) if len(token) > 2]
    return terms


class ArxivSource(PaperSourceConnector):
    """Async arXiv API client."""

    source = PaperSource.ARXIV

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        super().__init__()
        self._config = get_discovery_config()
        self._client = client
        self._owns_client = client is None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        return self._client

    async def close(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _fetch_xml(self, params: dict[str, str | int]) -> str:
        client = await self._get_client()

        async def _call() -> str:
            response = await client.get(self._config.arxiv_base_url, params=params)
            if response.status_code >= 500:
                raise UpstreamError(f"arXiv server error: {response.status_code}")
            response.raise_for_status()
            return response.text

        return await async_retry(_call, max_attempts=self._config.source_max_attempts)

    @staticmethod
    def _parse_year(published: str | None) -> int | None:
        if not published:
            return None
        match = re.match(r"(\d{4})", published)
        return int(match.group(1)) if match else None

    @classmethod
    def _parse_entry(cls, entry: ET.Element) -> PaperRef | None:
        raw_id = entry.findtext("atom:id", default="", namespaces=_ATOM_NS)
        arxiv_id_match = re.search(r"arxiv\.org/abs/([^/]+)$", raw_id)
        if not arxiv_id_match:
            return None
        arxiv_id = arxiv_id_match.group(1)
        title = (entry.findtext("atom:title", default="", namespaces=_ATOM_NS) or "").strip()
        abstract = (entry.findtext("atom:summary", default="", namespaces=_ATOM_NS) or "").strip()
        authors = [
            author.findtext("atom:name", default="", namespaces=_ATOM_NS).strip()
            for author in entry.findall("atom:author", _ATOM_NS)
            if author.findtext("atom:name", default="", namespaces=_ATOM_NS)
        ]
        published = entry.findtext("atom:published", default=None, namespaces=_ATOM_NS)
        return PaperRef(
            paper_id=f"arxiv:{arxiv_id}",
            title=title,
            authors=authors,
            year=cls._parse_year(published),
            venue="arXiv",
            doi=entry.findtext("arxiv:doi", default=None, namespaces=_ATOM_NS),
            abstract=abstract,
            citation_count=0,
            source=PaperSource.ARXIV,
            url=f"https://arxiv.org/abs/{arxiv_id}",
        )

    def _parse_feed(self, xml_text: str) -> list[PaperRef]:
        root = ET.fromstring(xml_text)
        papers: list[PaperRef] = []
        for entry in root.findall("atom:entry", _ATOM_NS):
            paper = self._parse_entry(entry)
            if paper is not None:
                papers.append(paper)
        return papers

    async def search(self, query: str, *, limit: int = 20) -> SourceSearchResult:
        warnings: list[str] = []
        for search_query in build_arxiv_search_queries(query):
            xml_text = await self._fetch_xml(
                {
                    "search_query": search_query,
                    "start": 0,
                    "max_results": limit,
                }
            )
            papers = self._parse_feed(xml_text)
            if papers:
                if search_query != build_arxiv_search_queries(query)[0]:
                    warnings.append(f"arXiv broadened query to: {search_query}")
                return SourceSearchResult(
                    papers=papers[:limit],
                    source=self.source,
                    warnings=warnings,
                )
        return SourceSearchResult(papers=[], source=self.source, partial=True, warnings=warnings)

    async def fetch_metadata(self, paper_id: str) -> PaperRef:
        arxiv_id = paper_id.removeprefix("arxiv:")
        xml_text = await self._fetch_xml(
            {
                "id_list": arxiv_id,
                "max_results": 1,
            }
        )
        papers = self._parse_feed(xml_text)
        if not papers:
            raise UpstreamError(f"arXiv paper not found: {paper_id}")
        return papers[0]
