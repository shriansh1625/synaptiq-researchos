"""Executive brief agent for grounded research synthesis."""

from __future__ import annotations

import json
import uuid
from typing import Any

from app.agents.base import BaseAgent
from app.core.exceptions import AgentExecutionError, SchemaValidationError
from app.core.retry import async_retry
from app.models.enums import AgentName, BriefStatus
from app.prompts.loader import load_prompt
from app.schemas.brief import (
    BriefGapBlock,
    BriefReport,
    BriefTextBlock,
    ExecutiveBriefOutput,
)
from app.services.brief.citation_integrity import (
    build_explainability_citations,
    validate_and_sanitize_brief,
)
from app.services.llm.base import LLMClient
from app.services.llm.factory import get_llm_client


class BriefAgent(BaseAgent):
    """Synthesize an executive brief from grounded research state."""

    agent_name = AgentName.BRIEF

    def __init__(self, *, llm_client: LLMClient | None = None, max_attempts: int = 3) -> None:
        super().__init__(max_attempts=max_attempts)
        self._llm = llm_client or get_llm_client()

    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        query: str = kwargs["query"]
        verified_claims: list[dict[str, Any]] = kwargs.get("verified_claims") or []
        comparisons: dict[str, Any] = kwargs.get("comparisons") or {}
        research_gaps: list[dict[str, Any]] = kwargs.get("research_gaps") or []
        contradictions: list[dict[str, Any]] = kwargs.get("contradictions") or []
        papers: list[dict[str, Any]] = kwargs.get("papers") or []
        state_citations: list[dict[str, Any]] = kwargs.get("citations") or []
        kg_summary: dict[str, Any] = kwargs.get("kg_summary") or {}
        retry_reason: str | None = kwargs.get("retry_reason")

        prompt = load_prompt("brief").render(
            question=query,
            claims=json.dumps(verified_claims),
            comparisons=json.dumps({**comparisons, "contradictions": contradictions}),
            gaps=json.dumps(research_gaps),
            kg_summary=json.dumps(kg_summary),
            config=json.dumps(
                {"audience": "executive", "max_findings": 7, "max_words_summary": 180}
            ),
            retry_reason=json.dumps(retry_reason),
        )

        async def _call() -> ExecutiveBriefOutput:
            try:
                return await self._llm.generate_structured(prompt, ExecutiveBriefOutput)
            except SchemaValidationError as exc:
                raise AgentExecutionError(str(exc)) from exc

        try:
            output = await async_retry(_call, max_attempts=self._max_attempts)
        except (AgentExecutionError, SchemaValidationError, Exception):
            output = self._fallback_brief(
                query=query,
                verified_claims=verified_claims,
                research_gaps=research_gaps,
                contradictions=contradictions,
            )
        if not output.report.report_id:
            output.report.report_id = f"rep_{uuid.uuid4().hex[:8]}"

        output = validate_and_sanitize_brief(
            output,
            verified_claims=verified_claims,
            research_gaps=research_gaps,
        )
        explainability = build_explainability_citations(
            verified_claims=verified_claims,
            research_gaps=research_gaps,
            papers=papers,
            state_citations=state_citations,
        )
        output = output.model_copy(update={"citations": explainability})

        return {
            "executive_brief": output.model_dump(mode="json"),
            "confidence_scores": {"brief_overall": output.overall_confidence},
            "agent_log": {
                "agent_name": self.agent_name.value,
                "input_data": {
                    "query": query,
                    "claim_count": len(verified_claims),
                    "gap_count": len(research_gaps),
                },
                "output_data": output.model_dump(mode="json"),
                "confidence_score": output.overall_confidence,
                "status": output.status.value,
            },
        }

    @staticmethod
    def _fallback_brief(
        *,
        query: str,
        verified_claims: list[dict[str, Any]],
        research_gaps: list[dict[str, Any]],
        contradictions: list[dict[str, Any]],
    ) -> ExecutiveBriefOutput:
        """Build a grounded executive brief when the LLM returns malformed JSON."""
        supported_claims = [
            claim
            for claim in verified_claims
            if str(claim.get("verdict", "")).upper() in {"SUPPORTED", "PARTIALLY_SUPPORTED"}
        ]
        cited_claims = supported_claims or verified_claims
        key_findings = [
            BriefTextBlock(
                text=claim.get("text", "Verified research claim."),
                citations=[claim["claim_id"]],
            )
            for claim in cited_claims[:5]
            if claim.get("claim_id")
        ]

        gap_blocks = [
            BriefGapBlock(
                text=gap.get("description", f"Research gap in {gap.get('topic', 'the literature')}."),
                gap_id=gap["gap_id"],
            )
            for gap in research_gaps[:5]
            if gap.get("gap_id")
        ]

        future_opportunities = [
            BriefTextBlock(
                text=gap.get(
                    "actionability_note",
                    f"Prioritize follow-up research on {gap.get('topic', 'this area')}.",
                ),
                citations=[gap["gap_id"]],
            )
            for gap in research_gaps[:5]
            if gap.get("gap_id")
        ]

        contradiction_blocks = [
            BriefTextBlock(
                text=item.get("rationale", "A contradiction requires follow-up review."),
                citations=[
                    ref
                    for ref in (item.get("claim_a"), item.get("claim_b"))
                    if isinstance(ref, str) and ref
                ],
            )
            for item in contradictions[:5]
        ]
        contradiction_blocks = [block for block in contradiction_blocks if block.citations]

        recommendations = future_opportunities[:3]
        if not recommendations and key_findings:
            recommendations = [
                BriefTextBlock(
                    text=(
                        "Use the cited evidence as a starting point and broaden retrieval "
                        "before making high-stakes decisions."
                    ),
                    citations=key_findings[0].citations,
                )
            ]

        status = BriefStatus.OK if key_findings else BriefStatus.INSUFFICIENT_EVIDENCE
        confidence_values = [
            float(claim.get("confidence", 0.0))
            for claim in cited_claims
            if isinstance(claim.get("confidence"), int | float)
        ]
        overall_confidence = (
            min(sum(confidence_values) / len(confidence_values), 0.7)
            if confidence_values
            else 0.2
        )

        report = BriefReport(
            report_id=f"rep_{uuid.uuid4().hex[:8]}",
            title=f"Executive Research Brief: {query[:80]}",
            executive_summary=(
                "The analysis completed with deterministic synthesis because the LLM "
                "returned malformed brief JSON. Findings below are grounded only in "
                "verified claims and detected research gaps from the pipeline state."
            ),
            key_findings=key_findings,
            comparative_insights=[
                BriefTextBlock(
                    text=(
                        "Claims were compared conservatively using verified topics, "
                        "verdicts, and available confidence scores."
                    ),
                    citations=key_findings[0].citations,
                )
            ]
            if key_findings
            else [],
            consensus=key_findings[:2],
            contradictions=contradiction_blocks,
            research_gaps=gap_blocks,
            future_opportunities=future_opportunities,
            recommendations=recommendations,
            limitations=(
                "This fallback brief is conservative and should be reviewed before external use."
            ),
        )
        return ExecutiveBriefOutput(
            status=status,
            report=report,
            overall_confidence=overall_confidence,
            warnings=["LLM brief output failed schema validation; used deterministic fallback."],
        )
