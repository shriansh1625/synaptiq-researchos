"""OpenRouter structured generation client (DeepSeek and other models)."""

from __future__ import annotations

import json
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.core.discovery_config import get_discovery_config
from app.core.exceptions import SchemaValidationError
from app.services.llm.json_utils import extract_json
from config.settings import get_settings

T = TypeVar("T", bound=BaseModel)

OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterClient:
    """OpenRouter chat-completions client with JSON schema validation."""

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
        raw = await self._generate_raw(
            prompt,
            temperature=temperature if temperature is not None else self._config.gemini_temperature,
        )
        try:
            payload = json.loads(raw)
            return schema.model_validate(payload)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise SchemaValidationError(f"OpenRouter output failed validation: {exc}") from exc

    async def _generate_raw(self, prompt: str, *, temperature: float) -> str:
        api_key = self._settings.openrouter_api_key
        if not api_key:
            raise SchemaValidationError("OPENROUTER_API_KEY is not configured")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://synaptiq.local",
            "X-Title": "SynaptiQ ResearchOS",
        }
        body = {
            "model": self._settings.openrouter_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a research intelligence agent. "
                        "Return only valid JSON matching the requested schema. "
                        "Do not wrap output in markdown fences."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(OPENROUTER_CHAT_URL, headers=headers, json=body)
            if response.status_code >= 400:
                detail = response.text[:500]
                raise SchemaValidationError(
                    f"OpenRouter request failed ({response.status_code}): {detail}"
                )
            data = response.json()

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise SchemaValidationError(f"Unexpected OpenRouter response shape: {data}") from exc

        if not content:
            raise SchemaValidationError("OpenRouter returned empty content")
        return extract_json(str(content))
