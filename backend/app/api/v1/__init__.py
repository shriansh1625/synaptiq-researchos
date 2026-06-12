"""API v1 package."""

from app.api.v1.routes_benchmark import router as benchmark_router
from app.api.v1.routes_observability import router as observability_router
from app.api.v1.routes_research import router as research_router

__all__ = ["research_router", "benchmark_router", "observability_router"]
