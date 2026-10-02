#!/bin/bash
# Frontend program wrapper (managed by supervisord).
# Gates on the FastAPI health endpoint, then starts the Next.js standalone server.
set -euo pipefail

BACKEND_PORT="${BACKEND_PORT:-8000}"

echo "[frontend] Waiting for FastAPI health endpoint ..."
for i in $(seq 1 120); do
  if curl -fsS "http://127.0.0.1:${BACKEND_PORT}/health" -o /dev/null 2>&1; then
    echo "[frontend] FastAPI is healthy."
    break
  fi
  if [ "$i" -eq 120 ]; then echo "[frontend] ERROR: FastAPI never became healthy." >&2; exit 1; fi
  sleep 1
done

echo "[frontend] Starting Next.js standalone server on ${HOSTNAME:-0.0.0.0}:${PORT:-3000} ..."
cd /app/frontend
exec /usr/local/bin/node server.js
