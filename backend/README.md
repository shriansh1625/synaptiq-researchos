# SynaptiQ ResearchOS — Backend

FastAPI backend for the SynaptiQ autonomous multi-agent research platform.

## Development

```bash
cd backend
pip install -e ".[dev]"
pytest tests/ -v
uvicorn main:app --reload
```

## Docker (full stack)

From the repository root:

```bash
cp docker/.env.example docker/.env
docker compose -f docker/docker-compose.yml --env-file docker/.env up --build
curl http://localhost:8000/health
```

The API container runs `alembic upgrade head` before starting Uvicorn.
`DATABASE_URL` and `REDIS_URL` are composed inside `docker-compose.yml` using
internal service hostnames (`postgres`, `redis`).

## Configuration

Runtime settings are loaded from environment variables and an optional `backend/.env` file.
See `config/settings.py` for the full list of supported variables.

## Database migrations

```bash
cd backend
alembic upgrade head
```
