# Deploy SynaptiQ ResearchOS (Vercel + Render)

## Prerequisites

- GitHub repository with this codebase
- [Gemini API key](https://aistudio.google.com/apikey)
- Vercel account (frontend)
- Render account (API + Postgres + Redis)

---

## 1. Push to GitHub

```powershell
cd c:\Users\shria\Desktop\synaptiq
git init
git add .
git commit -m "SynaptiQ ResearchOS — Capgemini Round 2 submission"
gh repo create synaptiq-researchos --public --source=. --remote=origin --push
```

If the repo already exists:

```powershell
git remote add origin https://github.com/YOUR_USER/synaptiq-researchos.git
git push -u origin main
```

Never commit `docker/.env` or `backend/.env` (they are gitignored).

---

## 2. Deploy API on Render

1. Go to [Render Dashboard](https://dashboard.render.com/) → **New** → **Blueprint**
2. Connect your GitHub repo
3. Render reads `render.yaml` and creates:
   - `synaptiq-api` (Python web service — free tier does not support Docker web services)
   - `synaptiq-db` (PostgreSQL)
   - `synaptiq-redis` (Key Value)
4. When prompted, set **secret** env vars on `synaptiq-api`:
   - `GEMINI_API_KEY` = your key
   - `SEMANTIC_SCHOLAR_API_KEY` = optional
5. Wait for deploy; note the API URL, e.g. `https://synaptiq-api.onrender.com`
6. Verify: `https://synaptiq-api.onrender.com/health`

**Free tier note:** Render spins down after inactivity; first request may take 30–60s.

---

## 3. Deploy frontend on Vercel

1. Go to [Vercel](https://vercel.com/new) → Import Git repository
2. Set **Root Directory** to `frontend`
3. Framework: **Next.js** (auto-detected)
4. Environment variable:

| Name | Value |
|------|--------|
| `NEXT_PUBLIC_API_URL` | `https://synaptiq-api.onrender.com` |

5. Deploy → note URL, e.g. `https://synaptiq-researchos.vercel.app`

Optional demo vars (after a successful production run):

| Name | Value |
|------|--------|
| `NEXT_PUBLIC_DEMO_SESSION_ID` | session UUID |
| `NEXT_PUBLIC_DEMO_REPORT_ID` | report UUID |

---

## 4. Post-deploy smoke test

1. Open Vercel URL → API badge should be **online**
2. Run **Benchmark** with hero RAG query
3. Open `/benchmark` → KPI cards load
4. Run **Run Analysis** with a non-hero query (may take several minutes on free tier)

---

## 5. Update submission materials

- Add GitHub URL to PPT and source PDF
- Add Vercel live demo URL to deck Slide 1
- Re-export `SynaptiQ_Source_Code_Submission.pdf` with real repo URL
