"""Shared pytest fixtures for the SynaptiQ backend test suite."""

from __future__ import annotations

import os

import pytest

from config.settings import get_settings

DEFAULT_TEST_ENV = {
    "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/synaptiq",
    "REDIS_URL": "redis://localhost:6379/0",
    "LLM_PROVIDER": "gemini",
    "GEMINI_API_KEY": "test-gemini-key",
}


def pytest_configure() -> None:
    """Set baseline env vars before test modules import application entrypoints."""
    for key, value in DEFAULT_TEST_ENV.items():
        os.environ.setdefault(key, value)


@pytest.fixture(autouse=True)
def default_application_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep env vars stable across tests and refresh the settings cache."""
    get_settings.cache_clear()
    for key, value in DEFAULT_TEST_ENV.items():
        monkeypatch.setenv(key, value)
    yield
    get_settings.cache_clear()
