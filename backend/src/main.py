import uuid
from datetime import datetime
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database import Base, engine, get_db
from src.models import KnowledgeSource, UnansweredQuery, VisibilityLevel, ContentStatus, Document, ChatAnalytics
from src.rag import answer_query, stream_rag_response
from src.services.ingest import process_and_store_document
from src.services.audit import record_audit, get_audit_logs
from src.suggested_questions import get_suggested_questions
from src.api.admin import router as admin_router
from src.auth import LoginRequest, LoginResponse, MeResponse, authenticate_admin, require_admin_auth

app = FastAPI(
    title="AJU Knowledge Management Platform API",
    description="Persona-aware RAG engine backend for Arthur Jarvis University",
    version="1.0.0"
)

# Enable CORS for local development & frontend clients (configured via env).
# Wildcard origins are NOT used — this is restrictable through CORS_ORIGINS.
cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()] or ["http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
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


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., example="old_strong_password")
    new_password: str = Field(..., example="new_strong_password")


@app.post("/api/v1/admin/auth/login", tags=["Admin Auth"])
async def admin_login(payload: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """
    Authenticate as an administrator using the configured admin password.

    On success, returns a short-lived bearer token that can be used to access
    protected admin endpoints. The token should be stored in an HttpOnly,
    Secure, SameSite cookie by the admin frontend.
    """
    client_ip = request.client.host if request.client else None
    result = await authenticate_admin(password=payload.password, db=db, client_ip=client_ip)
    
    # Record successful login
    await record_audit(
        db=db,
        action="login",
        status="success",
        user_role="admin",
        ip_address=client_ip,
        details={"method": "password"},
    )
    await db.commit()
    
    return result


@app.get("/api/v1/admin/auth/me", tags=["Admin Auth"])
async def admin_me(payload: dict = Depends(require_admin_auth)):
    """
    Return the current admin authentication state.

    Returns 401 if the request is not authenticated.
    """
    return {"authenticated": True, "role": payload.get("role", "admin")}


@app.post("/api/v1/admin/auth/logout", tags=["Admin Auth"])
async def admin_logout(payload: dict = Depends(require_admin_auth), db: AsyncSession = Depends(get_db), request: Request = None):
    """
    Invalidate the current admin session.

    With JWT this is a no-op on the server side (tokens are stateless and
    expire quickly), but the endpoint is provided so the frontend can clear
    its stored credentials.
    """
    client_ip = request.client.host if request and request.client else None
    await record_audit(
        db=db,
        action="logout",
        status="success",
        user_role="admin",
        ip_address=client_ip,
    )
    await db.commit()
    return {"authenticated": False}


@app.post("/api/v1/admin/auth/password", tags=["Admin Auth"])
async def change_password(payload: ChangePasswordRequest, request: Request, db: AsyncSession = Depends(get_db), auth: dict = Depends(require_admin_auth)):
    from sqlalchemy import select
    from src.models import SystemSetting
    import logging
    logger = logging.getLogger(__name__)

    client_ip = request.client.host if request.client else None
    
    # Verify current password
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == "admin_password_hash"))
    hash_setting = result.scalars().first()
    current_hash = hash_setting.value if hash_setting else (settings.ADMIN_PASSWORD_HASH or "").strip()
    
    from src.auth import verify_password, hash_password
    if not verify_password(payload.current_password, current_hash):
        logger.warning("Failed password change attempt from IP=%s", client_ip)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect.")
        
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password must be at least 8 characters.")
    
    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password must differ from current password.")
        
    new_hash = hash_password(payload.new_password)
    
    if hash_setting:
        hash_setting.value = new_hash
    else:
        new_setting = SystemSetting(key="admin_password_hash", value=new_hash)
        db.add(new_setting)
        
    # Update password_changed_at for session invalidation
    changed_at_res = await db.execute(select(SystemSetting).where(SystemSetting.key == "password_changed_at"))
    changed_at_setting = changed_at_res.scalars().first()
    now_ts = str(datetime.utcnow().timestamp())
    if changed_at_setting:
        changed_at_setting.value = now_ts
    else:
        db.add(SystemSetting(key="password_changed_at", value=now_ts))
        
    await db.commit()
    logger.info("Admin password changed successfully from IP=%s", client_ip)
    
    # Record password change
    await record_audit(
        db=db,
        action="password_change",
        status="success",
        user_role="admin",
        resource_type="settings",
        ip_address=client_ip,
    )
    await db.commit()
    
    return {"message": "Password changed successfully."}



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



