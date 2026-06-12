# SynaptiQ ResearchOS

**Autonomous Multi-Agent Research Intelligence Platform** — Capgemini Agentify AI Buildathon 2026 (Round 2).

SynaptiQ goes beyond vanilla RAG: a LangGraph pipeline discovers papers, verifies claims, detects contradictions, finds research gaps, and delivers a citation-grounded executive brief with an interactive knowledge graph.

## Features

- **5 specialized agents** — Discovery, Verification, Comparative, Gap Detection, Executive Brief
- **Claim-level grounding** — unsupported claims rejected via `citation_integrity`
- **Knowledge graph** — NetworkX + Pyvis with contradiction edges
- **Benchmark dashboard** — golden-set KPIs (accuracy, citation precision, hallucination reduction, latency)
- **Resilient demo paths** — hero fast-path, curated corpus fallback, multi-provider LLM

## Quick start (Docker — recommended)

```bash
cp docker/.env.example docker/.env
# Edit docker/.env — set GEMINI_API_KEY (and optional SEMANTIC_SCHOLAR_API_KEY)

docker compose -f docker/docker-compose.yml --env-file docker/.env up --build -d
```

| Service   | URL |
|-----------|-----|
| API       | http://localhost:8000 |
| API docs  | http://localhost:8000/docs |
| Frontend  | http://localhost:3000 |
| Benchmark | http://localhost:3000/benchmark |

Health check: `curl http://localhost:8000/health`

## Quick start (local dev)

**Backend**

```bash
cd backend
pip install -e ".[dev]"
cp ../docker/.env.example .env   # or use backend/.env
uvicorn main:app --reload --port 8000
```

**Frontend**

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Open http://localhost:3000

## Demo queries

**Benchmark (sub-8s hero path)**

```
How does retrieval-augmented generation reduce hallucination in scientific QA?
```

**Full pipeline (live APIs, 3–8 min)**

```
What are the main approaches to multi-agent LLM orchestration for research?
```

## Enable instant “Load Demo” button

After one successful **Run Analysis**:

1. Copy `session_id` and `report_id` from the results URL / API response.
2. Set in `docker/.env` and `frontend/.env.local`:

```env
NEXT_PUBLIC_DEMO_SESSION_ID=<session_id>
NEXT_PUBLIC_DEMO_REPORT_ID=<report_id>
```

3. Rebuild frontend: `docker compose -f docker/docker-compose.yml --env-file docker/.env up -d --build frontend`

## Architecture

| Layer | Stack |
|-------|--------|
| Frontend | Next.js 15, Tailwind |
| API | FastAPI, OpenTelemetry |
| Orchestration | LangGraph, conditional routing |
| Agents | 5 specialized agents + KG + PDF |
| Data | PostgreSQL, FAISS, Redis |
| LLM | Gemini 2.5 Flash Lite (swappable) |

See [ARCHITECTURE_BLUEPRINT.md](./ARCHITECTURE_BLUEPRINT.md) and [TECHNICAL_SPECIFICATION.md](./TECHNICAL_SPECIFICATION.md).

## Tests

```bash
cd backend && python -m pytest tests/ -q
cd frontend && npm run build
```

CI runs both on push (see `.github/workflows/ci.yml`).

## Submission artifacts

| Artifact | How to generate |
|----------|-----------------|
| PPT content pack | `SynaptiQ_PPT_Content_Pack.pdf` (repo root) |
| Source code PDF | `python scripts/generate_source_code_pdf.py` |
| Submission checklist | [SUBMISSION.md](./SUBMISSION.md) |

## Repository layout

```
synaptiq/
├── backend/          # FastAPI + LangGraph agents
├── frontend/         # Next.js UI
├── docker/           # Compose, Dockerfiles, .env.example
├── deployment/azure/ # Optional Azure Bicep
├── scripts/          # PDF generators
└── docs/             # Architecture specs
```

## Deployment (Vercel + Render)

See [deployment/DEPLOY.md](./deployment/DEPLOY.md) for step-by-step instructions.

Quick summary:
1. Push this repo to GitHub
2. Render Blueprint from `render.yaml` → API + Postgres + Redis
3. Vercel import `frontend/` → set `NEXT_PUBLIC_API_URL` to your Render API URL

## Team

| Member | Role |
|--------|------|
| Shriansh Vikram Singh | Lead / Backend & LangGraph |
| [Name 2] | Frontend & UX |
| [Name 3] | ML & Evaluation |
| [Name 4] | Architecture & DevOps |
| [Name 5] | [Role] |

## License

Proprietary — Capgemini Agentify AI Buildathon 2026 submission.
