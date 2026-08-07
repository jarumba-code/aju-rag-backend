from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db, engine, Base
from src.models import KnowledgeSource, VisibilityLevel, ContentStatus
from src.rag import generate_rag_response
from src.services.ingest import process_and_store_document

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
    persona: str = Field("public", example="student")  # 'public', 'student', or 'staff'
    department_id: Optional[int] = Field(default=None, example=None, description="Scope results to a specific department (optional)")


class QueryResponse(BaseModel):
    answer: str
    sources: List[Any]
    confidence_met: bool


class IngestRequest(BaseModel):
    title: str = Field(..., example="AJU Student Handbook 2026")
    content: str = Field(..., example="Academic policies and departmental guidelines...")
    is_confidential: bool = Field(False, description="True for internal student/staff data only")
    department_id: Optional[int] = Field(default=None, example=None)
    category_id: Optional[int] = Field(default=None, example=None)


class IngestResponse(BaseModel):
    message: str
    source_id: int
    chunks_created: int = 0


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
        result = await generate_rag_response(
            db=db,
            query=payload.query,
            persona=payload.persona,
            department_id=payload.department_id,
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
        visibility = VisibilityLevel.STUDENT if payload.is_confidential else VisibilityLevel.PUBLIC

        # 1. Create the parent KnowledgeSource record
        new_source = KnowledgeSource(
            title=payload.title,
            visibility=visibility,
            department_id=payload.department_id,
            category_id=payload.category_id,
            status=ContentStatus.DRAFT  # Set to DRAFT until chunking completes
        )
        db.add(new_source)
        await db.flush()  # Get the ID without committing

        # 2. Run the chunking + embedding + persistence pipeline
        chunks_created = await process_and_store_document(
            db=db,
            source_id=new_source.id,
            content=payload.content,
            visibility=visibility,
            department_id=payload.department_id,
        )

        return IngestResponse(
            message=f"Document ingested successfully with {chunks_created} chunks.",
            source_id=new_source.id,
            chunks_created=chunks_created,
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {str(e)}"
        )