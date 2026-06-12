#!/bin/sh
set -e

echo "Running database migrations..."
alembic upgrade head

if [ -d /app/app/resources/benchmark ]; then
  mkdir -p /app/data/benchmark
  for f in hero_bundle.json golden_set.json; do
    if [ ! -f "/app/data/benchmark/$f" ] && [ -f "/app/app/resources/benchmark/$f" ]; then
      cp "/app/app/resources/benchmark/$f" "/app/data/benchmark/$f"
    fi
  done
fi

echo "Starting API server..."
PORT="${PORT:-8000}"
exec uvicorn main:app --host 0.0.0.0 --port "${PORT}"
