"""Research intelligence API routes."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.runtime_paths import get_graphs_dir, get_reports_dir
from app.database.repositories.executive_report_repository import ExecutiveReportRepository
from app.database.repositories.research_session_repository import ResearchSessionRepository
from app.database.session import get_db
from app.schemas.api import (
    AnalyzeRequest,
    AnalyzeResponse,
    AnalyzeStartResponse,
    KnowledgeGraphResponse,
    QueryRequest,
    QueryResponse,
    ReportResponse,
    SessionResponse,
)
from app.graphs.research_graph import build_research_graph
from app.services.pipeline.background_runner import spawn_analysis_background
from app.services.pipeline.research_pipeline import ResearchPipelineService

router = APIRouter(tags=["research"])


@router.post("/query", response_model=QueryResponse, status_code=status.HTTP_201_CREATED)
async def create_query(
    payload: QueryRequest,
    db: AsyncSession = Depends(get_db),
) -> QueryResponse:
    """Create a research session from a user query."""
    pipeline = ResearchPipelineService(db)
    session_id = await pipeline.create_query_session(payload.query)
    session_repo = ResearchSessionRepository(db)
    session = await session_repo.get_by_id(session_id)
    if session is None:
        raise HTTPException(status_code=500, detail="Failed to create research session")
    return QueryResponse(
        session_id=session_id,
        query=session.query,
        status=session.status,
    )


async def _resolve_analyze_target(
    payload: AnalyzeRequest,
    pipeline: ResearchPipelineService,
    session_repo: ResearchSessionRepository,
) -> tuple[uuid.UUID, str]:
    if payload.session_id is not None:
        session = await session_repo.get_by_id(payload.session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        return session.id, session.query
    if payload.query:
        session_id = await pipeline.create_query_session(payload.query)
        return session_id, payload.query
    raise HTTPException(
        status_code=400,
        detail="Either session_id or query must be provided",
    )


@router.post("/analyze/start", response_model=AnalyzeStartResponse)
async def start_analyze_research(
    payload: AnalyzeRequest,
    db: AsyncSession = Depends(get_db),
) -> AnalyzeStartResponse:
    """Start analysis in background; poll GET /session/{id} for completion."""
    session_repo = ResearchSessionRepository(db)
    pipeline = ResearchPipelineService(db)
    session_id, query = await _resolve_analyze_target(payload, pipeline, session_repo)

    opts = dict(payload.options or {})
    opts.setdefault("turbo", True)
    filters = dict(payload.filters or {})
    filters.setdefault("max_papers", 10)

    spawn_analysis_background(
        session_id=session_id,
        query=query,
        filters=filters,
        options=opts,
    )
    return AnalyzeStartResponse(
        session_id=session_id,
        status="running",
        poll_url=f"/session/{session_id}",
    )


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_research(
    payload: AnalyzeRequest,
    db: AsyncSession = Depends(get_db),
) -> AnalyzeResponse:
    """Run the research pipeline (blocking). Use /analyze/start for long runs."""
    session_repo = ResearchSessionRepository(db)
    pipeline = ResearchPipelineService(db)
    session_id, query = await _resolve_analyze_target(payload, pipeline, session_repo)

    opts = dict(payload.options or {})
    if opts.get("mode") in {"benchmark", "fast", "demo"} or opts.get("fast"):
        final_state = await pipeline.run_analysis(
            session_id=session_id,
            query=query,
            filters=payload.filters,
            options=opts,
        )
    else:
        opts.setdefault("turbo", True)
        filters = dict(payload.filters or {})
        filters.setdefault("max_papers", 10)
        final_state = await pipeline.run_analysis(
            session_id=session_id,
            query=query,
            filters=filters,
            options=opts,
        )

    report_id = final_state.get("report_id") or None
    brief = final_state.get("executive_brief") or {}
    session = await session_repo.get_by_id(session_id)
    return AnalyzeResponse(
        session_id=session_id,
        status=session.status if session else "completed",
        report_id=uuid.UUID(report_id) if report_id else None,
        overall_confidence=brief.get("overall_confidence"),
        knowledge_graph_url=f"/knowledge-graph/{session_id}",
        report_url=f"/report/{report_id}" if report_id else None,
        errors=final_state.get("errors", []),
    )


@router.get("/session/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """Return session status and pipeline summary."""
    session_repo = ResearchSessionRepository(db)
    session = await session_repo.get_by_id(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    pipeline = ResearchPipelineService(db)
    agent_logs = await pipeline.get_agent_logs(session_id)
    report_repo = ExecutiveReportRepository(db)
    report = await report_repo.get_latest_for_session(session_id)

    graph = build_research_graph()
    config = {"configurable": {"thread_id": str(session_id)}}
    try:
        checkpoint_state = await graph.aget_state(config)
        values = checkpoint_state.values or {}
    except Exception:
        values = {}

    paper_count = len(values.get("papers", []))
    verified_claim_count = len(values.get("verified_claims", []))
    contradiction_count = len(values.get("contradictions", []))
    research_gap_count = len(values.get("research_gaps", []))
    overall_confidence = (values.get("executive_brief") or {}).get("overall_confidence")

    if paper_count == 0 or verified_claim_count == 0:
        for log in agent_logs:
            output = log.get("output_data") or {}
            if log.get("agent_name") == "discovery" and paper_count == 0:
                paper_count = len(output.get("papers") or [])
            if log.get("agent_name") == "verification" and verified_claim_count == 0:
                verified_claim_count = int(
                    output.get("verified_claim_count")
                    or len(output.get("verified_claims") or [])
                )
            if log.get("agent_name") == "comparative" and contradiction_count == 0:
                contradiction_count = len(output.get("contradictions") or [])
            if log.get("agent_name") == "gap" and research_gap_count == 0:
                research_gap_count = len(output.get("research_gaps") or [])

    if report is not None:
        recommendations = report.recommendations if isinstance(report.recommendations, dict) else {}
        if overall_confidence is None:
            overall_confidence = recommendations.get("overall_confidence")
        if contradiction_count == 0:
            contradiction_count = len(recommendations.get("contradictions") or [])
        if research_gap_count == 0:
            research_gap_count = len(recommendations.get("research_gaps") or [])

    return SessionResponse(
        session_id=session_id,
        query=session.query,
        status=session.status,
        created_at=session.created_at,
        updated_at=session.updated_at,
        paper_count=paper_count,
        verified_claim_count=verified_claim_count,
        contradiction_count=contradiction_count,
        research_gap_count=research_gap_count,
        report_id=report.id if report else None,
        overall_confidence=overall_confidence,
        agent_logs=agent_logs,
        errors=values.get("errors", []),
    )


@router.get("/report/{report_id}/json", response_model=ReportResponse)
async def get_report_json(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ReportResponse:
    """Return structured executive report metadata for the frontend brief viewer."""
    repo = ExecutiveReportRepository(db)
    report = await repo.get_by_id(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    pdf_path = Path((report.recommendations or {}).get("pdf_path", ""))
    if not pdf_path.is_file():
        fallback = get_reports_dir() / f"{report_id}.pdf"
        pdf_path = fallback if fallback.is_file() else pdf_path

    return ReportResponse(
        report_id=report.id,
        session_id=report.session_id,
        summary=report.summary,
        recommendations=report.recommendations,
        citations=report.citations,
        created_at=report.created_at,
        pdf_available=pdf_path.is_file(),
    )


@router.get("/report/{report_id}", response_model=None)
async def get_report(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Download or inspect an executive report."""
    repo = ExecutiveReportRepository(db)
    report = await repo.get_by_id(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    pdf_path = Path((report.recommendations or {}).get("pdf_path", ""))
    if not pdf_path.is_file():
        fallback = get_reports_dir() / f"{report_id}.pdf"
        pdf_path = fallback if fallback.is_file() else pdf_path

    if pdf_path.is_file():
        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            filename=f"synaptiq_report_{report_id}.pdf",
        )

    return ReportResponse(
        report_id=report.id,
        session_id=report.session_id,
        summary=report.summary,
        recommendations=report.recommendations,
        citations=report.citations,
        created_at=report.created_at,
        pdf_available=False,
    )


@router.get("/knowledge-graph/{session_id}", response_model=None)
async def get_knowledge_graph(session_id: uuid.UUID):
    """Return interactive knowledge graph HTML or structured graph data."""
    html_path = get_graphs_dir() / f"{session_id}.html"
    if html_path.is_file():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))

    raise HTTPException(
        status_code=404,
        detail="Knowledge graph not found for this session",
    )
