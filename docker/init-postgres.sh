#!/bin/bash
# Initialise the PostgreSQL 16 cluster inside the single container.
# - First start with an empty $PGDATA: runs initdb, creates role + database,
#   and enables the pgvector `vector` extension the application requires.
# - Restarts with existing $PGDATA: does NOTHING destructive (data preserved).
set -euo pipefail

PGDATA="${PGDATA:-/var/lib/postgresql/data}"
POSTGRES_USER="${POSTGRES_USER:-rag_user}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-change_me_in_production}"
POSTGRES_DB="${POSTGRES_DB:-school_rag}"

# Escape single quotes for safe interpolation into SQL string literals.
ESCAPED_USER="${POSTGRES_USER//\'/\'\'}"
ESCAPED_PASSWORD="${POSTGRES_PASSWORD//\'/\'\'}"
# Escape double quotes for safe interpolation into a SQL identifier.
ESCAPED_USER_IDENT="${POSTGRES_USER//\"/\"\"}"

mkdir -p "$PGDATA"
chown -R postgres:postgres "$PGDATA"
chmod 700 "$PGDATA"

if [ -s "$PGDATA/PG_VERSION" ]; then
  echo "[init-postgres] Existing cluster found in $PGDATA (PG $(cat "$PGDATA/PG_VERSION")). Skipping initdb."
  exit 0
fi

echo "[init-postgres] Initialising new PostgreSQL 16 cluster in $PGDATA ..."
gosu postgres /usr/lib/postgresql/16/bin/initdb -D "$PGDATA" --username=postgres --auth=trust

echo "[init-postgres] Starting temporary server for bootstrap ..."
gosu postgres /usr/lib/postgresql/16/bin/pg_ctl -D "$PGDATA" \
  -o "-c listen_addresses=127.0.0.1 -c port=5432" -w -t 120 start

cleanup() {
  echo "[init-postgres] Stopping temporary server ..."
  gosu postgres /usr/lib/postgresql/16/bin/pg_ctl -D "$PGDATA" -w -t 120 stop || true
}
trap cleanup EXIT

echo "[init-postgres] Creating role '$POSTGRES_USER' and database '$POSTGRES_DB' ..."
gosu postgres psql -h 127.0.0.1 -p 5432 -U postgres -v ON_ERROR_STOP=1 <<EOSQL
DO \$$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$ESCAPED_USER') THEN
    CREATE ROLE "$ESCAPED_USER_IDENT" WITH LOGIN PASSWORD '$ESCAPED_PASSWORD' CREATEDB;
  END IF;
END
\$$;
SELECT 'role ok' WHERE EXISTS (SELECT FROM pg_roles WHERE rolname = '$ESCAPED_USER');
EOSQL

if ! gosu postgres psql -h 127.0.0.1 -p 5432 -U postgres -lqt | cut -d'|' -f1 | grep -qw "$POSTGRES_DB"; then
  gosu postgres createdb -h 127.0.0.1 -p 5432 -U postgres -O "$POSTGRES_USER" "$POSTGRES_DB"
fi

# The application stores embeddings in a pgvector Vector(1536) column, so the
# extension must exist before SQLAlchemy create_all runs.
echo "[init-postgres] Enabling pgvector extension ..."
gosu postgres psql -h 127.0.0.1 -p 5432 -U postgres -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 \
  -c "CREATE EXTENSION IF NOT EXISTS vector;"

trap - EXIT
cleanup
echo "[init-postgres] Bootstrap complete."
