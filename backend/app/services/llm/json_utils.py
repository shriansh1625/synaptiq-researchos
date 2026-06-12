"""JSON extraction helpers for structured LLM responses."""

from __future__ import annotations

import re


def extract_json(text: str) -> str:
    """Extract a JSON object from model output, stripping markdown fences if present."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped
    match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
    if match:
        return match.group(0)
    return stripped
