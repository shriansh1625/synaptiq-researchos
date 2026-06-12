"""Fake LLM client for offline agent and graph tests."""

from __future__ import annotations

import json
import re
from typing import TypeVar

from pydantic import BaseModel

from app.models.enums import (
    BriefStatus,
    DiscoveryStatus,
    GapType,
    IntelligenceStatus,
    PaperSource,
    RelationType,
    Sufficiency,
    Verdict,
    VerificationStage,
)
from app.schemas.brief import (
    BriefGapBlock,
    BriefReport,
    BriefTextBlock,
    CitationIntegrity,
    ExecutiveBriefOutput,
)
from app.schemas.agent_io import DiscoveryOutput, DiscoveryPaperOutput
from app.schemas.intelligence import (
    ClaimCluster,
    ClaimRelation,
    ComparativeOutput,
    ExtractedClaim,
    GapDetectionOutput,
    ResearchGapItem,
    VerificationExtractOutput,
    VerificationVerifyOutput,
)
from app.schemas.intelligence import EvidenceSpanRef

T = TypeVar("T", bound=BaseModel)


def _json_after(prompt: str, label: str) -> object | None:
    """Parse the first JSON value that follows a prompt label."""
    idx = prompt.find(label)
    if idx == -1:
        return None
    start = idx + len(label)
    while start < len(prompt) and prompt[start] in " \t\r\n":
        start += 1
    try:
        value, _ = json.JSONDecoder().raw_decode(prompt, start)
        return value
    except json.JSONDecodeError:
        return None


