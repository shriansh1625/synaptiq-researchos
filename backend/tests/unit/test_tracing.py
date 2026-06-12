"""Tests for OpenTelemetry tracing utilities."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode

from app.monitoring.tracing import (
    get_current_trace_id,
    get_tracer,
    init_tracing,
    reset_tracing,
    traced,
)


@pytest.fixture
def span_exporter() -> InMemorySpanExporter:
    """Provide a fresh in-memory span exporter."""
    return InMemorySpanExporter()


@pytest.fixture
def tracing_provider(span_exporter: InMemorySpanExporter) -> TracerProvider:
    """Initialize tracing with an in-memory exporter."""
    reset_tracing()
    provider = init_tracing(exporter=span_exporter)
    yield provider
    reset_tracing()


@pytest.fixture(autouse=True)
def cleanup_tracing() -> None:
    """Ensure tracing state does not leak between tests."""
    reset_tracing()
    yield
    reset_tracing()


def test_init_tracing_configures_tracer_provider(
    tracing_provider: TracerProvider,
) -> None:
    """init_tracing should configure a tracer provider."""
    tracer = get_tracer("synaptiq.test")
    assert tracer is not None
    assert isinstance(tracing_provider, TracerProvider)


def test_traced_decorator_records_sync_span(
    tracing_provider: TracerProvider,
    span_exporter: InMemorySpanExporter,
) -> None:
    """The traced decorator should create spans for sync functions."""

    @traced("sync-work")
    def do_work(value: int) -> int:
        return value + 1

    assert do_work(2) == 3

    spans = span_exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "sync-work"
    assert spans[0].attributes["duration_ms"] >= 0


@pytest.mark.asyncio
async def test_traced_decorator_records_async_span_and_exceptions(
    tracing_provider: TracerProvider,
    span_exporter: InMemorySpanExporter,
) -> None:
    """The traced decorator should record async spans and exceptions."""

    @traced("async-work")
    async def failing_work() -> None:
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        await failing_work()

    spans = span_exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "async-work"
    assert spans[0].status.status_code == StatusCode.ERROR
    assert any(event.name == "exception" for event in spans[0].events)


def test_fastapi_tracing_records_request_span_and_latency(
    span_exporter: InMemorySpanExporter,
) -> None:
    """FastAPI instrumentation should record request spans with latency."""
    app = FastAPI()
    init_tracing(app, exporter=span_exporter)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "healthy"}

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200

    spans = span_exporter.get_finished_spans()
    assert len(spans) >= 1
    assert any(span.attributes.get("http.duration_ms", 0) >= 0 for span in spans)
    assert any(
        "health" in (span.name or "") or span.attributes.get("http.route") == "/health"
        for span in spans
    )

    reset_tracing(app)


def test_fastapi_tracing_records_exceptions(
    span_exporter: InMemorySpanExporter,
) -> None:
    """FastAPI tracing should record exceptions on failing requests."""
    app = FastAPI()
    init_tracing(app, exporter=span_exporter)

    @app.get("/fail")
    def fail() -> None:
        raise RuntimeError("request failed")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/fail")

    assert response.status_code == 500

    spans = span_exporter.get_finished_spans()
    assert any(span.status.status_code == StatusCode.ERROR for span in spans)
    assert any(any(event.name == "exception" for event in span.events) for span in spans)

    reset_tracing(app)


def test_get_current_trace_id_returns_active_trace(
    tracing_provider: TracerProvider,
) -> None:
    """get_current_trace_id should return the active trace ID inside a span."""
    tracer = get_tracer("synaptiq.trace-id")

    with tracer.start_as_current_span("trace-id-test"):
        trace_id = get_current_trace_id()

    assert trace_id is not None
    assert len(trace_id) == 32
