"""Generate Capgemini source-code submission PDF for SynaptiQ ResearchOS."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, Paragraph, Preformatted, SimpleDocTemplate, Spacer

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "SynaptiQ_Source_Code_Submission.pdf"

# Key files included with truncated snippets for the submission PDF.
CODE_SNIPPETS: list[tuple[str, int]] = [
    ("backend/app/graphs/research_graph.py", 80),
    ("backend/app/graphs/routing.py", 54),
    ("backend/app/agents/discovery_agent.py", 60),
    ("backend/app/agents/verification_agent.py", 80),
    ("backend/app/agents/comparative_agent.py", 60),
    ("backend/app/agents/gap_agent.py", 60),
    ("backend/app/agents/brief_agent.py", 80),
    ("backend/app/services/brief/citation_integrity.py", 80),
    ("backend/app/services/benchmark/evaluator.py", 80),
    ("backend/app/services/benchmark/fast_path.py", 60),
    ("backend/app/api/v1/routes_research.py", 80),
    ("backend/main.py", 80),
    ("frontend/app/page.tsx", 60),
    ("frontend/lib/api.ts", 80),
    ("docker/docker-compose.yml", 80),
]

TREE_DIRS = [
    "backend/app/agents",
    "backend/app/graphs",
    "backend/app/services",
    "backend/app/api",
    "frontend/app",
    "frontend/components",
    "docker",
    "deployment/azure",
    "scripts",
]


def build_tree() -> str:
    lines = ["synaptiq/"]
    for rel in TREE_DIRS:
        base = ROOT / rel
        if not base.is_dir():
            continue
        lines.append(f"├── {rel}/")
        children = sorted(
            p for p in base.iterdir() if p.suffix in {".py", ".tsx", ".ts", ".yml", ".yaml", ".md", ".bicep"}
        )[:12]
        for child in children:
            lines.append(f"│   ├── {child.name}")
        if len(list(base.iterdir())) > 12:
            lines.append("│   └── …")
    lines.append("├── README.md")
    lines.append("├── ARCHITECTURE_BLUEPRINT.md")
    lines.append("└── SUBMISSION.md")
    return "\n".join(lines)


def read_snippet(rel: str, max_lines: int) -> str:
    path = ROOT / rel
    if not path.is_file():
        return f"# missing: {rel}\n"
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if len(lines) > max_lines:
        lines = lines[:max_lines] + [f"... ({path.name} truncated at {max_lines} lines)"]
    return "\n".join(lines)


def main() -> None:
    styles = getSampleStyleSheet()
    title = ParagraphStyle("T", parent=styles["Title"], fontSize=18, spaceAfter=12)
    h1 = ParagraphStyle("H1", parent=styles["Heading2"], fontSize=12, spaceBefore=10, spaceAfter=6)
    body = ParagraphStyle("B", parent=styles["Normal"], fontSize=9, leading=12)
    mono = ParagraphStyle("M", parent=styles["Code"], fontSize=7, leading=9, fontName="Courier")

    story: list = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    story += [
        Paragraph("SynaptiQ ResearchOS — Source Code Submission", title),
        Paragraph("Capgemini Agentify AI Buildathon 2026 · Round 2 Deep Dive", body),
        Spacer(1, 0.3 * cm),
        Paragraph("<b>Repository:</b> [ADD YOUR GITHUB URL HERE]", body),
        Paragraph("<b>Live demo:</b> [ADD VERCEL URL WHEN DEPLOYED] → API on Render", body),
        Paragraph(f"<b>Generated:</b> {now}", body),
        Spacer(1, 0.4 * cm),
        Paragraph(
            "This PDF summarizes the SynaptiQ codebase structure and includes "
            "representative excerpts from the multi-agent pipeline, citation integrity, "
            "benchmark evaluation, API routes, frontend client, and Docker stack.",
            body,
        ),
        PageBreak(),
        Paragraph("Repository Structure", h1),
        Preformatted(build_tree(), mono),
        PageBreak(),
    ]

    for rel, max_lines in CODE_SNIPPETS:
        story.append(Paragraph(rel, h1))
        story.append(Preformatted(read_snippet(rel, max_lines), mono))
        story.append(Spacer(1, 0.2 * cm))

    story += [
        PageBreak(),
        Paragraph("Documentation References", h1),
        Paragraph("• README.md — quick start and demo instructions", body),
        Paragraph("• ARCHITECTURE_BLUEPRINT.md — full system design", body),
        Paragraph("• TECHNICAL_SPECIFICATION.md — implementation spec", body),
        Paragraph("• SUBMISSION.md — pre-submission verification checklist", body),
        Spacer(1, 0.4 * cm),
        Paragraph(
            "<b>Run locally:</b> docker compose -f docker/docker-compose.yml "
            "--env-file docker/.env up --build",
            body,
        ),
    ]

    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    def footer(canvas, _doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(1.5 * cm, 1 * cm, "SynaptiQ ResearchOS · Source Code Submission")
        canvas.drawRightString(A4[0] - 1.5 * cm, 1 * cm, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
