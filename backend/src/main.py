from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db, engine, Base
from src.models import KnowledgeSource
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


class QueryResponse(BaseModel):
    answer: str
    sources: List[str]
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


# --- Endpoints ---

@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "platform": "AJU RAG Backend"}


@app.post("/api/v1/query", response_model=QueryResponse, tags=["RAG Engine"])
async def query_rag(payload: QueryRequest, db: AsyncSession = Depends(get_db)):
    """
    Query the knowledge base with persona-aware context filtering.
    """
    try:
        result = await answer_query(db=db, query=payload.query, persona=payload.persona)
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