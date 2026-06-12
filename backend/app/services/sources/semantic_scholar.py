"""Semantic Scholar paper source connector."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from app.core.discovery_config import get_discovery_config
from app.core.exceptions import RateLimitError, UpstreamError
from app.core.retry import async_retry
from app.models.enums import PaperSource
from app.schemas.common import PaperRef
from app.services.sources.base_source import PaperSourceConnector, SourceSearchResult
from config.settings import get_settings

_SEMANTIC_SCHOLAR_MIN_INTERVAL_SECONDS = 1.05
_SEMANTIC_SCHOLAR_RATE_LIMIT_LOCK = asyncio.Lock()
_SEMANTIC_SCHOLAR_LAST_REQUEST_AT = 0.0


class SemanticScholarSource(PaperSourceConnector):
    """Async Semantic Scholar API client."""

    source = PaperSource.SEMANTIC_SCHOLAR

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        super().__init__()
        self._config = get_discovery_config()
        self._settings = get_settings()
        self._client = client
        self._owns_client = client is None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self._settings.semantic_scholar_api_key:
            headers["x-api-key"] = self._settings.semantic_scholar_api_key
        return headers

    async def close(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _request(self, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        client = await self._get_client()
        await _wait_for_rate_limit()
        response = await client.request(method, url, headers=self._headers(), **kwargs)
        if response.status_code == 429:
            raise RateLimitError("Semantic Scholar rate limit exceeded")
        if response.status_code >= 500:
            raise UpstreamError(f"Semantic Scholar server error: {response.status_code}")
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise UpstreamError("Semantic Scholar returned unexpected payload")
        return payload

    async def _request_with_retry(self, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        async def _call() -> dict[str, Any]:
            return await self._request(method, url, **kwargs)

        return await async_retry(
            _call,
            max_attempts=self._config.source_max_attempts,
            retry_on=(UpstreamError,),
        )

    @staticmethod
    def _normalize_paper(raw: dict[str, Any]) -> PaperRef | None:
        paper_id = raw.get("paperId") or raw.get("paper_id")
        title = raw.get("title")
        if not paper_id or not title:
            return None
        authors = [
            author.get("name", "")
            for author in raw.get("authors", [])
            if isinstance(author, dict) and author.get("name")
        ]
        year = raw.get("year")
        external_ids = raw.get("externalIds") or {}
        doi = external_ids.get("DOI") if isinstance(external_ids, dict) else None
        return PaperRef(
            paper_id=f"ss:{paper_id}",
            title=title,
            authors=authors,
            year=year,
            venue=raw.get("venue"),
            doi=doi,
            abstract=raw.get("abstract") or "",
            citation_count=int(raw.get("citationCount") or 0),
            source=PaperSource.SEMANTIC_SCHOLAR,
            url=raw.get("url"),
        )

    async def search(self, query: str, *, limit: int = 20) -> SourceSearchResult:
        try:
            payload = await self._request(
                "GET",
                f"{self._config.semantic_scholar_base_url}/paper/search",
                params={
                    "query": query,
                    "limit": limit,
                    "fields": "paperId,title,authors,year,venue,abstract,citationCount,url,externalIds",
                },
            )
        except RateLimitError:
            return SourceSearchResult(
                papers=[],
                source=self.source,
                partial=True,
                warnings=["Semantic Scholar rate limit exceeded; continuing with other sources."],
            )
        papers = [
            paper
            for item in payload.get("data", [])
            if isinstance(item, dict)
            for paper in [self._normalize_paper(item)]
            if paper is not None
        ]
        return SourceSearchResult(papers=papers, source=self.source)

    async def fetch_metadata(self, paper_id: str) -> PaperRef:
        normalized_id = paper_id.removeprefix("ss:")
        url = f"{self._config.semantic_scholar_base_url}/paper/{normalized_id}"
        payload = await self._request_with_retry(
            "GET",
            url,
            params={
                "fields": "paperId,title,authors,year,venue,abstract,citationCount,url,externalIds",
            },
        )
        paper = self._normalize_paper(payload)
        if paper is None:
            raise UpstreamError(f"Semantic Scholar paper not found: {paper_id}")
        return paper


async def _wait_for_rate_limit() -> None:
    """Keep Semantic Scholar requests under the 1 request/second API-key limit."""
    global _SEMANTIC_SCHOLAR_LAST_REQUEST_AT
    async with _SEMANTIC_SCHOLAR_RATE_LIMIT_LOCK:
        now = time.monotonic()
        elapsed = now - _SEMANTIC_SCHOLAR_LAST_REQUEST_AT
        wait_for = _SEMANTIC_SCHOLAR_MIN_INTERVAL_SECONDS - elapsed
        if wait_for > 0:
            await asyncio.sleep(wait_for)
        _SEMANTIC_SCHOLAR_LAST_REQUEST_AT = time.monotonic()
