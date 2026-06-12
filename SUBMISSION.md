# Capgemini Round 2 — Submission Checklist

**Extended deadline: June 13, 2026, 11:59 PM IST**

## Deliverables

| # | Item | Status | Action |
|---|------|--------|--------|
| 1 | Presentation deck (.pptx) | ☐ | Finalize Canva deck; embed screenshots; fill team + URLs |
| 2 | Source code PDF | ☐ | Run `python scripts/generate_source_code_pdf.py` |
| 3 | Repository link | ☐ | Push to dedicated GitHub repo; add URL to deck + PDF |
| 4 | Live demo readiness | ☐ | Local Docker + rehearsed script; deploy Vercel/Render last |

## Pre-submission verification

Run this checklist the day before you submit:

```bash
# 1. Full stack healthy
docker compose -f docker/docker-compose.yml --env-file docker/.env up -d --build
curl http://localhost:8000/health

# 2. Tests green
cd backend && python -m pytest tests/ -q

# 3. Frontend builds
cd frontend && npm run build

# 4. Benchmark KPIs
open http://localhost:3000/benchmark
# Expect: accuracy ≥92%, citation ≥95%, hallucination reduction ≥80%, P50 <8s

# 5. Benchmark demo (~20s)
# Home → Benchmark → hero RAG hallucination query

# 6. Full analysis (3–8 min)
# Home → Run Analysis → wait for session page with brief + KG

# 7. Load Demo (after setting NEXT_PUBLIC_DEMO_* in .env)
# Home → Load Demo → instant pre-computed session
```

## Demo script (4 minutes)

1. Open home — API online
2. Run **Benchmark** with hero query
3. Show agent timeline → brief → click citation → evidence panel
4. Show contradiction panel + knowledge graph
5. Open **Benchmark dashboard** — KPI cards
6. (Optional) **Load Demo** or fresh Run Analysis for judges

## Git repository setup

Initialize a **dedicated repo** for this folder only (not your home directory):

```bash
cd path/to/synaptiq
git init
git add .
git commit -m "SynaptiQ ResearchOS — Capgemini Round 2 submission"
git remote add origin https://github.com/YOUR_ORG/synaptiq-researchos.git
git push -u origin main
```

Ensure `.env` files are **not** committed (see `.gitignore`).

## Deployment (do last)

After local verification is 100%:

- [ ] Deploy frontend to **Vercel**
- [ ] Deploy API to **Render** (Docker)
- [ ] Set `NEXT_PUBLIC_API_URL` to Render API URL
- [ ] Update deck + README with live URLs

## Files to submit

- `SynaptiQ ResearchOS Pitch Deck.pptx` (or PDF export)
- `SynaptiQ_Source_Code_Submission.pdf` (from script)
- GitHub repository URL inside the source PDF cover page
