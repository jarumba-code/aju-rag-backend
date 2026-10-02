# AJU RAG — single-container deployment

One Docker image (`aju-rag`) that runs the **entire** stack as a single
deployable unit: PostgreSQL 16 + pgvector, Redis 7, FastAPI backend, and the
Next.js frontend. Processes are managed by **supervisord** (PID 1) — not by
fragile shell `&` backgrounding.

## Architecture

```text
┌──────────────────────────── container: aju-rag ────────────────────────────┐
│ supervisord (PID 1)                                                        │
│  ├─ postgres  → gosu postgres postgres -D /var/lib/postgresql/data \      │
│  │               -c listen_addresses=127.0.0.1  (loopback only)            │
│  ├─ redis     → redis-server /etc/redis/redis.conf (bind 127.0.0.1, AOF)   │
│  ├─ backend   → run-backend.sh: wait pg+redis → migrate.sh → uvicorn :8000 │
│  └─ frontend  → run-frontend.sh: wait /health → node server.js :3000       │
└────────────────────────────────────────────────────────────────────────────┘
  host publishes ONLY 3000 (Next.js) and 8000 (FastAPI).
```

> **Note — image `EXPOSE` metadata:** `docker inspect` shows `5432/tcp` alongside
> `3000`/`8000`. That entry is inherited metadata from the `pgvector/pgvector:pg16`
> base image (Docker has no `UNEXPOSE`). It publishes nothing: Postgres binds
> `127.0.0.1` inside the container and `docker run` maps only `-p 3000:3000
> -p 8000:8000`. Never add `-p 5432:5432` / `-p 6379:6379`.

## Debugging inside the container

```bash
docker exec -it aju-rag supervisorctl -c /etc/supervisor/conf.d/supervisord.conf status
docker exec -it aju-rag gosu postgres psql -h 127.0.0.1 -U rag_user -d school_rag
docker exec -it aju-rag redis-cli -h 127.0.0.1 ping
```

(`supervisorctl` needs the explicit `-c` flag because supervisord runs from a
non-default config path.)

Image stages (`Dockerfile`):

| Stage | Base | Purpose |
|---|---|---|
| `frontend-builder` | `node:20-bookworm-slim` | `npm ci` + `next build` (standalone output) |
| `python-builder` | `python:3.11-bookworm-slim` | `pip install --prefix=/python-install -r backend/requirements.txt` |
| runtime | `pgvector/pgvector:pg16` | Postgres 16 + pgvector prebuilt; adds python3, redis-server, node binary, supervisor, app sources |

## Startup sequence

1. `entrypoint.sh` → `init-postgres.sh`: if `$PGDATA` is empty, `initdb`,
   create `$POSTGRES_USER` / `$POSTGRES_DB`, `CREATE EXTENSION vector`.
   If data exists → **no-op** (never destructive).
2. `entrypoint.sh` → prepares `/data/redis` → `exec supervisord`.
3. `postgres` + `redis` start under supervisord (autostart + autorestart).
4. `run-backend.sh`: waits `pg_isready` + `redis-cli ping` → `migrate.sh`
   (`CREATE EXTENSION IF NOT EXISTS vector`, then the project's own
   `seed_db.init_and_seed_db()` = `create_all` + insert-if-not-exists seeding)
   → `uvicorn src.main:app --host 0.0.0.0 --port 8000`.
5. `run-frontend.sh`: waits `GET /health` → `node server.js` on port 3000.
6. `HEALTHCHECK` (`healthcheck.sh`) passes only when **all four** respond:
   `pg_isready`, `redis-cli ping`, `GET :8000/health`, `GET :3000/`.

Migration safety: the container reuses the project's existing mechanism
(`create_all` + idempotent seed). No Alembic exists in this repo (the README
mention is aspirational), and no second migration system was introduced.

## Build / run / restart