@app.post("/api/v1/query/stream", tags=["RAG Engine"])
async def query_rag_stream(payload: QueryRequest, db: AsyncSession = Depends(get_db)):
    """
    Stream a persona-aware RAG response using Server-Sent Events.
    Events: start, citation, metadata, token, done, error.
    """
    async def event_generator():
        try:
            async for frame in stream_rag_response(
                db=db,
                query=payload.query,
                persona=payload.persona,
                conversation_id=payload.conversation_id,
            ):
                yield frame
        except Exception as exc:
            import json
            error_frame = f"event: error\ndata: {json.dumps({'detail': 'Internal server error during streaming.'})}\n\n"
            yield error_frame

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.post(
    "/api/v1/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Knowledge Base"],
    dependencies=[Depends(require_admin_auth)],
)
async def ingest_document(
    payload: IngestRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Ingest institutional content into the PostgreSQL database.

    Admin-only: requires either a valid JWT from POST /api/v1/admin/auth/login
    or the legacy X-API-Key header.
    """
    try:
        # Determine visibility level based on confidentiality flag
        visibility = VisibilityLevel.STUDENT if payload.is_confidential else VisibilityLevel.PUBLIC

        # 1. Create parent KnowledgeSource metadata
        new_source = KnowledgeSource(
            title=payload.title,
            visibility=visibility,
            department_id=payload.department_id,
            category_id=payload.category_id,
            status=ContentStatus.DRAFT
        )
        db.add(new_source)
        await db.flush()  # Generate source ID

        # 2. Process and store document text (creates Document and DocumentChunks)
        await process_and_store_document(
            db=db,
            source_id=new_source.id,
            content=payload.content,
            visibility=visibility,
            department_id=payload.department_id,
            title=payload.title
        )

        # 3. Commit entire transaction if all stages succeeded
        await db.commit()

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


@app.get("/api/v1/suggested", tags=["Suggestions"])
async def suggested_questions(
    limit: int = Query(default=5, ge=1, le=10),
    db: AsyncSession = Depends(get_db),
):
    """Return curated/popular suggested questions for the chat widget."""
    questions = await get_suggested_questions(db, limit=limit)
    return {"questions": questions}


# --- Admin Analytics & Audit Endpoints ---

@app.get("/api/v1/admin/analytics/summary", tags=["Admin Analytics"])
async def get_analytics_summary(
    x_api_key: str = Depends(admin_api_key_header),
    db: AsyncSession = Depends(get_db),
):
    """
    Return dashboard summary metrics for the admin portal.
    """
    # Total documents
    doc_count_result = await db.execute(select(func.count()).select_from(Document))
    total_documents = doc_count_result.scalar_one()

    # Total chunks
    chunk_count_result = await db.execute(select(func.count()).select_from(DocumentChunk))
    total_chunks = chunk_count_result.scalar_one()

    # Total queries answered (from chat analytics)
    answered_result = await db.execute(select(func.count()).select_from(ChatAnalytics))
    total_answered = answered_result.scalar_one()

    # Unanswered queries
    unanswered_result = await db.execute(
        select(func.count()).select_from(UnansweredQuery).where(UnansweredQuery.resolved == False)
    )
    total_unanswered = unanswered_result.scalar_one()

    # Average confidence from recent chat analytics
    avg_conf_result = await db.execute(select(func.avg(ChatAnalytics.similarity_score)))
    avg_confidence = avg_conf_result.scalar_one() or 0.0

    # Average latency
    avg_latency_result = await db.execute(select(func.avg(ChatAnalytics.response_time_ms)))
    avg_latency = avg_latency_result.scalar_one() or 0.0

    # Resolution rate
    total_gaps_result = await db.execute(select(func.count()).select_from(UnansweredQuery))
    total_gaps = total_gaps_result.scalar_one()
    resolved_gaps_result = await db.execute(
        select(func.count()).select_from(UnansweredQuery).where(UnansweredQuery.resolved == True)
    )
    resolved_gaps = resolved_gaps_result.scalar_one()
    resolution_rate = (resolved_gaps / total_gaps * 100) if total_gaps > 0 else 100.0

    return {
        "total_documents": total_documents,
        "total_chunks": total_chunks,
        "total_answered": total_answered,
        "total_unanswered": total_unanswered,
        "avg_confidence": round(avg_confidence, 2),
        "avg_latency_ms": round(avg_latency, 0),
        "resolution_rate": round(resolution_rate, 1),
    }


@app.get("/api/v1/admin/analytics/trends", tags=["Admin Analytics"])
async def get_analytics_trends(
    days: int = Query(default=7, ge=1, le=30),
    x_api_key: str = Depends(admin_api_key_header),
    db: AsyncSession = Depends(get_db),
):
    """
    Return time-series data for analytics charts.
    """
    from datetime import datetime, timedelta
    from collections import defaultdict

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # Query volume by day
    volume_result = await db.execute(
        select(
            func.date(ChatAnalytics.created_at).label("date"),
            func.count().label("count"),
        )
        .where(ChatAnalytics.created_at >= start_date)
        .group_by(func.date(ChatAnalytics.created_at))
        .order_by(func.date(ChatAnalytics.created_at))
    )
    volume_by_day = {str(row.date): row.count for row in volume_result.fetchall()}

    # Fill in missing days
    date_labels = []
    volume_data = []
    current = start_date.date()
    while current <= end_date.date():
        date_str = str(current)
        date_labels.append(current.strftime("%a"))
        volume_data.append(volume_by_day.get(date_str, 0))
        current += timedelta(days=1)

    # Source utilization (from document chunks)
    source_result = await db.execute(
        select(DocumentChunk.document_id, func.count().label("chunk_count"))
        .group_by(DocumentChunk.document_id)
        .order_by(func.count().desc())
        .limit(10)
    )
    source_utilization = [
        {"document_id": str(row.document_id), "chunk_count": row.chunk_count}
        for row in source_result.fetchall()
    ]

    return {
        "query_volume": {
            "labels": date_labels,
            "data": volume_data,
        },
        "source_utilization": source_utilization,
    }


@app.get("/api/v1/admin/audit-log", tags=["Admin Audit"])
async def get_audit_log(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    action: Optional[str] = None,
    status: Optional[str] = None,
    x_api_key: str = Depends(admin_api_key_header),
    db: AsyncSession = Depends(get_db),
):
    """
    Return audit log entries for the admin portal.
    """
    result = await get_audit_logs(
        db=db,
        limit=limit,
        offset=offset,
        action=action,
        status=status,
    )
    return result


@app.patch("/api/v1/admin/documents/{document_id}", tags=["Admin Documents"])
async def update_document(
    document_id: str,
    payload: dict = Depends(require_admin_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Placeholder for future document metadata updates.
    Currently returns a stub response to allow the API surface to grow.
    """
    return {"updated": False, "detail": "Document update not yet implemented."}


# Register the authenticated admin document-management router.
# The shared ``require_admin_auth`` dependency accepts both:
#  - legacy X-API-Key authentication, and
#  - new JWT bearer tokens from POST /api/v1/admin/auth/login.
# These endpoints are never exposed publicly.
app.include_router(
    admin_router,
    dependencies=[Depends(require_admin_auth)],
)