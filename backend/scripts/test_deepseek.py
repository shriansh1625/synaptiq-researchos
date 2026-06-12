"""Quick DeepSeek API connectivity check."""

from __future__ import annotations

import asyncio
import os
import sys

from pydantic import BaseModel


class PingOut(BaseModel):
    answer: str


async def main() -> int:
    from config.settings import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    if settings.llm_provider.value != "deepseek":
        print(f"LLM_PROVIDER={settings.llm_provider.value} (expected deepseek)")
        return 1
    if not settings.deepseek_api_key:
        print("DEEPSEEK_API_KEY missing")
        return 1

    from app.services.llm.deepseek_client import DeepSeekClient

    client = DeepSeekClient()
    result = await client.generate_structured(
        'Return JSON with field answer set to "ok"',
        PingOut,
    )
    print("DEEPSEEK_OK", result.answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
