"""Verification agent for claim-level grounding."""

from __future__ import annotations

import json
import re
from typing import Any

from app.agents.base import BaseAgent
from app.core.exceptions import AgentExecutionError, SchemaValidationError
from app.core.retry import async_retry
from app.models.enums import AgentName, IntelligenceStatus, PaperSource, Verdict, VerificationStage
from app.prompts.loader import load_prompt
from app.schemas.common import Citation
from app.schemas.intelligence import (
    EvidenceSpanRef,
    ExtractedClaim,
    VerificationExtractOutput,
    VerificationVerifyOutput,
    VerifiedClaim,
)
from app.services.llm.base import LLMClient
from app.services.llm.factory import get_llm_client


class VerificationAgent(BaseAgent):
    """Extract and verify atomic claims against retrieved evidence."""

    agent_name = AgentName.VERIFICATION

    def __init__(
        self,
        *,
        llm_client: LLMClient | None = None,
        max_claims_per_paper: int = 5,
        max_attempts: int = 3,
    ) -> None:
        super().__init__(max_attempts=max_attempts)
        self._llm = llm_client or get_llm_client()
        self._max_claims_per_paper = max_claims_per_paper

    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        query: str = kwargs["query"]
        papers: list[dict[str, Any]] = kwargs.get("papers") or []
        chunks: list[dict[str, Any]] = kwargs.get("retrieved_chunks") or []
        retry_reason: str | None = kwargs.get("retry_reason")

        verified_claims: list[VerifiedClaim] = []
        citations: list[Citation] = []
        confidence_scores: dict[str, float] = {}

        chunks_by_paper: dict[str, list[dict[str, Any]]] = {}
        for chunk in chunks:
            chunks_by_paper.setdefault(chunk["paper_id"], []).append(chunk)

        for paper in papers:
            paper_id = paper["paper_id"]
            if not chunks_by_paper.get(paper_id):
                abstract_text = f"{paper.get('title', '')}. {paper.get('abstract', '')}".strip()
                if abstract_text:
                    chunks_by_paper[paper_id] = [
                        {
                            "span_id": f"sp_{paper_id}_abstract",
                            "chunk_id": f"chunk_{paper_id}_0",
                            "paper_id": paper_id,
                            "text": abstract_text,
                            "score": 0.82,
                        }
                    ]

        for paper in papers:
            paper_id = paper["paper_id"]
            paper_text = f"{paper.get('title', '')}\n\n{paper.get('abstract', '')}".strip()
            try:
                extracted = await self._extract_claims(
                    query=query,
                    paper_id=paper_id,
                    paper_text=paper_text,
                    retry_reason=retry_reason,
                )
            except Exception as exc:  # noqa: BLE001
                extracted = VerificationExtractOutput(
                    paper_id=paper_id,
                    claims=self._heuristic_extract_claims(paper_id, paper_text),
                    warnings=[f"Claim extraction fallback: {exc}"],
                )
            evidence_spans = self._build_evidence_spans(chunks_by_paper.get(paper_id, []))

            for claim in extracted.claims[: self._max_claims_per_paper]:
                try:
                    verified = await self._verify_claim(
                        query=query,
                        claim=claim,
                        evidence_spans=evidence_spans,
                        retry_reason=retry_reason,
                    )
                    self._validate_span_grounding(verified, evidence_spans)
                except Exception as exc:  # noqa: BLE001
                    verified = self._heuristic_verify_claim(claim, evidence_spans)
                    verified = verified.model_copy(
                        update={"reason": f"{verified.reason}; fallback={exc}"},
                    )
                claim_model = VerifiedClaim(
                    claim_id=verified.claim_id,
                    paper_id=verified.paper_id,
                    text=verified.text,
                    topic=verified.topic,
                    verdict=verified.verdict,
                    confidence=verified.confidence,
                    supporting_spans=verified.supporting_spans,
                    reason=verified.reason,
                    needs_review=verified.needs_review,
                )
                verified_claims.append(claim_model)
                confidence_scores[claim_model.claim_id] = claim_model.confidence
                for span in verified.supporting_spans:
                    raw_source = paper.get("source", PaperSource.SEMANTIC_SCHOLAR)
                    source = (
                        raw_source
                        if isinstance(raw_source, PaperSource)
                        else PaperSource(str(raw_source))
                    )
                    citations.append(
                        Citation(
                            citation_id=f"cite:{span.span_id}",
                            paper_id=verified.paper_id,
                            chunk_id=span.chunk_id,
                            title=paper.get("title", ""),
                            text_span=verified.text[:240],
                            source=source,
                            doi=paper.get("doi"),
                            url=paper.get("url"),
                        )
                    )

        avg_confidence = (
            sum(claim.confidence for claim in verified_claims) / len(verified_claims)
            if verified_claims
            else 0.0
        )
        unsupported_ratio = (
            sum(1 for claim in verified_claims if claim.verdict == Verdict.UNSUPPORTED)
            / len(verified_claims)
            if verified_claims
            else 1.0
        )

        return {
            "verified_claims": [claim.model_dump(mode="json") for claim in verified_claims],
            "citations": [citation.model_dump(mode="json") for citation in citations],
            "confidence_scores": confidence_scores,
            "control": {
                "current_agent": self.agent_name.value,
                "avg_confidence": round(avg_confidence, 4),
                "unsupported_ratio": round(unsupported_ratio, 4),
            },
            "agent_log": {
                "agent_name": self.agent_name.value,
                "input_data": {"query": query, "paper_count": len(papers)},
                "output_data": {
                    "verified_claim_count": len(verified_claims),
                    "avg_confidence": avg_confidence,
                },
                "confidence_score": avg_confidence,
                "status": "success",
            },
        }

    async def _extract_claims(
        self,
        *,
        query: str,
        paper_id: str,
        paper_text: str,
        retry_reason: str | None,
    ) -> VerificationExtractOutput:
        prompt = load_prompt("verification").render(
            stage=VerificationStage.EXTRACT.value,
            question=query,
            paper_id=paper_id,
            paper_text=paper_text,
            claim="{}",
            evidence_spans="[]",
            max_claims_per_paper=str(self._max_claims_per_paper),
            retry_reason=json.dumps(retry_reason),
        )

        async def _call() -> VerificationExtractOutput:
            try:
                return await self._llm.generate_structured(prompt, VerificationExtractOutput)
            except SchemaValidationError as exc:
                raise AgentExecutionError(str(exc)) from exc

        try:
            result = await async_retry(_call, max_attempts=self._max_attempts)
        except (AgentExecutionError, SchemaValidationError):
            result = VerificationExtractOutput(
                paper_id=paper_id,
                claims=self._heuristic_extract_claims(paper_id, paper_text),
                warnings=["LLM extraction unavailable; used deterministic fallback."],
            )
        if not result.claims:
            result.claims = self._heuristic_extract_claims(paper_id, paper_text)
        result.paper_id = result.paper_id or paper_id
        result.claims = [
            claim.model_copy(update={"paper_id": claim.paper_id or paper_id})
            for claim in result.claims
        ]
        return result

    async def _verify_claim(
        self,
        *,
        query: str,
        claim: ExtractedClaim,
        evidence_spans: list[dict[str, Any]],
        retry_reason: str | None,
    ) -> VerificationVerifyOutput:
        if not evidence_spans:
            return VerificationVerifyOutput(
                status=IntelligenceStatus.NO_EVIDENCE,
                claim_id=claim.claim_id,
                paper_id=claim.paper_id,
                text=claim.text,
                verdict=Verdict.UNSUPPORTED,
                confidence=0.8,
                reason="no_evidence: no spans available for this paper",
                topic=claim.topic,
            )

        prompt = load_prompt("verification").render(
            stage=VerificationStage.VERIFY.value,
            question=query,
            paper_id=claim.paper_id,
            paper_text="",
            claim=json.dumps(claim.model_dump(mode="json")),
            evidence_spans=json.dumps(evidence_spans),
            max_claims_per_paper=str(self._max_claims_per_paper),
            retry_reason=json.dumps(retry_reason),
        )

        async def _call() -> VerificationVerifyOutput:
            try:
                return await self._llm.generate_structured(prompt, VerificationVerifyOutput)
            except SchemaValidationError as exc:
                raise AgentExecutionError(str(exc)) from exc

        try:
            return await async_retry(_call, max_attempts=self._max_attempts)
        except (AgentExecutionError, SchemaValidationError):
            return self._heuristic_verify_claim(claim, evidence_spans)

    @staticmethod
    def _build_evidence_spans(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "span_id": chunk.get("chunk_id", f"sp_{index}"),
                "chunk_id": chunk.get("chunk_id", ""),
                "paper_id": chunk.get("paper_id", ""),
                "text": chunk.get("text", ""),
                "score": chunk.get("score", 0.0),
            }
            for index, chunk in enumerate(chunks)
        ]

    @staticmethod
    def _heuristic_extract_claims(paper_id: str, paper_text: str) -> list[ExtractedClaim]:
        sentences = [part.strip() for part in re.split(r"[.!?]+", paper_text) if part.strip()]
        claims: list[ExtractedClaim] = []
        for index, sentence in enumerate(sentences[:3]):
            if len(sentence) < 20:
                continue
            claims.append(
                ExtractedClaim(
                    claim_id=f"clm_{paper_id.replace(':', '_')}_{index}",
                    paper_id=paper_id,
                    text=sentence,
                    topic="general",
                )
            )
        return claims

    @staticmethod
    def _heuristic_verify_claim(
        claim: ExtractedClaim,
        evidence_spans: list[dict[str, Any]],
    ) -> VerificationVerifyOutput:
        """Conservative fallback verifier grounded only in retrieved spans."""
        claim_terms = set(re.findall(r"[a-z0-9]+", claim.text.lower()))
        claim_terms = {term for term in claim_terms if len(term) > 3}
        best_span: dict[str, Any] | None = None
        best_overlap = 0
        for span in evidence_spans:
            span_terms = set(re.findall(r"[a-z0-9]+", str(span.get("text", "")).lower()))
            overlap = len(claim_terms & span_terms)
            if overlap > best_overlap:
                best_overlap = overlap
                best_span = span

        span_text = str(best_span.get("text", "")) if best_span else ""
        claim_lower = claim.text.lower().strip()
        if claim_lower and claim_lower in span_text.lower():
            best_overlap = max(best_overlap, 5)

        if best_span is None or best_overlap < 2:
            return VerificationVerifyOutput(
                status=IntelligenceStatus.CLAIM_ERROR,
                claim_id=claim.claim_id,
                paper_id=claim.paper_id,
                text=claim.text,
                verdict=Verdict.UNSUPPORTED,
                confidence=0.65,
                reason="fallback_verifier: insufficient lexical overlap with retrieved evidence",
                topic=claim.topic,
                needs_review=True,
            )

        score = float(best_span.get("score", 0.6) or 0.6)
        verdict = Verdict.SUPPORTED if best_overlap >= 5 else Verdict.PARTIALLY_SUPPORTED
        return VerificationVerifyOutput(
            status=IntelligenceStatus.OK,
            claim_id=claim.claim_id,
            paper_id=claim.paper_id,
            text=claim.text,
            verdict=verdict,
            confidence=min(max(score, 0.55), 0.85 if verdict == Verdict.SUPPORTED else 0.75),
            supporting_spans=[
                EvidenceSpanRef(
                    span_id=str(best_span.get("span_id", "")),
                    chunk_id=str(best_span.get("chunk_id", "")),
                    score=min(max(score, 0.0), 1.0),
                )
            ],
            reason="fallback_verifier: claim overlaps with retrieved evidence span; needs review",
            topic=claim.topic,
            needs_review=True,
        )

    @staticmethod
    def _validate_span_grounding(
        verified: VerificationVerifyOutput,
        evidence_spans: list[dict[str, Any]],
    ) -> None:
        allowed = {span["span_id"] for span in evidence_spans}
        for span in verified.supporting_spans:
            if span.span_id not in allowed:
                raise AgentExecutionError(f"Unknown span cited: {span.span_id}")
        if not verified.supporting_spans and verified.verdict != Verdict.UNSUPPORTED:
            raise AgentExecutionError("Non-unsupported verdict requires supporting spans")