class FakeGeminiClient:
    """Deterministic Gemini client for tests."""

    def __init__(
        self,
        response: DiscoveryOutput | None = None,
        *,
        responses: dict[type[BaseModel], BaseModel] | None = None,
    ) -> None:
        self._response = response
        self._responses = responses or {}
        self.prompts: list[str] = []

    async def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        *,
        temperature: float | None = None,
    ) -> T:
        self.prompts.append(prompt)
        if schema in self._responses:
            return schema.model_validate(self._responses[schema].model_dump())  # type: ignore[return-value]
        if self._response is not None and schema is DiscoveryOutput:
            return schema.model_validate(self._response.model_dump())  # type: ignore[return-value]

        if schema is DiscoveryOutput:
            return self._discovery_output(prompt)  # type: ignore[return-value]
        if schema is VerificationExtractOutput:
            return self._verification_extract(prompt)  # type: ignore[return-value]
        if schema is VerificationVerifyOutput:
            return self._verification_verify(prompt)  # type: ignore[return-value]
        if schema is ComparativeOutput:
            return self._comparative_output(prompt)  # type: ignore[return-value]
        if schema is GapDetectionOutput:
            return self._gap_output(prompt)  # type: ignore[return-value]
        if schema is ExecutiveBriefOutput:
            return self._brief_output(prompt)  # type: ignore[return-value]

        raise ValueError(f"Unsupported schema: {schema}")

    def _discovery_output(self, prompt: str) -> DiscoveryOutput:
        match = re.search(r"RETRIEVED CANDIDATES:\s*(\[.*\])", prompt, re.DOTALL)
        raw_candidates = match.group(1) if match else "[]"
        candidates = json.loads(raw_candidates)
        papers = [
            DiscoveryPaperOutput(
                paper_id=item["paper_id"],
                title=item["title"],
                authors=item.get("authors", []),
                year=item.get("year"),
                venue=item.get("venue"),
                doi=item.get("doi"),
                abstract=item.get("abstract", ""),
                citation_count=item.get("citation_count", 0),
                source=PaperSource(item.get("source", "semantic_scholar")),
                url=item.get("url"),
                relevance_score=0.9,
                relevance_reason="Directly relevant to the query.",
            )
            for item in candidates[:2]
        ]
        return DiscoveryOutput(
            status=DiscoveryStatus.OK if papers else DiscoveryStatus.NO_CANDIDATES,
            query_plan=["test sub-query"],
            papers=papers,
            sources_used=[PaperSource.SEMANTIC_SCHOLAR],
            sufficiency=Sufficiency.INSUFFICIENT if len(papers) < 8 else Sufficiency.SUFFICIENT,
            discovery_confidence=0.8 if papers else 0.0,
        )

    def _verification_extract(self, prompt: str) -> VerificationExtractOutput:
        paper_match = re.search(r"PAPER ID:\s*(\S+)", prompt)
        paper_id = paper_match.group(1) if paper_match else "ss:paper-1"
        text_match = re.search(r"PAPER TEXT:\s*(.+?)(?:\n\nCLAIM:|\Z)", prompt, re.DOTALL)
        paper_text = (text_match.group(1) if text_match else "Sample claim text.").strip()
        sentence = paper_text.split(".")[0].strip() or paper_text[:120]
        return VerificationExtractOutput(
            stage=VerificationStage.EXTRACT,
            paper_id=paper_id,
            claims=[
                ExtractedClaim(
                    claim_id=f"clm_{paper_id.replace(':', '_')}_0",
                    paper_id=paper_id,
                    text=sentence,
                    topic="insulin_sensitivity",
                )
            ],
        )

    def _verification_verify(self, prompt: str) -> VerificationVerifyOutput:
        claim = _json_after(prompt, "CLAIM:") or {}
        spans = _json_after(prompt, "EVIDENCE SPANS:") or []
        if not isinstance(claim, dict):
            claim = {}
        if not isinstance(spans, list):
            spans = []
        supporting: list[EvidenceSpanRef] = []
        if spans:
            first = spans[0]
            supporting.append(
                EvidenceSpanRef(
                    span_id=first["span_id"],
                    chunk_id=first.get("chunk_id", first["span_id"]),
                    score=float(first.get("score", 0.9)),
                )
            )
        verdict = Verdict.SUPPORTED if supporting else Verdict.UNSUPPORTED
        return VerificationVerifyOutput(
            stage=VerificationStage.VERIFY,
            status=IntelligenceStatus.OK if supporting else IntelligenceStatus.NO_EVIDENCE,
            claim_id=claim.get("claim_id", "clm_test"),
            paper_id=claim.get("paper_id", "ss:paper-1"),
            text=claim.get("text", "test claim"),
            verdict=verdict,
            confidence=0.85 if supporting else 0.8,
            supporting_spans=supporting,
            reason="grounded in evidence" if supporting else "no_evidence",
            topic=claim.get("topic", "general"),
        )

    def _comparative_output(self, prompt: str) -> ComparativeOutput:
        raw_claims = _json_after(prompt, "VERIFIED CLAIMS:") or []
        if not isinstance(raw_claims, list):
            raw_claims = []
        claim_ids = [item["claim_id"] for item in raw_claims[:2]]
        if len(claim_ids) < 2:
            return ComparativeOutput(status=IntelligenceStatus.INSUFFICIENT_CLAIMS)
        return ComparativeOutput(
            status=IntelligenceStatus.OK,
            clusters=[
                ClaimCluster(
                    cluster_id="cluster_1",
                    topic="insulin_sensitivity",
                    member_claim_ids=claim_ids,
                    cluster_confidence=0.8,
                    relations=[
                        ClaimRelation(
                            relation_id="rel_1",
                            relation_type=RelationType.AGREES,
                            claim_a=claim_ids[0],
                            claim_b=claim_ids[1],
                            dimension="findings",
                            rationale="Both claims support improved insulin sensitivity.",
                            confidence=0.75,
                        )
                    ],
                )
            ],
            contradictions_count=0,
        )

    def _brief_output(self, prompt: str) -> ExecutiveBriefOutput:
        claims = _json_after(prompt, "VERIFIED CLAIMS:") or []
        gaps = _json_after(prompt, "RESEARCH GAPS:") or []
        if not isinstance(claims, list):
            claims = []
        if not isinstance(gaps, list):
            gaps = []
        supported = [item for item in claims if item.get("verdict") == Verdict.SUPPORTED.value]
        claim_id = supported[0]["claim_id"] if supported else None
        gap_id = gaps[0]["gap_id"] if gaps else "gap_1"
        status = BriefStatus.OK if supported else BriefStatus.INSUFFICIENT_EVIDENCE
        findings = (
            [BriefTextBlock(text=supported[0]["text"], citations=[claim_id])]
            if claim_id
            else []
        )
        return ExecutiveBriefOutput(
            status=status,
            report=BriefReport(
                report_id="rep_test",
                title="SynaptiQ Executive Research Brief",
                executive_summary="Evidence synthesis for the research question.",
                key_findings=findings,
                comparative_insights=findings,
                research_gaps=[BriefGapBlock(text="Gap in long-term evidence.", gap_id=gap_id)],
                future_opportunities=[
                    BriefTextBlock(text="Conduct longer RCTs.", citations=[gap_id])
                ],
                recommendations=[
                    BriefTextBlock(text="Expand evidence base.", citations=[gap_id])
                ],
                limitations="Small evidence base.",
            ),
            overall_confidence=0.7 if supported else 0.2,
            citation_integrity=CitationIntegrity(checked=True, all_citations_valid=True),
        )

    def _gap_output(self, prompt: str) -> GapDetectionOutput:
        return GapDetectionOutput(
            status=IntelligenceStatus.OK,
            analysis_confidence=0.72,
            gaps=[
                ResearchGapItem(
                    gap_id="gap_1",
                    gap_type=GapType.UNDERSTUDIED,
                    topic="long_term_outcomes",
                    description="Limited long-term RCT evidence on fasting and insulin sensitivity.",
                    evidence=["coverage_matrix shows low count for long_term_outcomes"],
                    related_claims=[],
                    impact_score=0.7,
                    actionability_note="Prioritize multi-year follow-up studies.",
                )
            ],
        )
