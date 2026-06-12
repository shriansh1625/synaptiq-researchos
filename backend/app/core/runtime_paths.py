"""Runtime filesystem paths for reports and knowledge graphs."""

from __future__ import annotations

from pathlib import Path


def backend_root() -> Path:
    """Return the backend package root directory."""
    return Path(__file__).resolve().parents[2]


def get_reports_dir() -> Path:
    """Directory for generated PDF reports."""
    path = backend_root() / "data" / "reports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_graphs_dir() -> Path:
    """Directory for exported knowledge graph HTML files."""
    path = backend_root() / "data" / "graphs"
    path.mkdir(parents=True, exist_ok=True)
    return path
