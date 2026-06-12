"""API tests for research intelligence routes."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.database.session import get_db
from main import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    db = AsyncMock()

    async def override_get_db() -> AsyncGenerator[AsyncMock, None]:
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_create_query_endpoint(client: TestClient) -> None:
    """POST /query should create a research session."""
    session_id = uuid.uuid4()
    with patch("app.api.v1.routes_research.ResearchPipelineService") as pipeline_cls:
        pipeline = pipeline_cls.return_value
        pipeline.create_query_session = AsyncMock(return_value=session_id)
        session = MagicMock()
        session.query = "Does fasting help?"
        session.status = "pending"
        with patch("app.api.v1.routes_research.ResearchSessionRepository") as repo_cls:
            repo_cls.return_value.get_by_id = AsyncMock(return_value=session)
            response = client.post("/query", json={"query": "Does fasting help?"})
    assert response.status_code == 201
    assert response.json()["session_id"] == str(session_id)


def test_analyze_requires_query_or_session(client: TestClient) -> None:
    """POST /analyze should reject empty payloads."""
    response = client.post("/analyze", json={})
    assert response.status_code == 400


def test_get_report_json_endpoint(client: TestClient) -> None:
    """GET /report/{id}/json should return structured report metadata."""
    report_id = uuid.uuid4()
    session_id = uuid.uuid4()
    report = MagicMock()
    report.id = report_id
    report.session_id = session_id
    report.summary = "Executive summary"
    report.recommendations = {"title": "Test Report", "pdf_path": "/nonexistent.pdf"}
    report.citations = [{"citation_id": "c1", "claim_id": "claim-1"}]
    report.created_at = None

    with patch("app.api.v1.routes_research.ExecutiveReportRepository") as repo_cls:
        repo_cls.return_value.get_by_id = AsyncMock(return_value=report)
        response = client.get(f"/report/{report_id}/json")

    assert response.status_code == 200
    body = response.json()
    assert body["report_id"] == str(report_id)
    assert body["summary"] == "Executive summary"
    assert body["recommendations"]["title"] == "Test Report"
