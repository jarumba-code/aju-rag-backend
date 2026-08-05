# SCHOOL RAG Platform

A production-grade Retrieval-Augmented Generation (RAG) platform for intelligent document processing and question answering.

## Architecture

```
├── backend/          # FastAPI backend
│   ├── alembic/      # Database migrations
│   └── src/
│       ├── api/      # REST API (v1 + middlewares)
│       ├── core/     # Config, auth, settings
│       ├── db/       # Database models & sessions
│       ├── pipelines/# Ingestion & query pipelines
│       └── services/ # Core RAG services
│           ├── parsing/     # Document parsing (PDF, DOCX, etc.)
│           ├── chunking/    # Text chunking strategies
│           ├── embeddings/  # Embedding model integrations
│           ├── vectorstore/ # Vector DB operations
│           ├── reranking/   # Result reranking
│           └── llm/         # LLM provider integrations
├── frontend/         # Next.js frontend
│   └── src/
│       ├── app/      # App router (dashboard, auth, API routes)
│       ├── components/
│       ├── hooks/
│       └── lib/
├── docker/           # Docker Compose & Dockerfiles
├── docs/             # Documentation
├── scripts/          # Utility scripts
└── .github/workflows/# CI/CD pipelines
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

```bash
# 1. Copy environment variables
cp .env.example .env

# 2. Start infrastructure
docker compose -f docker/docker-compose.yml up -d

# 3. Start backend
cd backend && pip install -r requirements.txt && uvicorn src.main:app --reload

# 4. Start frontend
cd frontend && npm install && npm run dev
```

## License

MIT
