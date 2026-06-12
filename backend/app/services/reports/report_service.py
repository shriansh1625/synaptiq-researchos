"""Orchestrate executive report persistence and PDF generation."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.runtime_paths import get_reports_dir
from app.database.repositories.executive_report_repository import ExecutiveReportRepository
from app.schemas.brief import ExecutiveBriefOutput
from app.schemas.knowledge_graph import KnowledgeGraphSnapshot
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
