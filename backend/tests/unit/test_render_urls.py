"""Tests for Render connection URL normalization."""

from __future__ import annotations

import pytest
from sqlalchemy.engine import make_url

from config.render_urls import normalize_database_url, normalize_render_database_url


def test_normalize_render_database_url_expands_internal_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Internal Render Postgres hostnames should expand to external FQDNs."""
    monkeypatch.setenv("RENDER_DB_REGION", "oregon")
    url = make_url("postgresql://synaptiq:secret@dpg-abc123def456-a:5432/synaptiq")

    normalized = normalize_render_database_url(url)

    assert normalized.host == "dpg-abc123def456-a.oregon-postgres.render.com"


def test_normalize_database_url_preserves_localhost() -> None:
    """Local development URLs should remain unchanged."""
    original = "postgresql://user:pass@localhost:5432/synaptiq"
    assert normalize_database_url(original) == original
