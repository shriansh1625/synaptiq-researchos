"""Unit tests for PDF report generation."""

from __future__ import annotations

from pathlib import Path

from app.models.enums import BriefStatus
from app.schemas.brief import (
    BriefReport,
    BriefTextBlock,
    CitationIntegrity,
    ExecutiveBriefOutput,
    ExplainabilityCitation,
)
from app.schemas.knowledge_graph import KGSummary, KnowledgeGraphSnapshot
from app.services.reports.pdf_generator import PDFReportGenerator


def test_pdf_generator_writes_report(tmp_path: Path) -> None:
    """PDF generator should create a non-empty PDF file."""
    brief = ExecutiveBriefOutput(
        status=BriefStatus.OK,
        report=BriefReport(
            report_id="rep_1",
            title="Test Brief",
            executive_summary="Summary text.",
            key_findings=[BriefTextBlock(text="Finding.", citations=["clm_1"])],
            limitations="Limited evidence.",
        ),
        overall_confidence=0.8,
        citations=[
            ExplainabilityCitation(
                citation_id="cite:clm_1",
                claim_id="clm_1",
                title="Paper",
                text_span="Finding.",
                confidence=0.8,
            )
        ],
        citation_integrity=CitationIntegrity(),
    )
    kg = KnowledgeGraphSnapshot(summary=KGSummary(nodes_count=2, edges_count=1))
    output = tmp_path / "report.pdf"
    PDFReportGenerator().generate(
        query="Test query?",
        brief=brief,
        knowledge_graph=kg,
        papers=[{"paper_id": "ss:1", "title": "Paper"}],
        output_path=output,
    )
    assert output.exists()
    assert output.stat().st_size > 500
