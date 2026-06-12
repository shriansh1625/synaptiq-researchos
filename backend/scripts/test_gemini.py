"""Quick Gemini API connectivity check."""

from __future__ import annotations

import asyncio
import sys

from pydantic import BaseModel


class PingOut(BaseModel):
    answer: str


async def main() -> int:
    from config.settings import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    if settings.llm_provider.value != "gemini":
        print(f"LLM_PROVIDER={settings.llm_provider.value} (expected gemini)")
        return 1
    if not settings.gemini_api_key:
        print("GEMINI_API_KEY missing")
        return 1

    from app.core.discovery_config import get_discovery_config
    from app.services.llm.gemini_client import GeminiClient

    get_discovery_config.cache_clear()
    model = get_discovery_config().gemini_model
    print(f"MODEL={model}")
    client = GeminiClient()
    try:
        result = await client.generate_structured(
            'Return JSON with field answer set to "ok"',
            PingOut,
        )
    except Exception as exc:
        print("GEMINI_FAIL", type(exc).__name__, str(exc)[:300])
        return 1
    print("GEMINI_OK", result.answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