```bash
# Build (run from the REPO ROOT, not backend/)
docker build -t aju-rag .

# First run (NAMED volumes preserve data across container replacement)
docker run -d --name aju-rag \
  -p 3000:3000 -p 8000:8000 \
  --env-file .env \
  -v aju-pgdata:/var/lib/postgresql/data \
  -v aju-redis:/data/redis \
  aju-rag

# Follow startup
docker logs -f aju-rag
docker ps                                   # STATUS should become (healthy)

# App endpoints
#   Frontend: http://localhost:3000
#   Backend:  http://localhost:8000  (health: http://localhost:8000/health)

# Restart (data survives: volumes are external to the container lifecycle)
docker stop aju-rag
docker start aju-rag

# Recreate the container WITHOUT losing data (volumes are reused)
docker rm aju-rag
docker run -d --name aju-rag -p 3000:3000 -p 8000:8000 \
  --env-file .env \
  -v aju-pgdata:/var/lib/postgresql/data \
  -v aju-redis:/data/redis aju-rag

# Full reset (DESTROYS all ingested data — opt-in only)
docker rm -f aju-rag
docker volume rm aju-pgdata aju-redis
```

## Volumes

| Mount | Purpose | Required |
|---|---|---|
| `aju-pgdata:/var/lib/postgresql/data` | All application state (documents, chunks/vectors, users, analytics, audit) | **yes** |
| `aju-redis:/data/redis` | Redis AOF + RDB (cache/rate-limit state; app code is stub-only today) | recommended |

No other volumes are needed: PDF uploads are parsed in memory and stored in
Postgres; embeddings/LLM calls go to OpenRouter (no local model cache).

## Environment

All configuration arrives at **run time** via `--env-file .env` / `-e`.
See `.env.example` for the full documented list. Minimum production set:

```text
POSTGRES_PASSWORD=<strong>
SECRET_KEY=<64-char random>
ADMIN_PASSWORD_HASH=<bcrypt hash>   # or ADMIN_API_KEY for automation
OPENROUTER_API_KEY=<key>            # required for answers + embeddings
```

`NEXT_PUBLIC_API_URL` is the one exception: it is inlined into the browser
bundle at **build** time. Rebuild with
`--build-arg NEXT_PUBLIC_API_URL=...` when the public API origin differs.

## Known limitations / tradeoffs (intentional, documented)

1. **Non-standard co-location.** Postgres + Redis + two app servers in one
   container deliberately trades the Docker "one process per container" norm
   for single-unit portability. Consequences: you cannot scale/restart tiers
   independently; resource limits apply to the whole unit; orchestration
   health is container-granular (mitigated by per-process `autorestart` and
   a 4-way healthcheck).
2. **Vertical scaling only.** One Uvicorn worker, one Next.js server. For
   more throughput, run bigger hosts or multiple whole-unit containers behind
   a load balancer with sticky sessions (each unit owns its own Postgres).
3. **No read replicas / managed-DB features.** Backups = volume snapshots /
   `pg_dump` against the containerised DB; point-in-time recovery and
   failover of a managed Postgres are unavailable.
4. **Redis is currently a provisioned stub.** No backend code path issues
   Redis commands yet (rate limiting returns `False` unconditionally). It runs
   with AOF persistence so enabling caching later needs no re-architecture,
   but today its volume holds no load-bearing data.
5. **LLM/embeddings are remote.** The unit is self-contained except for
   OpenRouter network access; without `OPENROUTER_API_KEY` (or network),
   retrieval runs but generation/embedding calls fail gracefully.
6. **Build-time frontend URL.** Changing the public API origin requires an
   image rebuild (`NEXT_PUBLIC_API_URL` is a client-bundle constant).
7. **Single-host volumes.** `aju-pgdata`/`aju-redis` are local Docker volumes;
   multi-host deployment needs shared storage or per-host units.
8. **Trust auth on loopback.** Postgres `initdb` uses trust authentication,
   acceptable because the database binds `127.0.0.1` and is never published
   (`EXPOSE` lists only 3000/8000). Do not publish 5432/6379.
