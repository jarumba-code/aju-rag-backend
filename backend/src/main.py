from datetime import datetime
from fastapi import FastAPI, Depends, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database import Base, engine, get_db
from src.models import KnowledgeSource, UnansweredQuery
from src.rag import answer_query

app = FastAPI(
    title="AJU Knowledge Management Platform API",
    description="Persona-aware RAG engine backend for Arthur Jarvis University",
    version="1.0.0"
)

# Enable CORS for local development & frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Schemas ---

class QueryRequest(BaseModel):
    query: str = Field(..., example="What are the admission requirements for Software Engineering?")
    persona: str = Field("public", example="student")  # 'public' or 'student'
    conversation_id: Optional[str] = Field(default=None, example="123e4567-e89b-12d3-a456-426614174000")


class QueryResponse(BaseModel):
    answer: str
    sources: List[str]
    conversation_id: str
    confidence_met: bool


class IngestRequest(BaseModel):
    title: str = Field(..., example="AJU Student Handbook 2026")
    content: str = Field(..., example="Academic policies and departmental guidelines...")
    is_confidential: bool = Field(False, description="True for internal student/staff data only")
    department_id: Optional[int] = None
    category_id: Optional[int] = None


class IngestResponse(BaseModel):
    message: str
    source_id: int


class AnalyticsQueryParams(BaseModel):
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)
    reason: Optional[str] = None
    resolved: Optional[bool] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class AnalyticsPatch(BaseModel):
    resolved: Optional[bool] = None
    resolution_note: Optional[str] = None


# --- Endpoints ---

@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "platform": "AJU RAG Backend"}


@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def admin_api_key_header(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    if not settings.ADMIN_API_KEY or x_api_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return x_api_key


@app.get("/api/v1/analytics/gaps", tags=["Analytics"])
async def get_unanswered_gaps(
    limit: int = 20,
    offset: int = 0,
    reason: Optional[str] = None,
    resolved: Optional[bool] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    x_api_key: str = Depends(admin_api_key_header),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(UnansweredQuery)
    if reason is not None:
        stmt = stmt.where(UnansweredQuery.reason == reason)
    if resolved is not None:
        stmt = stmt.where(UnansweredQuery.resolved == resolved)
    if start_date is not None:
        stmt = stmt.where(UnansweredQuery.created_at >= start_date)
    if end_date is not None:
        stmt = stmt.where(UnansweredQuery.created_at <= end_date)

    total_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(total_stmt)
    total_gaps = total_result.scalar_one()

    result = await db.execute(stmt.order_by(UnansweredQuery.created_at.desc()).limit(limit).offset(offset))
    gaps = result.scalars().all()

    grouped = {}
    if total_gaps:
        summary_stmt = select(UnansweredQuery.reason, func.count().label("count")).group_by(UnansweredQuery.reason)
        if reason is not None:
            summary_stmt = summary_stmt.where(UnansweredQuery.reason == reason)
        if resolved is not None:
            summary_stmt = summary_stmt.where(UnansweredQuery.resolved == resolved)
        if start_date is not None:
            summary_stmt = summary_stmt.where(UnansweredQuery.created_at >= start_date)
        if end_date is not None:
            summary_stmt = summary_stmt.where(UnansweredQuery.created_at <= end_date)
        summary_result = await db.execute(summary_stmt)
        grouped = {row[0]: row[1] for row in summary_result.fetchall()}

    return {
        "total_gaps": total_gaps,
        "recent_gaps": [
            {
                "id": str(gap.id),
                "query_text": gap.query_text,
                "normalized_query": gap.normalized_query,
                "reason": gap.reason,
                "confidence_score": gap.confidence_score,
                "retrieved_documents": gap.retrieved_documents,
                "conversation_id": str(gap.conversation_id) if gap.conversation_id else None,
                "user_id": str(gap.user_id) if gap.user_id else None,
                "metadata": gap.metadata,
                "created_at": gap.created_at.isoformat() if gap.created_at else None,
                "resolved": gap.resolved,
                "resolution_note": gap.resolution_note,
            }
            for gap in gaps
        ],
        "grouped_by_reason": grouped,
    }


@app.get("/api/v1/analytics/gaps/top", tags=["Analytics"])
async def get_top_unanswered_gaps(
    limit: int = 20,
    x_api_key: str = Depends(admin_api_key_header),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(
            UnansweredQuery.normalized_query,
            func.count(UnansweredQuery.id).label("frequency"),
            func.max(UnansweredQuery.created_at).label("last_seen"),
        )
        .group_by(UnansweredQuery.normalized_query)
        .order_by(desc("frequency"))
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.fetchall()

    return [
        {
            "representative_query": row.normalized_query,
            "frequency": row.frequency,
            "last_seen": row.last_seen.isoformat() if row.last_seen else None,
        }
        for row in rows
    ]


@app.patch("/api/v1/analytics/gaps/{gap_id}", tags=["Analytics"])
async def patch_unanswered_gap(
    gap_id: str,
    payload: AnalyticsPatch,
    x_api_key: str = Depends(admin_api_key_header),
    db: AsyncSession = Depends(get_db),
):
    try:
        gap_uuid = uuid.UUID(gap_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid gap ID")

    result = await db.execute(select(UnansweredQuery).where(UnansweredQuery.id == gap_uuid))
    gap = result.scalars().first()
    if gap is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gap not found")

    if payload.resolved is not None:
        gap.resolved = payload.resolved
    if payload.resolution_note is not None:
        gap.resolution_note = payload.resolution_note

    await db.commit()
    await db.refresh(gap)

    return {
        "id": str(gap.id),
        "resolved": gap.resolved,
        "resolution_note": gap.resolution_note,
    }


@app.post("/api/v1/query", response_model=QueryResponse, tags=["RAG Engine"])
async def query_rag(payload: QueryRequest, db: AsyncSession = Depends(get_db)):
    """
    Query the knowledge base with persona-aware context filtering.
    """
    try:
        result = await answer_query(
            db=db,
            query=payload.query,
            persona=payload.persona,
            conversation_id=payload.conversation_id,
        )
        return QueryResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query execution failed: {str(e)}"
        )


@app.post("/api/v1/ingest", response_model=IngestResponse, status_code=status.HTTP_201_CREATED, tags=["Knowledge Base"])
async def ingest_document(payload: IngestRequest, db: AsyncSession = Depends(get_db)):
    """
    Ingest institutional content into the PostgreSQL database.
    """
    try:
        new_source = KnowledgeSource(
            title=payload.title,
            content=payload.content,
            is_confidential=payload.is_confidential,
            department_id=payload.department_id,
            category_id=payload.category_id,
            is_active=True
        )
        db.add(new_source)
        await db.commit()
        await db.refresh(new_source)

        return IngestResponse(
            message="Document ingested successfully.",
            source_id=new_source.id
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {str(e)}"
        )