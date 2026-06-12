"""OpenTelemetry tracing utilities for SynaptiQ ResearchOS."""

from __future__ import annotations

import functools
import inspect
import time
from collections.abc import Callable
from typing import ParamSpec, TypeVar

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SimpleSpanProcessor,
    SpanExporter,
)
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import Status, StatusCode
from opentelemetry.util._once import Once

P = ParamSpec("P")
R = TypeVar("R")

_INITIALIZED = False
_INSTRUMENTED_APPS: set[int] = set()


def init_tracing(
    app: FastAPI | None = None,
    *,
    service_name: str = "synaptiq-researchos",
    exporter: SpanExporter | None = None,
    otlp_endpoint: str | None = None,
) -> TracerProvider:
    """Initialize OpenTelemetry and optionally instrument a FastAPI application."""
    global _INITIALIZED

    if _INITIALIZED:
        provider = trace.get_tracer_provider()
        if app is not None:
            _instrument_fastapi(app, provider)
        return provider  # type: ignore[return-value]

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    if exporter is None and otlp_endpoint:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )

        exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)

    if exporter is not None:
        processor = (
            SimpleSpanProcessor(exporter)
            if isinstance(exporter, InMemorySpanExporter)
            else BatchSpanProcessor(exporter)
        )
        provider.add_span_processor(processor)

    trace.set_tracer_provider(provider)
    _INITIALIZED = True

    if app is not None:
        _instrument_fastapi(app, provider)

    return provider


def _instrument_fastapi(app: FastAPI, provider: TracerProvider) -> None:
    """Instrument FastAPI once per application instance."""
    app_id = id(app)
    if app_id in _INSTRUMENTED_APPS:
        return

    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
    add_tracing_middleware(app)
    _INSTRUMENTED_APPS.add(app_id)


def add_tracing_middleware(app: FastAPI) -> None:
    """Enrich active request spans with latency and exception details."""

    @app.middleware("http")
    async def tracing_middleware(request, call_next):
        start = time.perf_counter()
        span = trace.get_current_span()

        try:
            response = await call_next(request)
        except Exception as exc:
            if span.is_recording():
                _record_exception(span, exc)
            raise
        else:
            if span.is_recording():
                span.set_attribute("http.status_code", response.status_code)
            return response
        finally:
            if span.is_recording():
                duration_ms = (time.perf_counter() - start) * 1000
                span.set_attribute("http.duration_ms", duration_ms)

    app.state.tracing_middleware_installed = True


def get_tracer(name: str) -> trace.Tracer:
    """Return a tracer for the given module or component name."""
    return trace.get_tracer(name)


def get_current_trace_id() -> str | None:
    """Return the current trace ID as a hex string, if a span is active."""
    span = trace.get_current_span()
    span_context = span.get_span_context()
    if not span_context.is_valid:
        return None
    return format(span_context.trace_id, "032x")


def traced(span_name: str | None = None) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator that creates a span around a sync or async function."""

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        name = span_name or func.__qualname__
        tracer = get_tracer(func.__module__)

        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                start = time.perf_counter()
                with tracer.start_as_current_span(name) as span:
                    try:
                        return await func(*args, **kwargs)
                    except Exception as exc:
                        _record_exception(span, exc)
                        raise
                    finally:
                        if span.is_recording():
                            span.set_attribute(
                                "duration_ms",
                                (time.perf_counter() - start) * 1000,
                            )

            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            start = time.perf_counter()
            with tracer.start_as_current_span(name) as span:
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    _record_exception(span, exc)
                    raise
                finally:
                    if span.is_recording():
                        span.set_attribute(
                            "duration_ms",
                            (time.perf_counter() - start) * 1000,
                        )

        return sync_wrapper  # type: ignore[return-value]

    return decorator


def _record_exception(span: trace.Span, exc: Exception) -> None:
    """Record an exception on the active span."""
    span.record_exception(exc)
    span.set_status(Status(StatusCode.ERROR, str(exc)))


def reset_tracing(app: FastAPI | None = None) -> None:
    """Reset tracing state. Intended for tests."""
    global _INITIALIZED

    if app is not None:
        app_id = id(app)
        if app_id in _INSTRUMENTED_APPS:
            try:
                from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

                FastAPIInstrumentor().uninstrument_app(app)
            except Exception:
                pass
            _INSTRUMENTED_APPS.discard(app_id)
    else:
        _INSTRUMENTED_APPS.clear()

    provider = trace.get_tracer_provider()
    if isinstance(provider, TracerProvider):
        provider.shutdown()

    trace._TRACER_PROVIDER = None  # type: ignore[attr-defined]
    trace._TRACER_PROVIDER_SET_ONCE = Once()  # type: ignore[attr-defined]
    _INITIALIZED = False
