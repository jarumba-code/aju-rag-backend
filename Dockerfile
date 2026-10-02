# ─────────────────────────────────────────────────────────────────────────────
# AJU RAG — single-container image (FastAPI + Next.js + PostgreSQL 16/pgvector + Redis 7)
#
#   docker build -t aju-rag .
#   docker run -p 3000:3000 -p 8000:8000 --env-file .env \
#     -v aju-pgdata:/var/lib/postgresql/data -v aju-redis:/data/redis aju-rag
#
# Only ports 3000 (Next.js) and 8000 (FastAPI) are exposed. PostgreSQL and
# Redis listen on the container loopback interface only and are reachable
# solely by the processes inside this container.
# No secrets are baked into this image: all credentials arrive at RUNTIME via
# environment variables (see .env.example). The real .env is never COPYed.
# ─────────────────────────────────────────────────────────────────────────────

# ─── Stage 1: build the Next.js frontend ──────────────────────────────────────
FROM node:20-bookworm-slim AS frontend-builder
WORKDIR /build

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
# NEXT_PUBLIC_* values are inlined into the client bundle at BUILD time.
# Default targets the single-container loopback layout (both ports published).
# For a non-localhost deployment, rebuild with:
#   --build-arg NEXT_PUBLIC_API_URL=https://api.example.com
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
RUN npm run build

# ─── Stage 2: vendor Python dependencies ─────────────────────────────────────
FROM python:3.11-slim-bookworm AS python-builder
WORKDIR /build
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir --prefix=/python-install -r requirements.txt \
 && ls /python-install/lib/python3.11/site-packages | head -5

# ─── Stage 3: runtime (PostgreSQL 16 + pgvector base) ────────────────────────
FROM pgvector/pgvector:pg16

ENV DEBIAN_FRONTEND=noninteractive \
    PGDATA=/var/lib/postgresql/data \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Runtime services + interpreter. gosu/postgres/pgvector come from the base image.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
      python3 \
      redis-server \
      supervisor \
 && rm -rf /var/lib/apt/lists/* \
 && test -x /usr/lib/postgresql/16/bin/postgres \
 && test -x /usr/bin/redis-server \
 && test -x /usr/bin/supervisord \
 && gosu --version \
 && python3 --version \
 && redis-server --version

# Node.js runtime for the Next.js standalone server (binary only; no npm needed).
COPY --from=node:20-bookworm-slim /usr/local/bin/node /usr/local/bin/node
RUN node --version

# Vendored Python dependencies (built against Python 3.11, matching bookworm's
# system python3). Verified importable on the next line — build fails early on
# any ABI mismatch instead of at container startup.
COPY --from=python-builder /python-install /python-install
ENV PYTHONPATH=/python-install/lib/python3.11/site-packages:/app/backend \
    PATH=/python-install/bin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
RUN python3 -c "import fastapi, sqlalchemy, asyncpg, pgvector, openai, fitz, jose, bcrypt; print('pydeps ok')"

# Application sources required at runtime (backend src + built frontend only).
COPY backend/src /app/backend/src
COPY docker/migrate_db.py /app/docker/migrate_db.py
COPY --from=frontend-builder /build/.next/standalone /app/frontend
COPY --from=frontend-builder /build/.next/static /app/frontend/.next/static
RUN test -f /app/frontend/server.js \
 && test -f /app/backend/src/main.py \
 && node --check /app/frontend/server.js \
 && python3 -m compileall -q /app/backend/src /app/docker/migrate_db.py

# Process supervision + service configuration + lifecycle scripts.
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY docker/redis.conf /etc/redis/redis.conf
COPY docker/entrypoint.sh docker/init-postgres.sh docker/migrate.sh \
     docker/run-backend.sh docker/run-frontend.sh docker/healthcheck.sh \
     /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh /usr/local/bin/init-postgres.sh \
             /usr/local/bin/migrate.sh /usr/local/bin/run-backend.sh \
             /usr/local/bin/run-frontend.sh /usr/local/bin/healthcheck.sh \
 && bash -n /usr/local/bin/entrypoint.sh \
 && bash -n /usr/local/bin/init-postgres.sh \
 && bash -n /usr/local/bin/migrate.sh \
 && bash -n /usr/local/bin/run-backend.sh \
 && bash -n /usr/local/bin/run-frontend.sh \
 && bash -n /usr/local/bin/healthcheck.sh

# Non-secret runtime defaults (mirrors backend/.env + app config defaults).
# Secrets (POSTGRES_PASSWORD, SECRET_KEY, ADMIN_*, OPENROUTER_API_KEY) MUST be
# supplied at `docker run` time via --env-file / -e. They are intentionally
# NOT set here.
ENV POSTGRES_USER=rag_user \
    POSTGRES_DB=school_rag \
    POSTGRES_HOST=localhost \
    POSTGRES_PORT=5432 \
    REDIS_HOST=localhost \
    REDIS_PORT=6379 \
    BACKEND_HOST=0.0.0.0 \
    BACKEND_PORT=8000 \
    FRONTEND_PORT=3000 \
    PORT=3000 \
    HOSTNAME=0.0.0.0 \
    NODE_ENV=production \
    CORS_ORIGINS=http://localhost:3000

VOLUME ["/var/lib/postgresql/data", "/data/redis"]

EXPOSE 3000 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=3 \
  CMD ["/usr/local/bin/healthcheck.sh"]

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
STOPSIGNAL SIGTERM
