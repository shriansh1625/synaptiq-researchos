"""Production observability endpoints (metrics, traces, status)."""

from __future__ import annotations

from fastapi import APIRouter, Response

from app.services.benchmark.metrics_store import get_metrics_store
from config.settings import get_settings

router = APIRouter(prefix="/observability", tags=["observability"])


@router.get("/status")
async def observability_status() -> dict:
    """Return OpenTelemetry and metrics pipeline status."""
    settings = get_settings()
    payload = get_metrics_store().observability_status()
    payload["environment"] = settings.environment.value
    payload["azure_configured"] = bool(settings.azure_storage_connection_string)
    payload["azure_container_apps"] = settings.azure_container_apps_environment
    return payload


@router.get("/metrics")
async def prometheus_metrics() -> Response:
    """Prometheus-compatible metrics exposition."""
    body = get_metrics_store().prometheus_lines()
    return Response(content=body, media_type="text/plain; version=0.0.4")
