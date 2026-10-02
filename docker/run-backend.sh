#!/bin/bash
# Backend program wrapper (managed by supervisord).
# Gates on PostgreSQL + Redis, runs migrations, then starts Uvicorn.
set -euo pipefail

POSTGRES_USER="${POSTGRES_USER:-rag_user}"
POSTGRES_DB="${POSTGRES_DB:-school_rag}"
REDIS_PORT="${REDIS_PORT:-6379}"
BACKEND_HOST="${BACKEND_HOST:-0.0.0.0}"
BACKEND_PORT="${BACKEND_PORT:-8000}"

echo "[backend] Waiting for PostgreSQL ..."
for i in $(seq 1 60); do
  if pg_isready -h 127.0.0.1 -p 5432 -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then
    break
  fi
  if [ "$i" -eq 60 ]; then echo "[backend] ERROR: PostgreSQL not ready." >&2; exit 1; fi
  sleep 1
done

echo "[backend] Waiting for Redis ..."
for i in $(seq 1 60); do
  if redis-cli -h 127.0.0.1 -p "$REDIS_PORT" ping >/dev/null 2>&1; then
    break
  fi
  if [ "$i" -eq 60 ]; then echo "[backend] ERROR: Redis not ready." >&2; exit 1; fi
  sleep 1
done

# Idempotent migrations/seeding (extension + create_all + seed). Must finish
# before Uvicorn starts accepting traffic.
/usr/local/bin/migrate.sh

echo "[backend] Starting Uvicorn on $BACKEND_HOST:$BACKEND_PORT ..."
cd /app/backend
exec python3 -m uvicorn src.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" --workers 1
