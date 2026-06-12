"""Generate SynaptiQ PPT Content Pack PDF for Capgemini submission."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUTPUT = Path(__file__).resolve().parents[1] / "SynaptiQ_PPT_Content_Pack.pdf"

ACCENT = colors.HexColor("#0ea5e9")
DARK = colors.HexColor("#0f172a")
MUTED = colors.HexColor("#64748b")
TABLE_HEADER = colors.HexColor("#1e293b")
TABLE_ALT = colors.HexColor("#f1f5f9")


def build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "DocTitle",
            parent=base["Title"],
            fontSize=22,
            leading=28,
            textColor=DARK,
            spaceAfter=6,
            alignment=TA_CENTER,
        ),
        "subtitle": ParagraphStyle(
            "DocSubtitle",
            parent=base["Normal"],
            fontSize=11,
            leading=14,
            textColor=MUTED,
            alignment=TA_CENTER,
            spaceAfter=20,
        ),
        "h1": ParagraphStyle(
            "H1",
            parent=base["Heading1"],
            fontSize=16,
            leading=20,
            textColor=ACCENT,
            spaceBefore=14,
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontSize=12,
            leading=15,
            textColor=DARK,
            spaceBefore=10,
            spaceAfter=6,
        ),
        "h3": ParagraphStyle(
            "H3",
            parent=base["Heading3"],
            fontSize=10,
            leading=13,
            textColor=DARK,
            spaceBefore=8,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontSize=9.5,
            leading=13,
            textColor=DARK,
            alignment=TA_JUSTIFY,
            spaceAfter=6,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=base["Normal"],
            fontSize=9.5,
            leading=13,
            textColor=DARK,
            leftIndent=14,
            bulletIndent=0,
            spaceAfter=3,
        ),
        "quote": ParagraphStyle(
            "Quote",
            parent=base["Normal"],
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#334155"),
            leftIndent=12,
            rightIndent=12,
            spaceBefore=4,
            spaceAfter=8,
            fontName="Helvetica-Oblique",
        ),
        "mono": ParagraphStyle(
            "Mono",
            parent=base["Code"],
            fontSize=8,
            leading=10,
            textColor=DARK,
            fontName="Courier",
            spaceAfter=6,
        ),
        "footer": ParagraphStyle(
            "Footer",
            parent=base["Normal"],
            fontSize=8,
            textColor=MUTED,
            alignment=TA_CENTER,
        ),
    }


def table(data: list[list[str]], col_widths: list[float] | None = None) -> Table:
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), TABLE_HEADER),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, TABLE_ALT]),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return t


def bullets(st: dict, items: list[str]) -> list:
    return [Paragraph(f"• {item}", st["bullet"]) for item in items]


def section_title(st: dict, num: str, title: str) -> list:
    return [
        Spacer(1, 0.2 * cm),
        Paragraph(f"SLIDE {num} — {title}", st["h1"]),
        HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=8),
    ]


def build_story(st: dict) -> list:
    story: list = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Cover
    story += [
        Spacer(1, 3 * cm),
        Paragraph("SynaptiQ ResearchOS", st["title"]),
        Paragraph("Complete PPT Content Pack", st["title"]),
        Spacer(1, 0.4 * cm),
        Paragraph("Capgemini Agentify AI Buildathon 2026 · Round 2 Deep Dive Submission", st["subtitle"]),
        Paragraph(f"Generated {now} · 12 slides + submission checklist", st["subtitle"]),
        Spacer(1, 1 * cm),
        Paragraph(
            "Use this document to build your presentation deck, rehearse your demo, "
            "and prepare for the evaluation call.",
            st["body"],
        ),
        PageBreak(),
    ]

    # Submission checklist
    story += [
        Paragraph("Submission Checklist", st["h1"]),
        table(
            [
                ["Item", "What to submit"],
                ["Presentation deck", "This PPT (5 original themes + 7 new slides)"],
                ["Source code PDF", "Export/print repo or key folders as PDF"],
                ["Repository link", "GitHub URL inside the PDF (recommended)"],
                ["Live demo readiness", "Judges may ask you to demonstrate working functionality"],
            ],
            [4.5 * cm, 12 * cm],
        ),
        Spacer(1, 0.3 * cm),
        Paragraph("<b>Deadline:</b> June 10, 11:59 PM IST", st["body"]),
        PageBreak(),
    ]

    # Slide 1
    story += section_title(st, "1", "Title")
    story += [
        Paragraph("<b>Title:</b> SynaptiQ ResearchOS", st["body"]),
        Paragraph("<b>Subtitle:</b> Autonomous Multi-Agent Research Intelligence Platform", st["body"]),
        Paragraph("<b>Footer:</b> Capgemini Agentify AI Buildathon 2026 · Team [Your Team Name]", st["body"]),
        Paragraph(
            '<b>Tagline:</b> <i>"Everyone built a RAG chatbot. We built a research intelligence system '
            "that verifies every claim, detects contradictions, and finds research gaps.\"</i>",
            st["quote"],
        ),
        Paragraph("<b>Visual:</b> Dark UI screenshot (home page with query console + Multi-agent · LangGraph badge).", st["body"]),
        Paragraph(
            "<b>Speaker note (15 sec):</b> We don't solve paper search — we solve research synthesis: "
            "verification, contradiction mapping, and gap discovery, with full citation traceability.",
            st["body"],
        ),
        PageBreak(),
    ]

    # Slide 2
    story += section_title(st, "2", "The Research Overload Crisis")
    story += bullets(
        st,
        [
            "<b>Information explosion:</b> ~2.5M research papers/year → synthesis is impossible manually.",
            "<b>60–70% of research time</b> is spent organizing and reconciling sources, not generating insights.",
            "<b>Validation bottleneck:</b> Contradictory findings live across fragmented, unverified sources.",
            "<b>Tool failure today:</b> ChatGPT → hallucinated citations; Perplexity → shallow synthesis; Google Scholar → retrieval only.",
            "<b>The $8.5B gap:</b> Enterprise R&D needs trustworthy research intelligence, not another chatbot.",
        ],
    )
    story += [
        Spacer(1, 0.2 * cm),
        Paragraph("<b>Subhead (bold on slide):</b> This is not a search problem. This is a reasoning problem.", st["quote"]),
        Paragraph("<b>Visual:</b> 3-column comparison: Vanilla RAG vs ChatGPT vs SynaptiQ.", st["body"]),
        PageBreak(),
    ]

    # Slide 3
    story += section_title(st, "3", "Proposed Solution: SynaptiQ ResearchOS")
    story += [
        table(
            [
                ["Pillar", "What it means"],
                ["Multi-Agent Pipeline", "LangGraph orchestrates specialized agents with shared state & checkpointing"],
                ["Claim-Level Verification", "Every insight tied to evidence spans; unsupported claims rejected"],
                ["Research Gap Detection", "Surfaces unexplored opportunities + contradictory findings"],
                ["Enterprise-Ready Stack", "FastAPI · Next.js · PostgreSQL · FAISS · Redis · OpenTelemetry"],
            ],
            [4.5 * cm, 12 * cm],
        ),
        Spacer(1, 0.3 * cm),
        Paragraph("<b>Pipeline flow:</b>", st["h3"]),
        Paragraph(
            "User Query → Discovery → Verification → Comparative Analysis → Gap Detection → "
            "Executive Brief → Knowledge Graph + PDF",
            st["mono"],
        ),
        Paragraph(
            "<b>Tech stack (current):</b> LangGraph · Gemini 2.5 Flash Lite · Sentence-Transformers · "
            "FAISS · FastAPI · Next.js 15",
            st["body"],
        ),
        PageBreak(),
    ]

    # Slide 4
    story += section_title(st, "4", "Innovation Story: The Synthesis Bottleneck")
    story += bullets(
        st,
        [
            "<b>The synthesis bottleneck:</b> Researchers drown in PDFs. The problem isn't lack of information — it's lack of research intelligence.",
            "<b>Autonomous multi-agent reasoning:</b> Simulates a human research team: librarian → fact-checker → analyst → strategist → editor.",
            "<b>Mapping the unseen:</b> Detect contradictions (red KG edges) and research gaps with rationale.",
        ],
    )
    story += [
        Paragraph(
            '<b>Key differentiator:</b> <i>"Grounding is enforced as a data contract — not a prompt suggestion."</i>',
            st["quote"],
        ),
        Paragraph("<b>Visual:</b> Knowledge Graph screenshot + Contradiction Panel.", st["body"]),
        PageBreak(),
    ]

    # Slide 5
    story += section_title(st, "5", "Execution Approach: Built to Scale")
    story += [
        table(
            [
                ["Phase", "Delivered"],
                ["Phase 1 — Core RAG", "Document ingestion, embeddings, FAISS vector index, hybrid retrieval"],
                ["Phase 2 — Orchestration", "LangGraph multi-agent workflows, conditional routing, checkpointing"],
                ["Phase 3 — Intelligence Layer", "Verification, contradiction detection, gap analysis, citation integrity"],
                ["Phase 4 — Production", "Benchmark KPIs, OpenTelemetry, Docker, Vercel (frontend) + Render (API)"],
            ],
            [4.5 * cm, 12 * cm],
        ),
        Spacer(1, 0.3 * cm),
        Paragraph("<b>Success metrics (live Benchmark Dashboard):</b>", st["h3"]),
        table(
            [
                ["Metric", "Your result", "Target"],
                ["Accuracy", "100%", "≥ 92%"],
                ["Citation precision", "100%", "≥ 95%"],
                ["Hallucination reduction", "100%", "≥ 80% (vs 32% vanilla-RAG baseline)"],
                ["P50 latency (hero path)", "6.5 s", "< 8 s"],
            ],
            [5 * cm, 4 * cm, 7.5 * cm],
        ),
        PageBreak(),
    ]

    # Slide 6
    story += section_title(st, "6", "Approach & Methodology (Capgemini Required)")
    story += bullets(
        st,
        [
            "Decompose research synthesis into irreducible cognitive roles (Discovery → Verification → Comparative → Gap → Brief).",
            "Design for trust first: claims are first-class objects; no span → UNSUPPORTED → excluded via citation_integrity.",
            "Orchestrate with LangGraph: shared ResearchState, conditional loops, checkpointing.",
            "Validate with measurable KPIs: golden set + benchmark fast-path + live full pipeline.",
            "Build demo-safe production paths: hero corpus fallback, curated paper rescue, LLM fallback, resilient polling.",
        ],
    )
    story += [
        Paragraph("<b>Frameworks:</b> LangGraph · Hybrid retrieval (FAISS + lexical) · Pydantic structured outputs · OpenTelemetry · Golden-set evaluation", st["body"]),
        PageBreak(),
    ]

    # Slide 7
    story += section_title(st, "7", "Implementation Steps (Capgemini Required)")
    story += [
        table(
            [
                ["Step", "What we built", "Key modules"],
                ["1", "Architecture & sprint plan", "ARCHITECTURE_BLUEPRINT.md, SPRINT_BOARD.md"],
                ["2", "Backend skeleton + Docker", "FastAPI, PostgreSQL, Redis, docker-compose.yml"],
                ["3", "Discovery agent + connectors", "discovery_agent.py, Semantic Scholar, arXiv"],
                ["4", "Verification + FAISS", "verification_agent.py, faiss_store, hybrid_retriever"],
                ["5", "Comparative + Gap agents", "comparative_agent.py, gap_agent.py"],
                ["6", "LangGraph pipeline", "research_graph.py, routing.py (7 nodes)"],
                ["7", "Next.js UI", "AgentTimeline, BriefViewer, GraphViewer, ContradictionPanel"],
                ["8", "Benchmark + hardening", "fast_path.py, evaluator.py, /benchmark page"],
            ],
            [1.2 * cm, 5.5 * cm, 9.8 * cm],
        ),
        PageBreak(),
    ]

    # Slide 8
    story += section_title(st, "8", "Solution Demonstration (Capgemini Required)")
    story += [
        Paragraph("<b>4-minute demo script:</b>", st["h3"]),
        table(
            [
                ["Time", "Action", "What to say"],
                ["0:00–0:30", "Open home page, show API online", "Real LangGraph pipeline — not a scripted animation."],
                ["0:30–1:00", "Click Benchmark with hero query", "Use: How does RAG reduce hallucination in scientific QA?"],
                ["1:00–1:45", "Show Agent Timeline", "Five agents: Discovery → Verification → Comparative → Gap → Brief → KG → PDF."],
                ["1:45–2:30", "Open Brief, click citation", "Every sentence links to verified claim and evidence span."],
                ["2:30–3:15", "Contradiction Panel + KG", "Red edges = contradictions — signal vanilla RAG destroys."],
                ["3:15–3:45", "Show research gaps in brief", "Absence reasoning, not just summarization."],
                ["3:45–4:00", "Benchmark Dashboard", "100% golden-set KPIs; P50 6.5s; Run Analysis for live depth."],
            ],
            [2.2 * cm, 4.5 * cm, 10.3 * cm],
        ),
        Spacer(1, 0.2 * cm),
        Paragraph("<b>Backup queries:</b> Multi-agent LLM orchestration for research · Transformer efficiency for long-context reasoning", st["body"]),
        Paragraph("<b>Screenshots to embed:</b> Home · Agent timeline · Brief with citations · KG · Benchmark dashboard · PDF download", st["body"]),
        PageBreak(),
    ]

    # Slide 9
    story += section_title(st, "9", "Technical Architecture (Capgemini Required)")
    story += bullets(
        st,
        [
            "<b>Presentation tier:</b> Next.js 15 + Tailwind — Query, Timeline, Brief, KG, Benchmark",
            "<b>API tier:</b> FastAPI — REST, session polling, OpenTelemetry middleware",
            "<b>Orchestration tier:</b> LangGraph — checkpointing, conditional routing",
            "<b>Agent tier:</b> 5 agents + KG builder (NetworkX + Pyvis)",
            "<b>Data tier:</b> PostgreSQL, FAISS, Redis, Semantic Scholar / arXiv",
        ],
    )
    story += [
        Paragraph("<b>Deployment:</b> Vercel (frontend) · Render (API, Docker) · Local: docker compose + npm run dev", st["body"]),
        Paragraph(
            "<b>Data flow:</b> sessions → papers → verified_claims → comparative_analysis → "
            "research_gaps → executive_reports → kg_nodes/edges",
            st["mono"],
        ),
        PageBreak(),
    ]

    # Slide 10
    story += section_title(st, "10", "Code Flow / Multi-Agent Pipeline (Capgemini Required)")
    story += [
        Paragraph("<b>End-to-end flow:</b>", st["h3"]),
        Paragraph(
            "1. POST /research/analyze → background_runner starts LangGraph<br/>"
            "2. node_discovery → PaperRetrievalService (SS + arXiv) + curated fallback<br/>"
            "3. route_after_discovery → loop if insufficient papers<br/>"
            "4. node_verification → chunk → embed → FAISS → claim verdicts<br/>"
            "5. route_after_verification → re-discover if unsupported_ratio &gt; 80%<br/>"
            "6. node_comparative → cluster claims → CONTRADICTS / SUPPORTS<br/>"
            "7. node_gap → coverage matrix → ranked gaps<br/>"
            "8. node_brief → LLM compose → citation_integrity sanitize<br/>"
            "9. node_kg_build → NetworkX → Pyvis HTML<br/>"
            "10. node_report → PDF deliverable<br/>"
            "11. GET /session/{id} → frontend polls until complete",
            st["mono"],
        ),
        Spacer(1, 0.2 * cm),
        Paragraph(
            "<b>Key files:</b> research_graph.py · routing.py · citation_integrity.py · frontend/lib/api.ts",
            st["body"],
        ),
        PageBreak(),
    ]

    # Slide 11
    story += section_title(st, "11", "Challenges & Learnings (Capgemini Required)")
    story += [
        table(
            [
                ["Challenge", "Solution", "Learning"],
                ["Docker volume hid hero bundle", "Moved to app/resources/benchmark/", "Immutable app resources for demo artifacts"],
                ["API rate limits (SS/arXiv 429)", "Curated corpus + emergency retrieval", "Never depend on single upstream"],
                ["LLM provider instability", "FallbackLLMClient + graceful degradation", "Multi-provider > single vendor"],
                ["Frontend request timeout", "120s poll, 12-min max wait", "Async pipelines need async UX"],
                ["Pyvis CDN 404", "cdn_resources=remote", "Explicit CDN config in containers"],
                ["Full pipeline 3–8 min vs benchmark <8s", "Two modes: Benchmark + Run Analysis", "Separate demo path from proof path"],
            ],
            [4 * cm, 5.5 * cm, 7 * cm],
        ),
        Paragraph(
            "<b>Team learning:</b> Top 10 means optimizing for trust, observability, and demo reliability — not feature count.",
            st["quote"],
        ),
        PageBreak(),
    ]

    # Slide 12 USP
    story += section_title(st, "12", "USP — Unique Selling Proposition")
    story += [
        Paragraph(
            '<b>One-liner:</b> <i>"SynaptiQ is the only solution that treats research synthesis as verified, '
            "multi-agent reasoning over claims — not chunked summarization — with measurable trust KPIs "
            'and full audit traceability."</i>',
            st["quote"],
        ),
        table(
            [
                ["#", "USP", "Why judges care"],
                ["1", "Claim-level grounding as data contract", "Unsupported claims rejected — solves hallucination fear"],
                ["2", "Contradiction + gap intelligence", "Surfaces what RAG averages away"],
                ["3", "Real LangGraph multi-agent orchestration", "Live agent timeline + OTel — proves agentify criteria"],
                ["4", "Interactive knowledge graph", "Explorable papers, claims, contradictions — demo wow factor"],
                ["5", "Benchmark-backed trust metrics", "100% accuracy & citation precision; 6.5s P50 latency"],
            ],
            [0.8 * cm, 5.5 * cm, 10.2 * cm],
        ),
        Spacer(1, 0.2 * cm),
        Paragraph(
            "<b>Positioning:</b> ChatGPT = fluency · Perplexity = shallow synthesis · Scholar = retrieval · "
            "<b>SynaptiQ = verified research intelligence</b>",
            st["body"],
        ),
        PageBreak(),
    ]

    # Slide 13 optional
    story += section_title(st, "13", "Team & Repository (Optional)")
    story += bullets(
        st,
        [
            "Team members + roles (PM, backend/LangGraph, frontend, ML/prompts)",
            "Repository: [your GitHub URL]",
            "Live demo: [Vercel URL] → API on Render",
            "Documentation: ARCHITECTURE_BLUEPRINT.md · TECHNICAL_SPECIFICATION.md",
            "Thank you / Q&A",
        ],
    )
    story.append(PageBreak())

    # Evaluation prep
    story += [
        Paragraph("Evaluation Call Preparation", st["h1"]),
        HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=8),
        Paragraph("<b>Opening (20 sec):</b>", st["h3"]),
        Paragraph(
            '"We built a multi-agent research intelligence platform. Every insight is claim-verified, '
            "contradictions are surfaced in a knowledge graph, and we hit 100% on our golden-set trust "
            'metrics with 6.5 second benchmark latency."',
            st["quote"],
        ),
        Paragraph('<b>If asked "Is it real or mocked?":</b>', st["h3"]),
    ]
    story += bullets(
        st,
        [
            "Agent logs in PostgreSQL are real.",
            "LangGraph execution is real.",
            "Benchmark uses hero bundle for speed; Run Analysis hits live APIs.",
            "Citation integrity is deterministic code, not prompt-only.",
        ],
    )
    story += [
        Paragraph("<b>If something breaks live:</b> Switch to Benchmark mode with hero query, or use Load Demo.", st["body"]),
        Spacer(1, 0.4 * cm),
        Paragraph("Source Code PDF — What to Include", st["h2"]),
    ]
    story += bullets(
        st,
        [
            "Repo link on cover page",
            "Folder tree (backend/app/agents/, graphs/, frontend/)",
            "Key snippets: research_graph.py, citation_integrity.py, evaluator.py",
            "docker-compose.yml + .env.example (no real API keys)",
            "Screenshot of benchmark dashboard or passing tests",
        ],
    )
    story += [
        Spacer(1, 0.4 * cm),
        Paragraph("Design Tips for Top 10 Polish", st["h2"]),
    ]
    story += bullets(
        st,
        [
            "Dark theme matching your app (purple/teal gradient, glass cards)",
            "One real screenshot per demo slide",
            "Bold numbers: 100%, 6.5s, 32% baseline, 5 agents, 7 pipeline steps",
            "Replace old deck text (GPT-4, Azure) with Gemini 2.5 Flash Lite, LangGraph, Vercel + Render",
        ],
    )

    return story


def main() -> None:
    st = build_styles()
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="SynaptiQ PPT Content Pack",
        author="SynaptiQ Team",
    )

    def on_page(canvas, doc_obj):  # noqa: ARG001
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(2 * cm, 1.2 * cm, "SynaptiQ ResearchOS · Capgemini Agentify AI 2026")
        canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    doc.build(build_story(st), onFirstPage=on_page, onLaterPages=on_page)
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
