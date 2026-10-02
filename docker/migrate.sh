#!/bin/bash
# Run database initialisation/migrations safely before the API accepts traffic.
# Uses ONLY the project's existing mechanism:
#   1. CREATE EXTENSION IF NOT EXISTS vector   (pgvector, required by models)
#   2. SQLAlchemy Base.metadata.create_all     (same as app startup_event)
#   3. seed_db.init_and_seed_db()              (idempotent insert-if-not-exists)
# Nothing here is destructive: no DROP, no delete, no re-seed overwrite.
set -euo pipefail

POSTGRES_USER="${POSTGRES_USER:-rag_user}"
POSTGRES_DB="${POSTGRES_DB:-school_rag}"

echo "[migrate] Waiting for PostgreSQL to accept connections ..."
for i in $(seq 1 60); do
  if pg_isready -h 127.0.0.1 -p 5432 -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then
    echo "[migrate] PostgreSQL is ready."
    break
  fi
  if [ "$i" -eq 60 ]; then
    echo "[migrate] ERROR: PostgreSQL did not become ready in time." >&2
    exit 1
  fi
  sleep 1
done

echo "[migrate] Running database initialisation (extension + create_all + seed) ..."
cd /app/backend
python3 /app/docker/migrate_db.py
echo "[migrate] Database initialisation complete."
