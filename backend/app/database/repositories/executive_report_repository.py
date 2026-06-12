"""Repository for executive report persistence."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.executive_report import ExecutiveReport


class ExecutiveReportRepository:
    """CRUD operations for executive reports."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        report_id: uuid.UUID,
        session_id: uuid.UUID,
        summary: str,
        recommendations: dict[str, Any],
        citations: list[Any],
    ) -> ExecutiveReport:
        report = ExecutiveReport(
            id=report_id,
            session_id=session_id,
            summary=summary,
            recommendations=recommendations,
            citations=citations,
        )
        self._session.add(report)
        await self._session.flush()
        return report

    async def get_by_id(self, report_id: uuid.UUID) -> ExecutiveReport | None:
        return await self._session.get(ExecutiveReport, report_id)

    async def get_latest_for_session(self, session_id: uuid.UUID) -> ExecutiveReport | None:
        stmt = (
            select(ExecutiveReport)
            .where(ExecutiveReport.session_id == session_id)
            .order_by(ExecutiveReport.created_at.desc())
            .limit(1)
        )
        return await self._session.scalar(stmt)
