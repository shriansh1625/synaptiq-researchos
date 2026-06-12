# Database Migrations (Alembic)

SynaptiQ ResearchOS uses [Alembic](https://alembic.sqlalchemy.org/) with **async SQLAlchemy 2.0** and **PostgreSQL** (`asyncpg`).

## Layout

```text
backend/
├── alembic.ini
└── app/database/migrations/
    ├── env.py                 # Async migration runtime + autogenerate metadata
    ├── script.py.mako         # Revision template for new migrations
    ├── versions/
    │   └── 0001_initial_schema.py
    └── README.md
```

## Prerequisites

1. PostgreSQL running and reachable.
2. Environment variables loaded (see `config/settings.py`):

```bash
export DATABASE_URL=postgresql+asyncpg://synaptiq:synaptiq@localhost:5432/synaptiq
export REDIS_URL=redis://localhost:6379/0
export GEMINI_API_KEY=your-dev-key-here
```

Or copy `docker/.env.example` to `docker/.env` and start the stack:

```bash
docker compose -f docker/docker-compose.yml --env-file docker/.env up -d postgres
```

3. Install backend dependencies:

```bash
cd backend
pip install -e ".[dev]"
```

## Common commands

Run all commands from the `backend/` directory.

### Apply migrations

```bash
alembic upgrade head
```

### Roll back one revision

```bash
alembic downgrade -1
```

### Show current revision

```bash
alembic current
```

### Show migration history

```bash
alembic history --verbose
```

## Auto-generation

`env.py` registers all ORM models on `Base.metadata` and enables:

- `compare_type=True`
- `compare_server_default=True`

After changing SQLAlchemy models under `app/database/models/`, generate a new revision:

```bash
alembic revision --autogenerate -m "describe your change"
```

**Always review** the generated script before applying it. Autogenerate detects most schema changes but may miss renames, data migrations, or complex constraints.

Apply the new revision:

```bash
alembic upgrade head
```

## Offline SQL generation

Generate SQL without connecting to the database:

```bash
alembic upgrade head --sql
```

## Initial schema (`0001_initial`)

Creates these tables:

| Table | Description |
|---|---|
| `users` | Application users |
| `papers` | Research paper metadata |
| `research_sessions` | User research query sessions |
| `executive_reports` | Session executive briefs |
| `agent_logs` | Agent execution audit trail |

Foreign keys:

- `research_sessions.user_id` → `users.id` (CASCADE)
- `executive_reports.session_id` → `research_sessions.id` (CASCADE)
- `agent_logs.session_id` → `research_sessions.id` (CASCADE)

## CI / deployment

Recommended pipeline step before app rollout:

```bash
alembic upgrade head
```

Run migrations once per deployment against the target database. Do not run migrations concurrently from multiple instances.

## Troubleshooting

| Issue | Fix |
|---|---|
| `Field required` for settings | Export `DATABASE_URL`, `REDIS_URL`, `GEMINI_API_KEY` |
| Connection refused | Start PostgreSQL (`docker compose up -d postgres`) |
| Autogenerate produces empty migration | Ensure new models are imported in `env.py` |
| `Target database is not up to date` | Run `alembic upgrade head` before autogenerate |
