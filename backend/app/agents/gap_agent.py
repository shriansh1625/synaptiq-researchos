"""Research gap detection agent."""

from __future__ import annotations

import json
from typing import Any

from app.agents.base import BaseAgent
from app.core.exceptions import AgentExecutionError, SchemaValidationError
from app.core.retry import async_retry
from app.models.enums import AgentName, GapType, IntelligenceStatus, RelationType
from app.prompts.loader import load_prompt
from app.schemas.intelligence import GapDetectionOutput, ResearchGapItem, VerifiedClaim
from app.services.intelligence.coverage_matrix import build_coverage_matrix, papers_meta_from_state
from app.services.llm.base import LLMClient
from app.services.llm.factory import get_llm_client


class GapAgent(BaseAgent):
    """Detect research gaps from verified claims and comparisons."""

    agent_name = AgentName.GAP

    def __init__(self, *, llm_client: LLMClient | None = None, max_attempts: int = 3) -> None:
        super().__init__(max_attempts=max_attempts)
        self._llm = llm_client or get_llm_client()

    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        query: str = kwargs["query"]
        raw_claims: list[dict[str, Any]] = kwargs.get("verified_claims") or []
        papers: list[dict[str, Any]] = kwargs.get("papers") or []
        comparisons: dict[str, Any] = kwargs.get("comparisons") or {}
        retry_reason: str | None = kwargs.get("retry_reason")

        claims = [VerifiedClaim.model_validate(item) for item in raw_claims]
        papers_meta = papers_meta_from_state(papers)
        coverage_matrix = build_coverage_matrix(claims, papers_meta)

        if not claims:
            output = GapDetectionOutput(
                status=IntelligenceStatus.INSUFFICIENT_CONTEXT,
                analysis_confidence=0.1,
                warnings=["No verified claims provided."],
            )
        else:
            prompt = load_prompt("gap").render(
                question=query,
                claims=json.dumps([claim.model_dump(mode="json") for claim in claims]),
                comparisons=json.dumps(comparisons),
                coverage_matrix=json.dumps(coverage_matrix),
                papers_meta=json.dumps(papers_meta),
                config=json.dumps(
                    {"max_gaps": 7, "current_year": 2026, "recency_window_years": 3}
                ),
                retry_reason=json.dumps(retry_reason),
            )

            async def _call() -> GapDetectionOutput:
                try:
                    return await self._llm.generate_structured(prompt, GapDetectionOutput)
                except SchemaValidationError as exc:
                    raise AgentExecutionError(str(exc)) from exc

            try:
                output = await async_retry(_call, max_attempts=self._max_attempts)
            except (AgentExecutionError, SchemaValidationError, Exception):
                output = self._fallback_gap_detection(
                    claims=claims,
                    papers=papers,
                    comparisons=comparisons,
                )

        return {
            "research_gaps": [gap.model_dump(mode="json") for gap in output.gaps],
            "agent_log": {
                "agent_name": self.agent_name.value,
                "input_data": {"query": query, "claim_count": len(claims)},
                "output_data": output.model_dump(mode="json"),
                "confidence_score": output.analysis_confidence,
                "status": "success",
            },
        }

    @staticmethod
    def _fallback_gap_detection(
        *,
        claims: list[VerifiedClaim],
        papers: list[dict[str, Any]],
        comparisons: dict[str, Any],
    ) -> GapDetectionOutput:
        """Build conservative gap records when the LLM returns malformed JSON."""
        topics = sorted({claim.topic or "general" for claim in claims}) or ["general"]
        claim_ids_by_topic = {
            topic: [claim.claim_id for claim in claims if (claim.topic or "general") == topic]
            for topic in topics
        }
        gaps: list[ResearchGapItem] = []

        for index, topic in enumerate(topics[:3], start=1):
            related_claims = claim_ids_by_topic.get(topic, [])[:5]
            gaps.append(
                ResearchGapItem(
                    gap_id=f"gap_fallback_{index}",
                    gap_type=GapType.UNDERSTUDIED,
                    topic=topic,
                    description=(
                        f"The retrieved evidence for {topic} is limited in coverage and "
                        "should be expanded before making high-confidence decisions."
                    ),
                    evidence=[
                        f"{len(related_claims)} verified claim(s) available for this topic.",
                        f"{len(papers)} paper(s) retrieved in the current session.",
                    ],
                    related_claims=related_claims,
                    impact_score=0.55,
                    actionability_note=(
                        "Run a broader search and prioritize studies with stronger methodology, "
                        "larger samples, and clearer outcome measurements."
                    ),
                )
            )

        contradiction_claims = GapAgent._contradiction_claim_ids(comparisons)
        if contradiction_claims:
            gaps.append(
                ResearchGapItem(
                    gap_id="gap_fallback_contradictions",
                    gap_type=GapType.UNRESOLVED_CONTRADICTION,
                    topic="contradictions",
                    description=(
                        "The comparative analysis found claim relationships that require "
                        "follow-up review before synthesizing a single conclusion."
                    ),
                    evidence=["Contradictory claim relationships were detected."],
                    related_claims=contradiction_claims[:6],
                    impact_score=0.7,
                    actionability_note=(
                        "Inspect the cited evidence spans for each contradictory claim pair "
                        "and compare study populations, methods, and endpoints."
                    ),
                )
            )

        return GapDetectionOutput(
            status=IntelligenceStatus.OK,
            gaps=gaps[:7],
            analysis_confidence=0.45,
            warnings=["LLM gap output failed schema validation; used deterministic fallback."],
        )

    @staticmethod
    def _contradiction_claim_ids(comparisons: dict[str, Any]) -> list[str]:
        claim_ids: list[str] = []
        for cluster in comparisons.get("clusters", []) if isinstance(comparisons, dict) else []:
            for relation in cluster.get("relations", []):
                if relation.get("relation_type") != RelationType.CONTRADICTS.value:
                    continue
                for key in ("claim_a", "claim_b"):
                    claim_id = relation.get(key)
                    if claim_id and claim_id not in claim_ids:
                        claim_ids.append(claim_id)
        return claim_ids
