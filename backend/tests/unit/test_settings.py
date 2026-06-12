"""Unit tests for application settings."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from config.settings import Environment, LogLevel, Settings, get_settings

VALID_ENV = {
    "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/synaptiq",
    "REDIS_URL": "redis://localhost:6379/0",
    "GEMINI_API_KEY": "test-gemini-key",
}


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    """Ensure settings cache does not leak between tests."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_settings_loads_from_environment_variables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Settings should read required values from environment variables."""
    for key, value in VALID_ENV.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    settings = Settings()

    assert settings.database_url == VALID_ENV["DATABASE_URL"]
    assert settings.redis_url == VALID_ENV["REDIS_URL"]
    assert settings.gemini_api_key == VALID_ENV["GEMINI_API_KEY"]
    assert settings.environment == Environment.DEVELOPMENT
    assert settings.log_level == LogLevel.DEBUG


def test_settings_loads_from_dotenv_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Settings should load values from a .env file."""
    for key in (
        "DATABASE_URL",
        "REDIS_URL",
        "GEMINI_API_KEY",
        "ENVIRONMENT",
        "LOG_LEVEL",
        "SEMANTIC_SCHOLAR_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)

    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "DATABASE_URL=postgresql://user:pass@localhost:5432/synaptiq",
                "REDIS_URL=redis://localhost:6379/1",
                "GEMINI_API_KEY=dotenv-gemini-key",
                "ENVIRONMENT=staging",
                "LOG_LEVEL=WARNING",
                "SEMANTIC_SCHOLAR_API_KEY=ss-key",
            ]
        ),
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_file)

    assert settings.database_url == "postgresql://user:pass@localhost:5432/synaptiq"
    assert settings.redis_url == "redis://localhost:6379/1"
    assert settings.gemini_api_key == "dotenv-gemini-key"
    assert settings.environment == Environment.STAGING
    assert settings.log_level == LogLevel.WARNING
    assert settings.semantic_scholar_api_key == "ss-key"


def test_settings_applies_defaults_for_optional_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Optional settings should use documented defaults."""
    for key, value in VALID_ENV.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "")

    settings = Settings()

    assert settings.environment == Environment.DEVELOPMENT
    assert settings.log_level == LogLevel.INFO
    assert settings.semantic_scholar_api_key is None
    assert settings.azure_storage_connection_string is None


@pytest.mark.parametrize(
    ("database_url", "message"),
    [
        ("mysql://localhost/db", "postgresql"),
        ("", "DATABASE_URL"),
    ],
)
def test_settings_rejects_invalid_database_url(
    monkeypatch: pytest.MonkeyPatch,
    database_url: str,
    message: str,
) -> None:
    """DATABASE_URL must use a supported PostgreSQL scheme."""
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("REDIS_URL", VALID_ENV["REDIS_URL"])
    monkeypatch.setenv("GEMINI_API_KEY", VALID_ENV["GEMINI_API_KEY"])

    with pytest.raises(ValidationError) as exc_info:
        Settings()

    assert message in str(exc_info.value)


@pytest.mark.parametrize(
    "redis_url",
    ["http://localhost:6379", "tcp://localhost:6379", ""],
)
def test_settings_rejects_invalid_redis_url(
    monkeypatch: pytest.MonkeyPatch,
    redis_url: str,
) -> None:
    """REDIS_URL must use redis:// or rediss://."""
    monkeypatch.setenv("DATABASE_URL", VALID_ENV["DATABASE_URL"])
    monkeypatch.setenv("REDIS_URL", redis_url)
    monkeypatch.setenv("GEMINI_API_KEY", VALID_ENV["GEMINI_API_KEY"])

    with pytest.raises(ValidationError) as exc_info:
        Settings()

    assert "REDIS_URL" in str(exc_info.value)


def test_settings_rejects_empty_gemini_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GEMINI_API_KEY must be present when LLM_PROVIDER=gemini."""
    monkeypatch.setenv("DATABASE_URL", VALID_ENV["DATABASE_URL"])
    monkeypatch.setenv("REDIS_URL", VALID_ENV["REDIS_URL"])
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "   ")

    with pytest.raises(ValidationError) as exc_info:
        Settings()

    assert "GEMINI_API_KEY is required" in str(exc_info.value)


def test_settings_accepts_openrouter_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OpenRouter provider should require OPENROUTER_API_KEY only."""
    monkeypatch.setenv("DATABASE_URL", VALID_ENV["DATABASE_URL"])
    monkeypatch.setenv("REDIS_URL", VALID_ENV["REDIS_URL"])
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    settings = Settings()

    assert settings.llm_provider.value == "openrouter"
    assert settings.openrouter_api_key == "test-openrouter-key"
    assert settings.openrouter_model == "deepseek/deepseek-chat"


def test_settings_requires_azure_storage_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Production deployments must provide Azure storage configuration."""
    for key, value in VALID_ENV.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("ENVIRONMENT", "production")

    with pytest.raises(ValidationError) as exc_info:
        Settings()

    assert "AZURE_STORAGE_CONNECTION_STRING" in str(exc_info.value)


def test_settings_accepts_production_with_azure_storage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Production settings are valid when Azure storage is configured."""
    for key, value in VALID_ENV.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv(
        "AZURE_STORAGE_CONNECTION_STRING",
        "DefaultEndpointsProtocol=https;AccountName=test;AccountKey=key;EndpointSuffix=core.windows.net",
    )

    settings = Settings()

    assert settings.environment == Environment.PRODUCTION
    assert settings.azure_storage_connection_string is not None


def test_get_settings_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_settings should return the same cached instance."""
    for key, value in VALID_ENV.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("LLM_PROVIDER", "gemini")

    first = get_settings()
    second = get_settings()

    assert first is second


def test_settings_strips_whitespace_from_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Secret values should be normalized by trimming whitespace."""
    monkeypatch.setenv("DATABASE_URL", f"  {VALID_ENV['DATABASE_URL']}  ")
    monkeypatch.setenv("REDIS_URL", f"  {VALID_ENV['REDIS_URL']}  ")
    monkeypatch.setenv("GEMINI_API_KEY", "  trimmed-gemini-key  ")
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "  ss-key  ")

    settings = Settings()

    assert settings.database_url == VALID_ENV["DATABASE_URL"]
    assert settings.redis_url == VALID_ENV["REDIS_URL"]
    assert settings.gemini_api_key == "trimmed-gemini-key"
    assert settings.semantic_scholar_api_key == "ss-key"


def test_settings_rejects_invalid_log_level(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """LOG_LEVEL must be one of the supported enum values."""
    for key, value in VALID_ENV.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("LOG_LEVEL", "VERBOSE")

    with pytest.raises(ValidationError):
        Settings()


def test_settings_missing_required_fields_raise_validation_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing required environment variables should fail fast."""
    for key in list(VALID_ENV) + [
        "DATABASE_URL",
        "REDIS_URL",
        "GEMINI_API_KEY",
        "LLM_PROVIDER",
        "OPENROUTER_API_KEY",
    ]:
        monkeypatch.delenv(key, raising=False)

    # Ensure pytest environment does not accidentally satisfy required fields.
    for key in os.environ:
        if key in {
            "DATABASE_URL",
            "REDIS_URL",
            "GEMINI_API_KEY",
            "LLM_PROVIDER",
            "OPENROUTER_API_KEY",
        }:
            monkeypatch.delenv(key, raising=False)

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)

    error_text = str(exc_info.value)
    assert "database_url" in error_text
    assert "redis_url" in error_text
