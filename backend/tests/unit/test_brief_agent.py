"""Unit tests for the executive brief agent."""

from __future__ import annotations

import pytest

from app.agents.brief_agent import BriefAgent
from app.core.exceptions import SchemaValidationError
from app.models.enums import BriefStatus, Verdict
from app.schemas.brief import ExecutiveBriefOutput
from tests.fixtures.fake_gemini import FakeGeminiClient


class BrokenBriefClient(FakeGeminiClient):
    """Fake client that simulates malformed brief citations from OpenRouter."""

    async def generate_structured(self, prompt, schema, *, temperature=None):
        if schema is ExecutiveBriefOutput:
            raise SchemaValidationError("citations must be objects")
        return await super().generate_structured(prompt, schema, temperature=temperature)


@pytest.mark.asyncio
async def test_brief_agent_generates_grounded_brief() -> None:
    """Brief agent should return structured executive output."""
    agent = BriefAgent(llm_client=FakeGeminiClient())
    claims = [
        {
            "claim_id": "clm_1",
            "paper_id": "ss:paper-1",
            "text": "Fasting improves insulin sensitivity.",
            "topic": "insulin_sensitivity",
            "verdict": Verdict.SUPPORTED.value,
            "confidence": 0.9,
            "reason": "grounded",
        }
    ]
    gaps = [
        {
            "gap_id": "gap_1",
            "gap_type": "UNDERSTUDIED",
            "topic": "long_term",
            "description": "Limited long-term evidence.",
            "impact_score": 0.7,
            "actionability_note": "Run longer trials.",
        }
    ]

    result = await agent.run(
        query="Does fasting improve insulin sensitivity?",
        verified_claims=claims,
        comparisons={"clusters": []},
        research_gaps=gaps,
        contradictions=[],
        papers=[{"paper_id": "ss:paper-1", "title": "Fasting Study"}],
        citations=[],
    )

    brief = result["executive_brief"]
    assert brief["status"] == BriefStatus.OK.value
    assert brief["report"]["key_findings"]
    assert result["agent_log"]["confidence_score"] > 0
    assert result["executive_brief"]["citation_integrity"]["checked"] is True


@pytest.mark.asyncio
async def test_brief_agent_falls_back_on_malformed_llm_output() -> None:
    """Malformed OpenRouter brief JSON should not fail report synthesis."""
    agent = BriefAgent(llm_client=BrokenBriefClient(), max_attempts=1)
    claims = [
        {
            "claim_id": "clm_1",
            "paper_id": "ss:paper-1",
            "text": "Fasting improves insulin sensitivity.",
            "topic": "insulin_sensitivity",
            "verdict": Verdict.SUPPORTED.value,
            "confidence": 0.9,
            "reason": "grounded",
        }
    ]
    gaps = [
        {
            "gap_id": "gap_1",
            "gap_type": "UNDERSTUDIED",
            "topic": "long_term",
            "description": "Limited long-term evidence.",
            "impact_score": 0.7,
            "actionability_note": "Run longer trials.",
        }
    ]

    result = await agent.run(
        query="Does fasting improve insulin sensitivity?",
        verified_claims=claims,
        comparisons={"clusters": []},
        research_gaps=gaps,
        contradictions=[],
        papers=[{"paper_id": "ss:paper-1", "title": "Fasting Study"}],
        citations=[],
    )

    assert not result.get("errors")
    brief = result["executive_brief"]
    assert brief["report"]["key_findings"]
    assert isinstance(brief["citations"][0], dict)
    assert brief["warnings"]
