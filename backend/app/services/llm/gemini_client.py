"""Gemini structured generation client."""

from __future__ import annotations

import json
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.core.discovery_config import get_discovery_config
from app.core.exceptions import RateLimitError, SchemaValidationError
from app.core.retry import async_retry
from app.services.llm.gemini_throttle import GeminiThrottle
from app.services.llm.json_utils import extract_json
from config.settings import get_settings

T = TypeVar("T", bound=BaseModel)


def _is_rate_limited(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(
        token in message
        for token in ("429", "quota", "rate limit", "resource_exhausted", "too many requests")
    )


class GeminiClient:
    """Gemini client with JSON schema validation and gentle rate limiting."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._config = get_discovery_config()

    async def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        *,
        temperature: float | None = None,
    ) -> T:
        raw = await async_retry(
            lambda: self._generate_raw(
                prompt,
                temperature=temperature if temperature is not None else self._config.gemini_temperature,
            ),
            max_attempts=3,
            base_delay=1.0,
            max_delay=12.0,
            retry_on=(RateLimitError,),
        )
        try:
            payload = json.loads(raw)
            return schema.model_validate(payload)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise SchemaValidationError(f"Gemini output failed validation: {exc}") from exc

    async def _generate_raw(self, prompt: str, *, temperature: float) -> str:
        import asyncio

        import google.generativeai as genai

        async with GeminiThrottle():
            def _call() -> str:
                if not self._settings.gemini_api_key:
                    raise SchemaValidationError("GEMINI_API_KEY is not configured")
                try:
                    genai.configure(api_key=self._settings.gemini_api_key)
                    model = genai.GenerativeModel(self._config.gemini_model)
                    response = model.generate_content(
                        prompt,
                        generation_config={
                            "temperature": temperature,
                            "response_mime_type": "application/json",
                        },
                    )
                    text = getattr(response, "text", None) or ""
                    if not text and response.candidates:
                        parts = response.candidates[0].content.parts
                        text = "".join(getattr(part, "text", "") for part in parts)
                    return extract_json(text)
                except SchemaValidationError:
                    raise
                except Exception as exc:
                    if _is_rate_limited(exc):
                        raise RateLimitError(str(exc)) from exc
                    raise SchemaValidationError(f"Gemini request failed: {exc}") from exc

            return await asyncio.to_thread(_call)
