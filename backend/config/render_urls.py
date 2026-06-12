"""Normalize Render-managed datastore URLs for reliable cross-region deploys."""

from __future__ import annotations

import os
import re

from sqlalchemy.engine import URL, make_url

_RENDER_PG_INTERNAL_HOST = re.compile(r"^dpg-[a-z0-9]+-[a-z]$", re.IGNORECASE)


def render_postgres_region() -> str:
    """Render Postgres region slug used in external hostnames."""
    return os.environ.get("RENDER_DB_REGION", "oregon").strip().lower()


def normalize_render_database_url(url: URL) -> URL:
    """Expand Render internal Postgres hostnames to external FQDNs."""
    host = url.host or ""
    if _RENDER_PG_INTERNAL_HOST.fullmatch(host):
        external_host = f"{host}.{render_postgres_region()}-postgres.render.com"
        return url.set(host=external_host)
    return url


def normalize_database_url(database_url: str) -> str:
    """Normalize a PostgreSQL URL for application and migration use."""
    url = normalize_render_database_url(make_url(database_url.strip()))
    return url.render_as_string(hide_password=False)
