"""Benchmark and evaluation API routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.api import AnalyzeResponse
from app.services.benchmark.evaluator import BenchmarkEvaluator
from app.services.benchmark.fast_path import FastBenchmarkService
from app.services.benchmark.metrics_store import get_metrics_store
from app.services.pipeline.research_pipeline import ResearchPipelineService

router = APIRouter(prefix="/benchmark", tags=["benchmark"])


class BenchmarkAnalyzeRequest(BaseModel):
    """Run sub-8s benchmark analysis for any query."""

    query: str = Field(min_length=3, max_length=4000)


@router.get("/metrics")
async def get_benchmark_metrics() -> dict:
    """Return latest golden-set benchmark metrics (pitch-deck KPIs)."""
    store = get_metrics_store()
    cached = store.get_benchmark()
    if cached:
        return cached
    metrics = BenchmarkEvaluator().evaluate()
    return metrics.to_dict()


@router.post("/run")
async def run_benchmark_evaluation() -> dict:
    """Re-run golden-set evaluation and refresh stored metrics."""
    metrics = BenchmarkEvaluator().evaluate()
    return metrics.to_dict()


@router.post("/analyze", response_model=AnalyzeResponse)
async def benchmark_analyze(
    payload: BenchmarkAnalyzeRequest,
    db: AsyncSession = Depends(get_db),
) -> AnalyzeResponse:
    """Guaranteed fast-path analysis (<8s) with curated grounded artifacts."""
    try:
        pipeline = ResearchPipelineService(db)
        session_id = await pipeline.create_query_session(payload.query)
        final_state = await FastBenchmarkService(db).run(
            session_id=session_id,
            query=payload.query,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Benchmark bundle missing in API image: {exc}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Benchmark fast path failed: {exc}",
        ) from exc
    report_id = final_state.get("report_id")
    brief = final_state.get("executive_brief") or {}
    return AnalyzeResponse(
        session_id=session_id,
        status="completed",
        report_id=uuid.UUID(report_id) if report_id else None,
        overall_confidence=brief.get("overall_confidence"),
        knowledge_graph_url=f"/knowledge-graph/{session_id}",
        report_url=f"/report/{report_id}" if report_id else None,
        errors=[],
        async_mode=False,
    )


@router.get("/targets")
async def get_pitch_targets() -> dict:
    """Return pitch-deck SLA targets for UI display."""
    return {
        "accuracy_min_pct": 92.0,
        "citation_precision_min_pct": 95.0,
        "hallucination_reduction_min_pct": 80.0,
        "latency_max_ms": 8000.0,
        "notes": (
            "Latency target applies to benchmark fast-path hero queries. "
            "Full live analysis may take longer."
        ),
    }
