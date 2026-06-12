"""LLM client factory."""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from app.core.exceptions import SchemaValidationError
from app.services.llm.base import LLMClient
from app.services.llm.deepseek_client import DeepSeekClient
from app.services.llm.gemini_client import GeminiClient
from app.services.llm.openrouter_client import OpenRouterClient
from config.settings import LLMProvider, get_settings

T = TypeVar("T", bound=BaseModel)


class _FallbackLLMClient:
    """Try the configured provider first, then fall back to an alternate."""

    def __init__(self, primary: LLMClient, secondary: LLMClient | None) -> None:
        self._primary = primary
        self._secondary = secondary

    async def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        *,
        temperature: float | None = None,
    ) -> T:
        try:
            return await self._primary.generate_structured(
                prompt,
                schema,
                temperature=temperature,
            )
        except SchemaValidationError as primary_exc:
            if self._secondary is None:
                raise
            try:
                return await self._secondary.generate_structured(
                    prompt,
                    schema,
                    temperature=temperature,
                )
            except SchemaValidationError as secondary_exc:
                raise SchemaValidationError(
                    f"All LLM providers failed. primary={primary_exc}; secondary={secondary_exc}"
                ) from secondary_exc


def _valid_secret(value: str | None) -> bool:
    return bool(value and len(value.strip()) >= 8)


def get_llm_client() -> LLMClient:
    """Return the configured LLM client for agent pipelines."""
    settings = get_settings()
    if settings.llm_provider == LLMProvider.DEEPSEEK:
        secondary = GeminiClient() if _valid_secret(settings.gemini_api_key) else None
        if secondary is None and _valid_secret(settings.openrouter_api_key):
            secondary = OpenRouterClient()
        return _FallbackLLMClient(DeepSeekClient(), secondary)
    if settings.llm_provider == LLMProvider.OPENROUTER:
        secondary = GeminiClient() if _valid_secret(settings.gemini_api_key) else None
        if secondary is None and _valid_secret(settings.deepseek_api_key):
            secondary = DeepSeekClient()
        return _FallbackLLMClient(OpenRouterClient(), secondary)
    secondary = DeepSeekClient() if _valid_secret(settings.deepseek_api_key) else None
    if secondary is None and _valid_secret(settings.openrouter_api_key):
        secondary = OpenRouterClient()
    return _FallbackLLMClient(GeminiClient(), secondary)
