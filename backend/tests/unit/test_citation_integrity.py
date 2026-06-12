"""Unit tests for brief citation integrity validation."""

from __future__ import annotations

from app.models.enums import BriefStatus
from app.schemas.brief import (
    BriefReport,
    BriefTextBlock,
    CitationIntegrity,
    ExecutiveBriefOutput,
)
from app.services.brief.citation_integrity import validate_and_sanitize_brief


def test_validate_and_sanitize_brief_strips_invalid_citations() -> None:
    """Invalid claim references should be removed."""
    output = ExecutiveBriefOutput(
        status=BriefStatus.OK,
        report=BriefReport(
            report_id="rep_1",
            title="Brief",
            executive_summary="Summary",
            key_findings=[BriefTextBlock(text="Bad finding", citations=["clm_missing"])],
        ),
        overall_confidence=0.5,
        citation_integrity=CitationIntegrity(),
    )
    sanitized = validate_and_sanitize_brief(
        output,
        verified_claims=[{"claim_id": "clm_valid", "verdict": "SUPPORTED"}],
        research_gaps=[],
    )
    assert sanitized.report.key_findings == []
    assert sanitized.citation_integrity.uncited_removed == 1
