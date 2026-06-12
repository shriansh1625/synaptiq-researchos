"""Deterministic citation integrity validation for executive briefs."""

from __future__ import annotations

from app.models.enums import BriefStatus, Verdict
from app.schemas.brief import (
    BriefGapBlock,
    BriefReport,
    BriefTextBlock,
    CitationIntegrity,
    ExecutiveBriefOutput,
    ExplainabilityCitation,
)


def _valid_claim_ids(claims: list[dict]) -> set[str]:
    return {claim["claim_id"] for claim in claims}


def _valid_gap_ids(gaps: list[dict]) -> set[str]:
    return {gap["gap_id"] for gap in gaps}


def _filter_text_blocks(
    blocks: list[BriefTextBlock],
    claim_ids: set[str],
    gap_ids: set[str],
) -> tuple[list[BriefTextBlock], int]:
    """Keep only blocks whose citations reference valid ids."""
    kept: list[BriefTextBlock] = []
    removed = 0
    for block in blocks:
        valid_citations = [
            ref
            for ref in block.citations
            if ref in claim_ids or ref in gap_ids
        ]
        if block.text.strip() and valid_citations:
            kept.append(BriefTextBlock(text=block.text, citations=valid_citations))
        elif block.text.strip():
            removed += 1
    return kept, removed


def _filter_gap_blocks(
    blocks: list[BriefGapBlock],
    gap_ids: set[str],
) -> tuple[list[BriefGapBlock], int]:
    kept: list[BriefGapBlock] = []
    removed = 0
    for block in blocks:
        if block.gap_id in gap_ids and block.text.strip():
            kept.append(block)
        elif block.text.strip():
            removed += 1
    return kept, removed


def build_explainability_citations(
    *,
    verified_claims: list[dict],
    research_gaps: list[dict],
    papers: list[dict],
    state_citations: list[dict],
) -> list[ExplainabilityCitation]:
    """Build explainability citations from grounded state artifacts."""
    paper_titles = {paper["paper_id"]: paper.get("title", "") for paper in papers}
    citations: list[ExplainabilityCitation] = []

    for claim in verified_claims:
        citations.append(
            ExplainabilityCitation(
                citation_id=f"cite:{claim['claim_id']}",
                claim_id=claim["claim_id"],
                paper_id=claim.get("paper_id"),
                title=paper_titles.get(claim.get("paper_id", ""), ""),
                text_span=claim.get("text", "")[:240],
                confidence=float(claim.get("confidence", 0.0)),
                source=claim.get("paper_id", ""),
                verdict=str(claim.get("verdict", "")),
                reasoning=claim.get("reason", ""),
            )
        )

    for gap in research_gaps:
        citations.append(
            ExplainabilityCitation(
                citation_id=f"cite:{gap['gap_id']}",
                gap_id=gap["gap_id"],
                title=gap.get("topic", ""),
                text_span=gap.get("description", "")[:240],
                confidence=float(gap.get("impact_score", 0.0)),
                reasoning=gap.get("actionability_note", ""),
            )
        )

    for item in state_citations:
        citations.append(
            ExplainabilityCitation(
                citation_id=item.get("citation_id", ""),
                claim_id=None,
                paper_id=item.get("paper_id"),
                title=item.get("title", ""),
                text_span=item.get("text_span", "")[:240],
                confidence=0.0,
                source=str(item.get("source", "")),
                reasoning="retrieved_evidence_span",
            )
        )
    return citations


def validate_and_sanitize_brief(
    output: ExecutiveBriefOutput,
    *,
    verified_claims: list[dict],
    research_gaps: list[dict],
) -> ExecutiveBriefOutput:
    """Validate citations and strip hallucinated references."""
    claim_ids = _valid_claim_ids(verified_claims)
    gap_ids = _valid_gap_ids(research_gaps)
    removed = 0

    report = output.report
    key_findings, n = _filter_text_blocks(report.key_findings, claim_ids, gap_ids)
    removed += n
    comparative_insights, n = _filter_text_blocks(report.comparative_insights, claim_ids, gap_ids)
    removed += n
    consensus, n = _filter_text_blocks(report.consensus, claim_ids, gap_ids)
    removed += n
    contradictions, n = _filter_text_blocks(report.contradictions, claim_ids, gap_ids)
    removed += n
    future_opportunities, n = _filter_text_blocks(report.future_opportunities, claim_ids, gap_ids)
    removed += n
    recommendations, n = _filter_text_blocks(report.recommendations, claim_ids, gap_ids)
    removed += n
    research_gaps, n = _filter_gap_blocks(report.research_gaps, gap_ids)
    removed += n

    supported_count = sum(
        1 for claim in verified_claims if claim.get("verdict") == Verdict.SUPPORTED.value
    )
    all_valid = removed == 0
    status = output.status
    if supported_count == 0 and status == BriefStatus.OK:
        status = BriefStatus.INSUFFICIENT_EVIDENCE

    sanitized_report = report.model_copy(
        update={
            "key_findings": key_findings,
            "comparative_insights": comparative_insights,
            "consensus": consensus,
            "contradictions": contradictions,
            "research_gaps": research_gaps,
            "future_opportunities": future_opportunities,
            "recommendations": recommendations,
        }
    )
    return output.model_copy(
        update={
            "status": status,
            "report": sanitized_report,
            "citation_integrity": CitationIntegrity(
                checked=True,
                all_citations_valid=all_valid,
                uncited_removed=removed,
            ),
        }
    )
