import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, UploadFile, File, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from src.api.admin import router as admin_router
from src.config import settings
from src.db import init_db, get_db
from src.rag import stream_rag_response, ingest_document
from src.suggested_questions import get_suggested_questions, record_user_query

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ─── Lifespan (Startup / Shutdown) ──────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Execute CREATE EXTENSION IF NOT EXISTS vector; and table creation
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized successfully.")
    yield


# ─── FastAPI Instance ────────────────────────────────────────────────────────

app = FastAPI(
    title="Arthur Jarvis University RAG Chat API",
    description="RAG-powered chat widget backend for AJU",
    version="1.0.0",
    lifespan=lifespan,
)

# ─── CORS Configurations ─────────────────────────────────────────────────────

# Parse origins from settings and include default variations
allowed_origins = [
    origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()
]
# Ensure common development and production variations are supported
extra_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "https://arthurjarvisuniversity.edu.ng",
    "http://arthurjarvisuniversity.edu.ng",
]
for origin in extra_origins:
    if origin not in allowed_origins:
        allowed_origins.append(origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin_router)


# ─── Request Schemas ─────────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    message: str


# ─── API Endpoints ───────────────────────────────────────────────────────────


@app.get("/health", summary="Health Check", tags=["System"])
async def health_check():
    """Returns service health status."""
    return {"status": "ok", "service": "AJU RAG Chat API"}


@app.post("/api/chat", summary="Stream RAG Response")
async def chat_endpoint(body: ChatRequest, session: AsyncSession = Depends(get_db)):
    """
    Accepts user question, searches pgvector, logs user query to track analytics,
    and returns a streamed LLM answer.
    """
    if not body.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Message cannot be empty"
        )

    # 1. Record user query asynchronously for analytics/suggested questions
    try:
        await record_user_query(session, body.message)
    except Exception as e:
        logger.error(f"Error logging user query: {e}")

    # 2. Return streaming response from LLM using retrieved context
    return StreamingResponse(
        stream_rag_response(body.message, session),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/suggested", summary="Fetch Suggested Questions")
async def suggested_endpoint(session: AsyncSession = Depends(get_db)):
    """
    Returns the top and recent questions asked by users.
    Falls back to pre-seeded defaults if no questions exist in DB.
    """
    questions = await get_suggested_questions(session, limit=5)
    return {"questions": questions}


@app.post("/api/upload", summary="Quick Ingest PDF Document")
async def upload_endpoint(
    file: UploadFile = File(...), session: AsyncSession = Depends(get_db)
):
    """
    Endpoint for uploading school documentation.
    Parses PDF, chunks, embeds, and saves inside vector DB.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Only PDF files are allowed.",
        )

    try:
        file_bytes = await file.read()
        doc = await ingest_document(file_bytes, file.filename, session)
        return {
            "status": "success",
            "message": f"Successfully ingested {file.filename}",
            "document_id": str(doc.id),
        }
    except Exception as e:
        logger.error(f"Ingestion error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest document: {str(e)}",
        )
