"""Professional PDF report generation."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.schemas.brief import ExecutiveBriefOutput
from app.schemas.knowledge_graph import KnowledgeGraphSnapshot


class PDFReportGenerator:
    """Generate downloadable executive research PDFs."""

    def generate(
        self,
        *,
        query: str,
        brief: ExecutiveBriefOutput,
        knowledge_graph: KnowledgeGraphSnapshot,
        papers: list[dict[str, Any]],
        output_path: Path,
    ) -> Path:
        """Render a multi-section PDF report."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=letter,
            leftMargin=0.75 * inch,
            rightMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
            title=brief.report.title,
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Title"],
            fontSize=22,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=16,
        )
        heading_style = ParagraphStyle(
            "SectionHeading",
            parent=styles["Heading2"],
            fontSize=14,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=12,
            spaceAfter=8,
        )
        body_style = ParagraphStyle(
            "Body",
            parent=styles["BodyText"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#334155"),
        )

        story: list[Any] = []
        story.append(Paragraph("SynaptiQ ResearchOS", title_style))
        story.append(Paragraph(brief.report.title, heading_style))
        story.append(
            Paragraph(
                f"Generated {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
                body_style,
            )
        )
        story.append(Spacer(1, 0.2 * inch))
        story.append(PageBreak())

        story.append(Paragraph("Research Query", heading_style))
        story.append(Paragraph(self._escape(query), body_style))
        story.append(Spacer(1, 0.15 * inch))

        story.append(Paragraph("Executive Summary", heading_style))
        story.append(Paragraph(self._escape(brief.report.executive_summary), body_style))

        self._add_blocks(story, heading_style, body_style, "Key Findings", brief.report.key_findings)
        self._add_blocks(
            story,
            heading_style,
            body_style,
            "Comparative Insights",
            brief.report.comparative_insights,
        )
        self._add_blocks(story, heading_style, body_style, "Contradictions", brief.report.contradictions)
        self._add_gap_blocks(story, heading_style, body_style, brief.report.research_gaps)
        self._add_blocks(
            story,
            heading_style,
            body_style,
            "Future Opportunities",
            brief.report.future_opportunities,
        )
        self._add_blocks(story, heading_style, body_style, "Recommendations", brief.report.recommendations)

        story.append(Paragraph("Confidence Scores", heading_style))
        confidence_rows = [
            ["Metric", "Score"],
            ["Overall Brief Confidence", f"{brief.overall_confidence:.2f}"],
            ["Citation Integrity", "Valid" if brief.citation_integrity.all_citations_valid else "Adjusted"],
            ["Papers Analyzed", str(len(papers))],
        ]
        story.append(self._table(confidence_rows))
        story.append(PageBreak())

        story.append(Paragraph("Knowledge Graph Snapshot", heading_style))
        kg_rows = [
            ["Nodes", str(knowledge_graph.summary.nodes_count)],
            ["Edges", str(knowledge_graph.summary.edges_count)],
            ["Contradictions", str(knowledge_graph.summary.contradictions_count)],
            ["Communities", str(knowledge_graph.summary.communities_count)],
            ["Top Topics", ", ".join(knowledge_graph.summary.top_topics) or "N/A"],
        ]
        story.append(self._table(kg_rows))
        story.append(PageBreak())

        story.append(Paragraph("Citations", heading_style))
        for citation in brief.citations[:25]:
            line = (
                f"<b>{self._escape(citation.citation_id)}</b> — "
                f"{self._escape(citation.title or citation.text_span)} "
                f"(confidence {citation.confidence:.2f})"
            )
            story.append(Paragraph(line, body_style))

        story.append(PageBreak())
        story.append(Paragraph("Appendix", heading_style))
        story.append(Paragraph(self._escape(brief.report.limitations), body_style))
        paper_lines = [
            f"• {self._escape(paper.get('title', paper.get('paper_id', '')))}"
            for paper in papers[:20]
        ]
        for line in paper_lines:
            story.append(Paragraph(line, body_style))

        doc.build(story)
        return output_path

    @staticmethod
    def _escape(text: str) -> str:
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    def _add_blocks(
        self,
        story: list[Any],
        heading_style: ParagraphStyle,
        body_style: ParagraphStyle,
        title: str,
        blocks: list[Any],
    ) -> None:
        if not blocks:
            return
        story.append(Paragraph(title, heading_style))
        for block in blocks:
            cites = ", ".join(block.citations) if block.citations else "—"
            story.append(
                Paragraph(
                    f"• {self._escape(block.text)} <i>[{self._escape(cites)}]</i>",
                    body_style,
                )
            )

    def _add_gap_blocks(
        self,
        story: list[Any],
        heading_style: ParagraphStyle,
        body_style: ParagraphStyle,
        blocks: list[Any],
    ) -> None:
        if not blocks:
            return
        story.append(Paragraph("Research Gaps", heading_style))
        for block in blocks:
            story.append(
                Paragraph(
                    f"• {self._escape(block.text)} <i>[{self._escape(block.gap_id)}]</i>",
                    body_style,
                )
            )

    @staticmethod
    def _table(rows: list[list[str]]) -> Table:
        table = Table(rows, hAlign="LEFT", colWidths=[2.5 * inch, 3.5 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        return table
