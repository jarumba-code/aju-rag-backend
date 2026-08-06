from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_db
from src.models import Document
from src.services.ingest import client as openai_client, process_and_ingest_pdf

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.post("/documents/upload", summary="Upload and index a PDF document")
async def upload_document(
    file: UploadFile = File(...),
    department: str | None = Form(default=None),
    doc_type: str | None = Form(default=None),
    session: AsyncSession = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported.",
        )

    file_bytes = await file.read()
    try:
        document = await process_and_ingest_pdf(
            session=session,
            openai_client=openai_client,
            file_bytes=file_bytes,
            filename=file.filename,
            department=department,
            doc_type=doc_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive path
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest document: {exc}",
        ) from exc

    return {
        "status": "success",
        "document_id": str(document.id),
        "filename": document.filename or document.title,
        "department": document.department,
        "doc_type": document.doc_type,
    }


@router.get("/documents", summary="List indexed documents")
async def list_documents(session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Document).order_by(Document.created_at.desc()))
    documents = result.scalars().all()
    return [
        {
            "id": str(document.id),
            "filename": document.filename or document.title,
            "file_hash": document.file_hash,
            "department": document.department,
            "doc_type": document.doc_type,
            "chunk_count": document.chunk_count,
            "created_at": document.created_at.isoformat(),
        }
        for document in documents
    ]


@router.delete("/documents/{document_id}", summary="Delete a document and its chunks")
async def delete_document(document_id: str, session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    await session.delete(document)
    await session.commit()
    return {"status": "deleted", "document_id": document_id}
