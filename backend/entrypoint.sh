#!/bin/sh
set -e

echo "Running database migrations..."
alembic upgrade head

if [ -d ./app/resources/benchmark ]; then
  mkdir -p ./data/benchmark
  for f in hero_bundle.json golden_set.json; do
    if [ ! -f "./data/benchmark/$f" ] && [ -f "./app/resources/benchmark/$f" ]; then
      cp "./app/resources/benchmark/$f" "./data/benchmark/$f"
    fi
  done
fi

echo "Starting API server..."
PORT="${PORT:-8000}"
exec uvicorn main:app --host 0.0.0.0 --port "${PORT}"
