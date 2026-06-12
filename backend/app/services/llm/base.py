"""LLM client protocol."""

from __future__ import annotations

from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMClient(Protocol):
    """Protocol for structured LLM generation."""

    async def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        *,
        temperature: float | None = None,
    ) -> T:
        """Generate and validate structured output."""
