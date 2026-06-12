"""Paper persistence repository using existing Sprint 2 ORM models."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.paper import EmbeddingStatus, Paper
from app.schemas.common import PaperRef


class PaperRepository:
    """Persist discovered papers without modifying the ORM schema."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_paper(self, paper: PaperRef) -> Paper:
        """Insert or update a paper by DOI or normalized title."""
        existing = await self._find_existing(paper)
        publication_date = date(paper.year, 1, 1) if paper.year else None

        if existing is None:
            entity = Paper(
                title=paper.title,
                abstract=paper.abstract or " ",
                authors=paper.authors,
                publication_date=publication_date,
                source=paper.source.value,
                url=paper.url or f"synaptiq://paper/{paper.paper_id}",
                doi=paper.doi,
                embedding_status=EmbeddingStatus.PENDING,
            )
            self._session.add(entity)
            await self._session.flush()
            return entity

        existing.title = paper.title
        existing.abstract = paper.abstract or existing.abstract
        existing.authors = paper.authors
        existing.publication_date = publication_date or existing.publication_date
        existing.source = paper.source.value
        existing.url = paper.url or existing.url
        existing.doi = paper.doi or existing.doi
        await self._session.flush()
        return existing

    async def upsert_many(self, papers: list[PaperRef]) -> list[Paper]:
        """Persist multiple papers."""
        return [await self.upsert_paper(paper) for paper in papers]

    async def _find_existing(self, paper: PaperRef) -> Paper | None:
        if paper.doi:
            result = await self._session.execute(
                select(Paper).where(Paper.doi == paper.doi)
            )
            found = result.scalar_one_or_none()
            if found is not None:
                return found

        result = await self._session.execute(
            select(Paper).where(Paper.title == paper.title)
        )
        return result.scalar_one_or_none()
