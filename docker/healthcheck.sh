#!/bin/bash
# Container HEALTHCHECK: healthy only when the core stack is actually usable.
# Uses the project's EXISTING health endpoint (GET /health) plus direct
# PostgreSQL / Redis / Next.js probes. Any failure => unhealthy.
set -uo pipefail

POSTGRES_USER="${POSTGRES_USER:-rag_user}"
POSTGRES_DB="${POSTGRES_DB:-school_rag}"
REDIS_PORT="${REDIS_PORT:-6379}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"

fail() { echo "healthcheck: $1" >&2; exit 1; }

pg_isready -h 127.0.0.1 -p 5432 -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1 \
  || fail "postgres not ready"

[ "$(redis-cli -h 127.0.0.1 -p "$REDIS_PORT" ping 2>/dev/null)" = "PONG" ] \
  || fail "redis not responding"

curl -fsS "http://127.0.0.1:${BACKEND_PORT}/health" -o /dev/null 2>&1 \
  || fail "fastapi /health not responding"

curl -fsS "http://127.0.0.1:${FRONTEND_PORT}/" -o /dev/null 2>&1 \
  || fail "next.js not responding"

echo "healthcheck: ok (postgres + redis + fastapi + next.js)"
exit 0
