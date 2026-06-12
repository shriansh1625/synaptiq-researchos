"""API tests for health endpoints."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from main import app, create_app


@patch("app.monitoring.health.check_database", new_callable=AsyncMock, return_value=True)
@patch("app.monitoring.health.check_redis", new_callable=AsyncMock, return_value=True)
def test_health_returns_healthy_status(
    _mock_redis: AsyncMock,
    _mock_database: AsyncMock,
) -> None:
    """GET /health should return a healthy status payload when dependencies are up."""
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "database": "up",
        "redis": "up",
    }


@patch("app.monitoring.health.check_database", new_callable=AsyncMock, return_value=False)
@patch("app.monitoring.health.check_redis", new_callable=AsyncMock, return_value=True)
def test_health_returns_degraded_when_database_is_down(
    _mock_redis: AsyncMock,
    _mock_database: AsyncMock,
) -> None:
    """GET /health should return 503 when PostgreSQL is unavailable."""
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
    assert response.json()["database"] == "down"


def test_create_app_returns_configured_application() -> None:
    """create_app should return a new FastAPI instance."""
    application = create_app()

    assert application.title == "SynaptiQ ResearchOS"
    assert application.version == "0.1.0"


@patch("app.monitoring.health.check_database", new_callable=AsyncMock, return_value=True)
@patch("app.monitoring.health.check_redis", new_callable=AsyncMock, return_value=True)
def test_cors_allows_cross_origin_requests(
    _mock_redis: AsyncMock,
    _mock_database: AsyncMock,
) -> None:
    """CORS middleware should allow configured cross-origin access."""
    client = TestClient(app)

    response = client.get(
        "/health",
        headers={"Origin": "http://localhost:3000"},
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "*"
