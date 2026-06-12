"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import benchmark_router, observability_router, research_router
from app.services.benchmark.evaluator import BenchmarkEvaluator
from app.cache.redis_client import RedisClient
from app.database.session import close_db
from app.monitoring.health import check_database, check_redis, collect_dependency_status
from app.monitoring.logger import configure_logging, get_logger
from app.monitoring.tracing import init_tracing
from config.settings import get_settings

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_application: FastAPI) -> AsyncIterator[None]:
    """Manage startup and shutdown of shared infrastructure resources."""
    settings = get_settings()
    database_ok = await check_database()
    redis_ok = await check_redis()

    if database_ok:
        logger.info("PostgreSQL connection verified", environment=settings.environment.value)
    else:
        logger.error(
            "PostgreSQL connection failed during startup",
            environment=settings.environment.value,
        )

    if redis_ok:
        logger.info("Redis connection verified", environment=settings.environment.value)
    else:
        logger.error(
            "Redis connection failed during startup",
            environment=settings.environment.value,
        )

    try:
        from app.services.embeddings.embedder import Embedder

        embedder = Embedder()
        await embedder.embed_text("warmup")
        logger.info("Embedding model pre-warmed", dimension=embedder.dimension)
    except Exception as exc:
        logger.warning("Embedding pre-warm skipped", error=str(exc))

    try:
        metrics = BenchmarkEvaluator().evaluate()
        logger.info(
            "Benchmark evaluation complete",
            accuracy_pct=metrics.accuracy_pct,
            citation_precision_pct=metrics.citation_precision_pct,
            hallucination_reduction_pct=metrics.hallucination_reduction_pct,
        )
    except Exception as exc:
        logger.warning("Benchmark evaluation skipped at startup", error=str(exc))

    yield

    await close_db()
    await RedisClient.reset_instance()
    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    configure_logging(settings.log_level.value)

    application = FastAPI(
        title="SynaptiQ ResearchOS",
        version="0.1.0",
        lifespan=lifespan,
    )

    init_tracing(application, otlp_endpoint=settings.otel_exporter_otlp_endpoint)
    application.include_router(research_router)
    application.include_router(benchmark_router)
    application.include_router(observability_router)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """Log unhandled exceptions and return a safe error response."""
        logger.error(
            "Unhandled request exception",
            path=request.url.path,
            method=request.method,
            error=str(exc),
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    @application.get("/health")
    async def health() -> JSONResponse:
        """Return service health and dependency readiness."""
        dependencies = await collect_dependency_status()
        all_up = all(status == "up" for status in dependencies.values())
        payload: dict[str, Any] = {
            "status": "healthy" if all_up else "degraded",
            **dependencies,
        }
        return JSONResponse(
            status_code=200 if all_up else 503,
            content=payload,
        )

    return application


app = create_app()
