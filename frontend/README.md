# SynaptiQ ResearchOS — Frontend

Next.js demo UI for the research intelligence API. Does not modify the agent pipeline — only consumes existing endpoints.

## Quick start (local)

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). API must be running at `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`).

## Demo mode

After one successful `POST /analyze`, copy `session_id` and `report_id` into `.env.local`:

```
NEXT_PUBLIC_DEMO_SESSION_ID=<session_id>
NEXT_PUBLIC_DEMO_REPORT_ID=<report_id>
```

The **Load Demo** button opens a pre-computed run instantly for pitches.

## Docker (with backend)

From repo root:

```bash
docker compose -f docker/docker-compose.yml --env-file docker/.env up --build frontend api
```
