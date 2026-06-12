"""Try common Gemini model IDs against the configured API key."""

from __future__ import annotations

import asyncio
import os

from pydantic import BaseModel

MODELS = (
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash",
)


class PingOut(BaseModel):
    answer: str


async def try_model(model: str) -> None:
    os.environ["GEMINI_MODEL"] = model
    from app.core.discovery_config import get_discovery_config
    from config.settings import get_settings

    get_settings.cache_clear()
    get_discovery_config.cache_clear()

    from app.services.llm.gemini_client import GeminiClient

    try:
        result = await GeminiClient().generate_structured(
            'Return JSON with field answer set to "ok"',
            PingOut,
        )
        print(f"{model}: OK ({result.answer})")
    except Exception as exc:
        print(f"{model}: FAIL {type(exc).__name__} {str(exc)[:160]}")


async def main() -> None:
    for model in MODELS:
        await try_model(model)


if __name__ == "__main__":
    asyncio.run(main())
