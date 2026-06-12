"""Unit tests for the verification agent."""

from __future__ import annotations

import pytest

from app.agents.verification_agent import VerificationAgent
from app.core.exceptions import SchemaValidationError
from app.models.enums import PaperSource, Verdict
from app.schemas.intelligence import VerificationExtractOutput, VerificationVerifyOutput
from tests.fixtures.fake_gemini import FakeGeminiClient


class BrokenVerificationClient(FakeGeminiClient):
    """Fake client that simulates malformed extraction JSON from OpenRouter."""

    async def generate_structured(self, prompt, schema, *, temperature=None):
        if schema is VerificationExtractOutput:
            raise SchemaValidationError("missing paper_id")
        if schema is VerificationVerifyOutput:
            raise SchemaValidationError("malformed verification output")
        return await super().generate_structured(prompt, schema, temperature=temperature)


@pytest.mark.asyncio
async def test_verification_agent_grounds_claims() -> None:
    """Verification agent should return verified claims with citations."""
    agent = VerificationAgent(llm_client=FakeGeminiClient())
    papers = [
        {
            "paper_id": "ss:paper-1",
            "title": "Intermittent Fasting Study",
            "abstract": "RCT showing improved insulin sensitivity under intermittent fasting.",
            "source": PaperSource.SEMANTIC_SCHOLAR.value,
        }
    ]
    chunks = [
        {
            "chunk_id": "chunk_1",
            "paper_id": "ss:paper-1",
            "text": "RCT showing improved insulin sensitivity under intermittent fasting.",
            "score": 0.92,
        }
    ]

    result = await agent.run(
        query="Does intermittent fasting improve insulin sensitivity?",
        papers=papers,
        retrieved_chunks=chunks,
    )

    assert result["verified_claims"]
    assert result["verified_claims"][0]["verdict"] == Verdict.SUPPORTED.value
    assert result["citations"]
    assert result["confidence_scores"]
    assert result["agent_log"]["confidence_score"] > 0


@pytest.mark.asyncio
async def test_verification_agent_marks_unsupported_without_chunks() -> None:
    """Claims without any paper text or chunks should be marked unsupported."""
    agent = VerificationAgent(llm_client=FakeGeminiClient())
    papers = [
        {
            "paper_id": "ss:paper-2",
            "title": "",
            "abstract": "",
            "source": PaperSource.SEMANTIC_SCHOLAR.value,
        }
    ]

    result = await agent.run(
        query="Test query",
        papers=papers,
        retrieved_chunks=[],
    )

    assert result["verified_claims"]
    assert result["verified_claims"][0]["verdict"] == Verdict.UNSUPPORTED.value


@pytest.mark.asyncio
async def test_verification_agent_synthesizes_abstract_chunks_when_missing() -> None:
    """Empty retrieved_chunks should fall back to title/abstract evidence spans."""
    agent = VerificationAgent(llm_client=FakeGeminiClient())
    papers = [
        {
            "paper_id": "ss:paper-2b",
            "title": "No Evidence Paper",
            "abstract": "A claim without indexed chunks.",
            "source": PaperSource.SEMANTIC_SCHOLAR.value,
        }
    ]

    result = await agent.run(
        query="Test query",
        papers=papers,
        retrieved_chunks=[],
    )

    assert result["verified_claims"]
    assert result["verified_claims"][0]["verdict"] == Verdict.SUPPORTED.value


@pytest.mark.asyncio
async def test_verification_agent_falls_back_on_malformed_llm_output() -> None:
    """Malformed OpenRouter JSON should not fail the verification agent."""
    agent = VerificationAgent(llm_client=BrokenVerificationClient(), max_attempts=1)
    papers = [
        {
            "paper_id": "ss:paper-3",
            "title": "Intermittent Fasting and Insulin Sensitivity",
            "abstract": "Intermittent fasting improves insulin sensitivity in adults.",
            "source": PaperSource.SEMANTIC_SCHOLAR.value,
        }
    ]
    chunks = [
        {
            "chunk_id": "chunk_3",
            "paper_id": "ss:paper-3",
            "text": "Intermittent fasting improves insulin sensitivity in adults.",
            "score": 0.8,
        }
    ]

    result = await agent.run(
        query="Does intermittent fasting improve insulin sensitivity?",
        papers=papers,
        retrieved_chunks=chunks,
    )

    assert not result.get("errors")
    assert result["verified_claims"]
    assert result["verified_claims"][0]["paper_id"] == "ss:paper-3"
    assert result["verified_claims"][0]["needs_review"] is True
