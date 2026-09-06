# SCHOOL RAG Platform

A production-grade Retrieval-Augmented Generation (RAG) platform for intelligent document processing and question answering.

## Architecture

```
├── backend/              # FastAPI backend
│   ├── Dockerfile
│   ├── src/
│   │   ├── api/          # Admin REST API
│   │   ├── schemas/      # Pydantic schemas (retrieval filters, results)
│   │   ├── services/     # RAG services
│   │   │   ├── embeddings.py  # OpenRouter embeddings + Redis cache
│   │   │   ├── retrieval.py   # pgvector search + metadata filters
│   │   │   ├── cache.py       # Embedding & response caching
│   │   │   └── rate_limit.py  # Per-IP rate limiting middleware
│   │   ├── auth.py       # JWT / API-key admin auth
│   │   ├── models.py     # SQLAlchemy models
│   │   ├── rag.py        # RAG orchestration
│   │   └── main.py       # App entrypoint
│   └── tests/            # Pytest suite
├── frontend/             # Next.js frontend
│   ├── Dockerfile
│   └── src/
│       ├── app/          # App router (chat, admin, API routes)
│       ├── components/
│       └── lib/
└── docker-compose.yml    # Full stack: postgres/pgvector, redis, backend, frontend
```

## Tech Stack

| Layer       | Technology                          |
| ----------- | ----------------------------------- |
| Backend     | Python · FastAPI · SQLAlchemy       |
| Frontend    | Next.js · TypeScript · React        |
| Database    | PostgreSQL 16 + pgvector            |
| Cache       | Redis 7                             |
| Embeddings  | OpenAI / Sentence Transformers     |
| Vector DB   | pgvector (integrated w/ Postgres)   |
| LLM         | OpenAI / Anthropic / Local models   |

## Quick Start

Run the whole stack (postgres + pgvector, redis, backend, frontend) with Docker:

```bash
cp .env.example .env      # set OPENROUTER_API_KEY, ADMIN_PASSWORD_HASH, JWT_SECRET_KEY
docker compose up -d --build
```

Frontend: http://localhost:3000 · API docs: http://localhost:8000/docs

Local development without containers:

```bash
docker compose up -d postgres redis
cd backend && pip install -r requirements-dev.txt && uvicorn src.main:app --reload
cd frontend && npm install && npm run dev
```

Backend tests: `cd backend && pytest`

## Operational features

| Feature | Details |
| ------- | ------- |
| Rate limiting | `RATE_LIMIT_REQUESTS` (default 10) per IP per `RATE_LIMIT_WINDOW_SECONDS` (default 60) on every API endpoint; stricter throttle on admin login |
| Metadata-filtered retrieval | `filters` on `/api/v1/query`: `department`, `department_id`, `doc_type`, `document_ids`, `source_ids`, `created_after`, `created_before` — applied in SQL before vector top-k |
| Embedding cache | SHA-256 keyed Redis cache; only cache misses hit the provider |
| Response cache | Keyed by normalized query + persona + filters, invalidated on ingestion/deletion |

Caching and rate limiting fail open when Redis is unavailable.

## License

MIT
