#!/bin/bash
# Container entrypoint (runs before supervisord becomes PID 1).
# 1. Bootstraps PostgreSQL data dir on first start (no-op on restart).
# 2. Prepares the Redis persistence directory.
# 3. Execs supervisord, which manages postgres / redis / backend / frontend.
set -euo pipefail

echo "[entrypoint] AJU RAG single-container starting ..."

# PostgreSQL bootstrap (idempotent; never destroys existing data).
/usr/local/bin/init-postgres.sh

# Redis persistence directory (backed by the /data/redis Docker volume).
mkdir -p /data/redis
# redis-server runs as root in this image, so root ownership is sufficient.
chmod 700 /data/redis

# Supervisor state dir.
mkdir -p /tmp

echo "[entrypoint] Handing off to supervisord ..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
