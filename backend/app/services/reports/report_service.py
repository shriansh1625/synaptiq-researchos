"""Orchestrate executive report persistence and PDF generation."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.runtime_paths import get_reports_dir
from app.database.models.executive_report import ExecutiveReport
from app.database.repositories.executive_report_repository import ExecutiveReportRepository
from app.database.repositories.research_session_repository import ResearchSessionRepository
from app.schemas.brief import (
    BriefGapBlock,
    BriefReport,
    BriefTextBlock,
    ExecutiveBriefOutput,
    ExplainabilityCitation,
)
from app.schemas.knowledge_graph import KGSummary, KnowledgeGraphSnapshot
from app.services.reports.pdf_generator import PDFReportGenerator


class ReportService:
    """Persist executive reports and generate PDF artifacts."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        reports_dir: Path | None = None,
        pdf_generator: PDFReportGenerator | None = None,
    ) -> None:
        self._session = session
        self._reports_dir = reports_dir or get_reports_dir()
        self._pdf_generator = pdf_generator or PDFReportGenerator()
        self._repo = ExecutiveReportRepository(session)

    async def create_report(
        self,
        *,
        session_id: uuid.UUID,
        query: str,
        brief_payload: dict[str, Any],
        papers: list[dict[str, Any]],
        knowledge_graph: dict[str, Any],
    ) -> tuple[uuid.UUID, Path]:
        """Store structured report data and generate a PDF."""
        brief = ExecutiveBriefOutput.model_validate(brief_payload)
        kg = KnowledgeGraphSnapshot.model_validate(knowledge_graph)
        report_id = uuid.uuid4()
        pdf_path = self._reports_dir / f"{report_id}.pdf"

        self._pdf_generator.generate(
            query=query,
            brief=brief,
            knowledge_graph=kg,
            papers=papers,
            output_path=pdf_path,
        )

        recommendations = {
            "report_id": str(report_id),
            "title": brief.report.title,
            "key_findings": [item.model_dump(mode="json") for item in brief.report.key_findings],
            "comparative_insights": [
                item.model_dump(mode="json") for item in brief.report.comparative_insights
            ],
            "contradictions": [item.model_dump(mode="json") for item in brief.report.contradictions],
            "research_gaps": [item.model_dump(mode="json") for item in brief.report.research_gaps],
            "future_opportunities": [
                item.model_dump(mode="json") for item in brief.report.future_opportunities
            ],
            "recommendations": [item.model_dump(mode="json") for item in brief.report.recommendations],
            "limitations": brief.report.limitations,
            "overall_confidence": brief.overall_confidence,
            "pdf_path": str(pdf_path),
            "knowledge_graph_summary": kg.summary.model_dump(mode="json"),
        }
        citations = [item.model_dump(mode="json") for item in brief.citations]

        await self._repo.create(
            report_id=report_id,
            session_id=session_id,
            summary=brief.report.executive_summary,
            recommendations=recommendations,
            citations=citations,
        )

        try:
            from app.services.storage.azure_blob import upload_artifact

            blob_url = upload_artifact(
                pdf_path,
                blob_name=f"reports/{report_id}.pdf",
            )
            if blob_url:
                recommendations["azure_blob_url"] = blob_url
        except Exception:
            pass

        return report_id, pdf_path

    @staticmethod
    def brief_from_stored_report(report: ExecutiveReport) -> ExecutiveBriefOutput:
        """Rebuild brief output from persisted report rows."""
        rec = report.recommendations or {}
        brief_report = BriefReport(
            report_id=str(report.id),
            title=str(rec.get("title") or "SynaptiQ Research Brief"),
            executive_summary=report.summary or "",
            key_findings=[BriefTextBlock.model_validate(item) for item in rec.get("key_findings", [])],
            comparative_insights=[
                BriefTextBlock.model_validate(item) for item in rec.get("comparative_insights", [])
            ],
            consensus=[BriefTextBlock.model_validate(item) for item in rec.get("consensus", [])],
            contradictions=[BriefTextBlock.model_validate(item) for item in rec.get("contradictions", [])],
            research_gaps=[BriefGapBlock.model_validate(item) for item in rec.get("research_gaps", [])],
            future_opportunities=[
                BriefTextBlock.model_validate(item) for item in rec.get("future_opportunities", [])
            ],
            recommendations=[
                BriefTextBlock.model_validate(item) for item in rec.get("recommendations", [])
            ],
            limitations=str(rec.get("limitations") or ""),
        )
        citations = [
            ExplainabilityCitation.model_validate(item) for item in (report.citations or [])
        ]
        return ExecutiveBriefOutput(
            report=brief_report,
            overall_confidence=float(rec.get("overall_confidence", 0.0)),
            citations=citations,
        )

    @staticmethod
    def knowledge_graph_from_stored_report(report: ExecutiveReport) -> KnowledgeGraphSnapshot:
        """Rebuild a minimal knowledge graph snapshot for PDF rendering."""
        rec = report.recommendations or {}
        summary_payload = rec.get("knowledge_graph_summary") or {}
        summary = KGSummary.model_validate(summary_payload)
        return KnowledgeGraphSnapshot(summary=summary)

    def resolve_pdf_path(self, report_id: uuid.UUID, recommendations: dict[str, Any] | None) -> Path:
        """Return the expected on-disk PDF path for a report."""
        stored = Path((recommendations or {}).get("pdf_path", ""))
        if stored.is_file():
            return stored
        fallback = self._reports_dir / f"{report_id}.pdf"
        return fallback

    async def ensure_pdf(
        self,
        report: ExecutiveReport,
        *,
        query: str | None = None,
    ) -> Path:
        """Return an existing PDF path or regenerate one from stored report data."""
        pdf_path = self.resolve_pdf_path(report.id, report.recommendations)
        if pdf_path.is_file():
            return pdf_path

        resolved_query = query
        if not resolved_query:
            session = await ResearchSessionRepository(self._session).get_by_id(report.session_id)
            resolved_query = session.query if session else "Research intelligence brief"

        brief = self.brief_from_stored_report(report)
        kg = self.knowledge_graph_from_stored_report(report)
        pdf_path = self._reports_dir / f"{report.id}.pdf"
        self._pdf_generator.generate(
            query=resolved_query,
            brief=brief,
            knowledge_graph=kg,
            papers=[],
            output_path=pdf_path,
        )
        return pdf_path
