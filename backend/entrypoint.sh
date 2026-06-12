#!/bin/sh
set -e

echo "Running database migrations..."
attempt=0
max_attempts=30
until alembic upgrade head; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge "$max_attempts" ]; then
    echo "Database migrations failed after ${max_attempts} attempts."
    exit 1
  fi
  echo "Migration attempt ${attempt} failed; retrying in 5s..."
  sleep 5
done

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
