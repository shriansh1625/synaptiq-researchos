"""Application settings loaded from environment variables and .env files."""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Self

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ENV_FILE = _BACKEND_DIR / ".env"


class Environment(StrEnum):
    """Deployment environment."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(StrEnum):
    """Logging verbosity."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LLMProvider(StrEnum):
    """Structured LLM backend."""

    GEMINI = "gemini"
    OPENROUTER = "openrouter"
    DEEPSEEK = "deepseek"


class Settings(BaseSettings):
    """SynaptiQ ResearchOS runtime configuration."""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = Field(
        ...,
        description="PostgreSQL connection URL",
        examples=["postgresql+asyncpg://user:pass@localhost:5432/synaptiq"],
    )
    redis_url: str = Field(
        ...,
        description="Redis connection URL",
        examples=["redis://localhost:6379/0"],
    )
    llm_provider: LLMProvider = Field(
        default=LLMProvider.GEMINI,
        description="LLM backend for agent structured generation",
    )
    gemini_api_key: str | None = Field(
        default=None,
        description="Google Gemini API key (required when LLM_PROVIDER=gemini)",
    )
    openrouter_api_key: str | None = Field(
        default=None,
        description="OpenRouter API key (required when LLM_PROVIDER=openrouter)",
    )
    openrouter_model: str = Field(
        default="deepseek/deepseek-chat",
        description="OpenRouter model slug",
    )
    deepseek_api_key: str | None = Field(
        default=None,
        description="DeepSeek platform API key (required when LLM_PROVIDER=deepseek)",
    )
    deepseek_model: str = Field(
        default="deepseek-chat",
        description="DeepSeek model name",
    )
    semantic_scholar_api_key: str | None = Field(
        default=None,
        description="Optional Semantic Scholar API key",
    )
    environment: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Deployment environment",
    )
    log_level: LogLevel = Field(
        default=LogLevel.INFO,
        description="Application log level",
    )
    azure_storage_connection_string: str | None = Field(
        default=None,
        description="Azure Blob Storage connection string",
    )
    otel_exporter_otlp_endpoint: str | None = Field(
        default=None,
        description="OTLP gRPC endpoint for OpenTelemetry trace export",
    )
    benchmark_fast_enabled: bool = Field(
        default=True,
        description="Enable sub-8s hero-query fast path for benchmark demos",
    )
    azure_container_apps_environment: str | None = Field(
        default=None,
        description="Azure Container Apps environment name (production)",
    )

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        """Ensure DATABASE_URL uses a supported PostgreSQL scheme."""
        normalized = value.strip()
        allowed_prefixes = (
            "postgresql://",
            "postgresql+asyncpg://",
            "postgresql+psycopg://",
            "postgresql+psycopg2://",
        )
        if not normalized.startswith(allowed_prefixes):
            msg = (
                "DATABASE_URL must start with postgresql://, "
                "postgresql+asyncpg://, postgresql+psycopg://, or "
                "postgresql+psycopg2://"
            )
            raise ValueError(msg)
        return normalized

    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, value: str) -> str:
        """Ensure REDIS_URL uses a supported Redis scheme."""
        normalized = value.strip()
        if not normalized.startswith(("redis://", "rediss://")):
            raise ValueError("REDIS_URL must start with redis:// or rediss://")
        return normalized

    @field_validator("gemini_api_key")
    @classmethod
    def validate_gemini_api_key(cls, value: str | None) -> str | None:
        """Strip whitespace and reject empty or too-short Gemini keys when provided."""
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        if len(normalized) < 8:
            raise ValueError("GEMINI_API_KEY must be at least 8 characters")
        return normalized

    @field_validator("openrouter_api_key", "deepseek_api_key")
    @classmethod
    def validate_llm_api_keys(cls, value: str | None) -> str | None:
        """Strip whitespace and reject empty or too-short LLM keys when provided."""
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        if len(normalized) < 8:
            raise ValueError("API key must be at least 8 characters")
        return normalized

    @field_validator("semantic_scholar_api_key", "azure_storage_connection_string")
    @classmethod
    def strip_optional_secrets(cls, value: str | None) -> str | None:
        """Normalize optional secret values."""
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def validate_environment_requirements(self) -> Self:
        """Apply environment-specific validation rules."""
        if self.llm_provider == LLMProvider.GEMINI and not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required when LLM_PROVIDER=gemini")
        if self.llm_provider == LLMProvider.OPENROUTER and not self.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY is required when LLM_PROVIDER=openrouter")
        if self.llm_provider == LLMProvider.DEEPSEEK and not self.deepseek_api_key:
            raise ValueError("DEEPSEEK_API_KEY is required when LLM_PROVIDER=deepseek")
        if self.environment == Environment.PRODUCTION:
            if not self.azure_storage_connection_string:
                raise ValueError(
                    "AZURE_STORAGE_CONNECTION_STRING is required when ENVIRONMENT=production"
                )
        return self


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
