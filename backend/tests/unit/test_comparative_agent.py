"""Unit tests for the comparative analysis agent."""

from __future__ import annotations

import pytest

from app.agents.comparative_agent import ComparativeAgent
from app.core.exceptions import SchemaValidationError
from app.models.enums import IntelligenceStatus, RelationType, Verdict
from app.schemas.intelligence import ComparativeOutput
from tests.fixtures.fake_gemini import FakeGeminiClient


class BrokenComparativeClient(FakeGeminiClient):
    """Fake client that simulates malformed comparative JSON from OpenRouter."""

    async def generate_structured(self, prompt, schema, *, temperature=None):
        if schema is ComparativeOutput:
            raise SchemaValidationError("missing relation fields")
        return await super().generate_structured(prompt, schema, temperature=temperature)


def _verified_claim(claim_id: str, paper_id: str) -> dict:
    return {
        "claim_id": claim_id,
        "paper_id": paper_id,
        "text": "Fasting improves insulin sensitivity.",
        "topic": "insulin_sensitivity",
        "verdict": Verdict.SUPPORTED.value,
        "confidence": 0.85,
        "supporting_spans": [],
        "reason": "grounded",
        "needs_review": False,
    }


@pytest.mark.asyncio
async def test_comparative_agent_returns_clusters() -> None:
    """Comparative agent should return structured comparison output."""
    agent = ComparativeAgent(llm_client=FakeGeminiClient())
    claims = [_verified_claim("clm_a", "ss:1"), _verified_claim("clm_b", "ss:2")]

    result = await agent.run(
        query="Compare fasting findings",
        verified_claims=claims,
    )

    comparisons = result["comparisons"]
    assert comparisons["status"] == IntelligenceStatus.OK.value
    assert comparisons["clusters"]
    assert comparisons["clusters"][0]["relations"][0]["relation_type"] == RelationType.AGREES.value
    assert result["agent_log"]["confidence_score"] > 0


@pytest.mark.asyncio
async def test_comparative_agent_insufficient_claims() -> None:
    """Comparative agent should handle a single claim gracefully."""
    agent = ComparativeAgent(llm_client=FakeGeminiClient())
    result = await agent.run(
        query="Compare fasting findings",
        verified_claims=[_verified_claim("clm_a", "ss:1")],
    )

    assert result["comparisons"]["status"] == IntelligenceStatus.INSUFFICIENT_CLAIMS.value
    assert result["contradictions"] == []


@pytest.mark.asyncio
async def test_comparative_agent_falls_back_on_malformed_llm_output() -> None:
    """Malformed OpenRouter comparison JSON should not fail the agent."""
    agent = ComparativeAgent(llm_client=BrokenComparativeClient(), max_attempts=1)
    claims = [_verified_claim("clm_a", "ss:1"), _verified_claim("clm_b", "ss:2")]

    result = await agent.run(
        query="Compare fasting findings",
        verified_claims=claims,
    )

    assert not result.get("errors")
    assert result["comparisons"]["clusters"]
    relation = result["comparisons"]["clusters"][0]["relations"][0]
    assert relation["relation_type"] == RelationType.AGREES.value
    assert relation["needs_review"] is True
