"""End-to-end research pipeline orchestration."""

from __future__ import annotations

import time
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings
from app.database.models.research_session import ResearchSessionStatus
from app.database.repositories.agent_log_repository import AgentLogRepository
from app.database.repositories.research_session_repository import ResearchSessionRepository
from app.graphs.research_graph import build_research_graph
from app.graphs.state import ResearchState
from app.services.benchmark.fast_path import FastBenchmarkService, is_hero_query
from app.services.benchmark.metrics_store import get_metrics_store


class ResearchPipelineService:
    """Run the full research intelligence pipeline for a session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._session_repo = ResearchSessionRepository(session)
        self._agent_log_repo = AgentLogRepository(session)

    async def create_query_session(self, query: str) -> uuid.UUID:
        user = await self._session_repo.get_or_create_demo_user()
        research_session = await self._session_repo.create(user_id=user.id, query=query)
        await self._session.commit()
        return research_session.id

    async def run_analysis(
        self,
        *,
        session_id: uuid.UUID,
        query: str,
        filters: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        await self._session_repo.update_status(session_id, ResearchSessionStatus.RUNNING)
        await self._session.commit()

        settings = get_settings()
        opts = dict(options or {})
        filters = dict(filters or {})
        if opts.get("force_full") is True:
            opts["turbo"] = False
            filters.setdefault("max_papers", int(opts.get("max_papers", 15)))
            opts.setdefault("max_claims_per_paper", 4)
        else:
            opts.setdefault("turbo", True)
            filters.setdefault("max_papers", int(opts.get("max_papers", 10)))
            opts.setdefault("max_claims_per_paper", 3)

        use_fast = (
            opts.get("fast") is True
            or opts.get("mode") in {"benchmark", "fast", "demo"}
            or (
                settings.benchmark_fast_enabled
                and opts.get("force_full") is not True
                and is_hero_query(query)
            )
        )
        if use_fast:
            started = time.perf_counter()
            final_state = await FastBenchmarkService(self._session).run(
                session_id=session_id,
                query=query,
            )
            get_metrics_store().record_analyze_latency(
                (time.perf_counter() - started) * 1000,
                fast_path=True,
            )
            return final_state

        graph = build_research_graph()
        started = time.perf_counter()
        initial_state: ResearchState = {
            "session_id": str(session_id),
            "query": query,
            "filters": filters,
            "options": opts,
            "papers": [],
            "retrieved_chunks": [],
            "citations": [],
            "confidence_scores": {},
            "verified_claims": [],
            "research_gaps": [],
            "contradictions": [],
            "errors": [],
            "messages": [],
        }
        config = {
            "configurable": {
                "thread_id": str(session_id),
                "db_session": self._session,
            }
        }

        try:
            final_state = await graph.ainvoke(initial_state, config=config)
            has_report = bool(final_state.get("report_id"))
            has_papers = bool(final_state.get("papers"))
            if not has_papers or not has_report:
                status = ResearchSessionStatus.FAILED
            else:
                status = ResearchSessionStatus.COMPLETED
            await self._session_repo.update_status(session_id, status)
            await self._session.commit()
            get_metrics_store().record_analyze_latency(
                (time.perf_counter() - started) * 1000,
                fast_path=False,
            )
            return final_state
        except Exception:
            await self._session.rollback()
            await self._session_repo.update_status(session_id, ResearchSessionStatus.FAILED)
            await self._session.commit()
            raise

    async def get_agent_logs(self, session_id: uuid.UUID) -> list[dict[str, Any]]:
        from sqlalchemy import select

        from app.database.models.agent_log import AgentLog

        stmt = (
            select(AgentLog)
            .where(AgentLog.session_id == session_id)
            .order_by(AgentLog.timestamp.asc())
        )
        rows = (await self._session.scalars(stmt)).all()
        return [
            {
                "agent_name": row.agent_name,
                "latency": row.latency,
                "confidence_score": row.confidence_score,
                "status": row.status,
                "input_data": row.input_data,
                "output_data": row.output_data,
                "timestamp": row.timestamp.isoformat() if row.timestamp else None,
            }
            for row in rows
        ]
