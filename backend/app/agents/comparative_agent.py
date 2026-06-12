"""Comparative analysis agent."""

from __future__ import annotations

import json
from typing import Any

from app.agents.base import BaseAgent
from app.core.exceptions import AgentExecutionError, SchemaValidationError
from app.core.retry import async_retry
from app.models.enums import AgentName, IntelligenceStatus, RelationType
from app.prompts.loader import load_prompt
from app.schemas.intelligence import (
    ClaimCluster,
    ClaimRelation,
    ComparativeOutput,
    ContradictionRecord,
    VerifiedClaim,
)
from app.services.llm.base import LLMClient
from app.services.llm.factory import get_llm_client


class ComparativeAgent(BaseAgent):
    """Compare verified claims across papers."""

    agent_name = AgentName.COMPARATIVE

    def __init__(self, *, llm_client: LLMClient | None = None, max_attempts: int = 3) -> None:
        super().__init__(max_attempts=max_attempts)
        self._llm = llm_client or get_llm_client()

    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        query: str = kwargs["query"]
        raw_claims: list[dict[str, Any]] = kwargs.get("verified_claims") or []
        retry_reason: str | None = kwargs.get("retry_reason")
        claims = [VerifiedClaim.model_validate(item) for item in raw_claims]

        if len(claims) < 2:
            output = ComparativeOutput(
                status=IntelligenceStatus.INSUFFICIENT_CLAIMS,
                warnings=["Fewer than two verified claims available for comparison."],
            )
        else:
            prompt = load_prompt("comparative").render(
                question=query,
                claims=json.dumps([claim.model_dump(mode="json") for claim in claims]),
                clusters_hint="[]",
                config=json.dumps(
                    {
                        "contradiction_threshold": 0.6,
                        "min_pair_confidence": 0.6,
                        "max_relations": 50,
                    }
                ),
                retry_reason=json.dumps(retry_reason),
            )

            async def _call() -> ComparativeOutput:
                try:
                    return await self._llm.generate_structured(prompt, ComparativeOutput)
                except SchemaValidationError as exc:
                    raise AgentExecutionError(str(exc)) from exc

            try:
                output = await async_retry(_call, max_attempts=self._max_attempts)
                self._validate_relations(output, claims)
            except (AgentExecutionError, SchemaValidationError, Exception):
                output = self._fallback_comparative_output(claims)

        contradictions = self._extract_contradictions(output)
        avg_confidence = (
            sum(cluster.cluster_confidence for cluster in output.clusters) / len(output.clusters)
            if output.clusters
            else 0.0
        )

        return {
            "comparisons": output.model_dump(mode="json"),
            "contradictions": [item.model_dump(mode="json") for item in contradictions],
            "agent_log": {
                "agent_name": self.agent_name.value,
                "input_data": {"query": query, "claim_count": len(claims)},
                "output_data": output.model_dump(mode="json"),
                "confidence_score": avg_confidence,
                "status": "success",
            },
        }

    @staticmethod
    def _validate_relations(output: ComparativeOutput, claims: list[VerifiedClaim]) -> None:
        claim_ids = {claim.claim_id for claim in claims}
        for cluster in output.clusters:
            for relation in cluster.relations:
                if relation.claim_a not in claim_ids or relation.claim_b not in claim_ids:
                    raise AgentExecutionError("Relation references unknown claim_id")
                if relation.confidence > min(
                    next(c.confidence for c in claims if c.claim_id == relation.claim_a),
                    next(c.confidence for c in claims if c.claim_id == relation.claim_b),
                ) + 0.01:
                    raise AgentExecutionError("Relation confidence exceeds claim confidences")

    @staticmethod
    def _extract_contradictions(output: ComparativeOutput) -> list[ContradictionRecord]:
        records: list[ContradictionRecord] = []
        for cluster in output.clusters:
            for relation in cluster.relations:
                if relation.relation_type != RelationType.CONTRADICTS:
                    continue
                records.append(
                    ContradictionRecord(
                        relation_id=relation.relation_id,
                        claim_a=relation.claim_a,
                        claim_b=relation.claim_b,
                        topic=cluster.topic,
                        rationale=relation.rationale,
                        confidence=relation.confidence,
                    )
                )
        return records

    @staticmethod
    def _fallback_comparative_output(claims: list[VerifiedClaim]) -> ComparativeOutput:
        """Build conservative comparison clusters when LLM JSON is malformed."""
        claims_by_topic: dict[str, list[VerifiedClaim]] = {}
        for claim in claims:
            claims_by_topic.setdefault(claim.topic or "general", []).append(claim)

        clusters: list[ClaimCluster] = []
        for cluster_index, (topic, topic_claims) in enumerate(claims_by_topic.items(), start=1):
            relations: list[ClaimRelation] = []
            for rel_index, (left, right) in enumerate(
                zip(topic_claims, topic_claims[1:], strict=False),
                start=1,
            ):
                relation_type = (
                    RelationType.AGREES
                    if left.verdict == right.verdict
                    else RelationType.INCONCLUSIVE
                )
                relations.append(
                    ClaimRelation(
                        relation_id=f"rel_fallback_{cluster_index}_{rel_index}",
                        relation_type=relation_type,
                        claim_a=left.claim_id,
                        claim_b=right.claim_id,
                        dimension="findings",
                        rationale=(
                            "Fallback comparison grouped claims by topic and compared "
                            "verification verdicts conservatively."
                        ),
                        confidence=min(left.confidence, right.confidence, 0.65),
                        needs_review=True,
                    )
                )

            cluster_confidence = (
                sum(claim.confidence for claim in topic_claims) / len(topic_claims)
                if topic_claims
                else 0.0
            )
            clusters.append(
                ClaimCluster(
                    cluster_id=f"cluster_fallback_{cluster_index}",
                    topic=topic,
                    member_claim_ids=[claim.claim_id for claim in topic_claims],
                    cluster_confidence=min(cluster_confidence, 0.7),
                    relations=relations,
                )
            )

        return ComparativeOutput(
            status=IntelligenceStatus.OK,
            clusters=clusters,
            contradictions_count=0,
            warnings=["LLM comparative output failed schema validation; used deterministic fallback."],
        )
