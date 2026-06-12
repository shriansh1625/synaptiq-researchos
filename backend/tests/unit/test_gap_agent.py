"""Unit tests for the research gap detection agent."""

from __future__ import annotations

import pytest

from app.agents.gap_agent import GapAgent
from app.core.exceptions import SchemaValidationError
from app.models.enums import GapType, IntelligenceStatus, Verdict
from app.schemas.intelligence import GapDetectionOutput
from tests.fixtures.fake_gemini import FakeGeminiClient


class BrokenGapClient(FakeGeminiClient):
    """Fake client that simulates partial/malformed gap JSON from OpenRouter."""

    async def generate_structured(self, prompt, schema, *, temperature=None):
        if schema is GapDetectionOutput:
            raise SchemaValidationError("missing description and impact_score")
        return await super().generate_structured(prompt, schema, temperature=temperature)


@pytest.mark.asyncio
async def test_gap_agent_detects_gaps() -> None:
    """Gap agent should return structured research gaps."""
    agent = GapAgent(llm_client=FakeGeminiClient())
    claims = [
        {
            "claim_id": "clm_1",
            "paper_id": "ss:paper-1",
            "text": "Fasting improves insulin sensitivity.",
            "topic": "insulin_sensitivity",
            "verdict": Verdict.SUPPORTED.value,
            "confidence": 0.9,
            "supporting_spans": [],
            "reason": "grounded",
            "needs_review": False,
        }
    ]
    papers = [{"paper_id": "ss:paper-1", "year": 2021, "venue": "Cell Metab", "source": "semantic_scholar"}]

    result = await agent.run(
        query="What gaps exist in fasting research?",
        verified_claims=claims,
        papers=papers,
        comparisons={"clusters": []},
    )

    assert result["research_gaps"]
    assert result["research_gaps"][0]["gap_type"] == GapType.UNDERSTUDIED.value
    assert result["agent_log"]["confidence_score"] > 0


@pytest.mark.asyncio
async def test_gap_agent_insufficient_context() -> None:
    """Gap agent should return insufficient_context when no claims exist."""
    agent = GapAgent(llm_client=FakeGeminiClient())
    result = await agent.run(
        query="What gaps exist?",
        verified_claims=[],
        papers=[],
        comparisons={},
    )

    assert result["research_gaps"] == []
    assert result["agent_log"]["output_data"]["status"] == IntelligenceStatus.INSUFFICIENT_CONTEXT.value


@pytest.mark.asyncio
async def test_gap_agent_falls_back_on_malformed_llm_output() -> None:
    """Malformed OpenRouter gap JSON should not fail the gap agent."""
    agent = GapAgent(llm_client=BrokenGapClient(), max_attempts=1)
    claims = [
        {
            "claim_id": "clm_1",
            "paper_id": "ss:paper-1",
            "text": "Fasting improves insulin sensitivity.",
            "topic": "insulin_sensitivity",
            "verdict": Verdict.SUPPORTED.value,
            "confidence": 0.9,
            "supporting_spans": [],
            "reason": "grounded",
            "needs_review": False,
        }
    ]

    result = await agent.run(
        query="What gaps exist in fasting research?",
        verified_claims=claims,
        papers=[{"paper_id": "ss:paper-1", "year": 2021}],
        comparisons={"clusters": []},
    )

    assert not result.get("errors")
    assert result["research_gaps"]
    assert result["research_gaps"][0]["description"]
    assert result["agent_log"]["confidence_score"] == 0.45
