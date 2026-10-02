"""Admin document-management API (PDF upload, list, delete).

Security: every route in this router is protected by the shared ``X-API-Key``
auth dependency (see ``src.main.admin_api_key_header``). The router is mounted
in ``src.main`` *with that dependency applied*, so all admin endpoints require a
valid admin key and are never exposed publicly.

Ingestion reuses the single existing ingestion pipeline
(``process_and_store_document``) after extracting text from the uploaded PDF via
PyMuPDF (``fitz``). No second/chunking embedding system is created here.
"""
import hashlib
import logging
from typing import Optional

import fitz  # PyMuPDF (see backend/requirements.txt)
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models import ContentStatus, Document, KnowledgeSource, VisibilityLevel
from src.services.ingest import process_and_store_document
from src.services.audit import record_audit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def _extract_pdf_text(file_bytes: bytes) -> str:
    """Extract plain text from raw PDF bytes using PyMuPDF."""
    try:
        with fitz.open(stream=file_bytes, filetype="pdf") as doc:
            pages = [page.get_text() for page in doc]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to parse PDF: {exc}",
        ) from exc

    text = "\n\n".join(p for p in pages if p and p.strip()).strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No extractable text was found in the uploaded PDF.",
        )
    return text


@router.post("/documents/upload", summary="Upload and index a PDF document")
async def upload_document(
    file: UploadFile = File(...),
    department: Optional[str] = Form(default=None),
    doc_type: Optional[str] = Form(default=None),
    session: AsyncSession = Depends(get_db),
    request: Request = None,
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported.",
        )

    file_bytes = await file.read()
    content = _extract_pdf_text(file_bytes)
    file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    # Parent source metadata (public by default for admin-uploaded documents).
    source = KnowledgeSource(
        title=file.filename,
        status=ContentStatus.DRAFT,
        visibility=VisibilityLevel.PUBLIC,
    )
    session.add(source)
    await session.flush()  # generate source ID

    try:
        await process_and_store_document(
            db=session,
            source_id=source.id,
            content=content,
            visibility=VisibilityLevel.PUBLIC,
            title=file.filename,
            department=department,
            doc_type=doc_type or "pdf",
        )
    except ValueError as exc:  # duplicate-content protection from the pipeline
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive path
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest document: {exc}",
        ) from exc

    # The pipeline flushed the Document row in this same transaction.
    document = (
        await session.execute(select(Document).where(Document.file_hash == file_hash))
    ).scalar_one()
    await session.commit()

    # Record audit log
    client_ip = request.client.host if request and request.client else None
    await record_audit(
        db=session,
        action="document_upload",
        status="success",
        user_role="admin",
        resource_type="document",
        resource_id=str(document.id),
        details={"filename": file.filename, "department": department, "doc_type": doc_type or "pdf"},
        ip_address=client_ip,
    )
    await session.commit()

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
async def delete_document(document_id: str, session: AsyncSession = Depends(get_db), request: Request = None):
    result = await session.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Record audit log before deletion
    client_ip = request.client.host if request and request.client else None
    await record_audit(
        db=session,
        action="document_delete",
        status="success",
        user_role="admin",
        resource_type="document",
        resource_id=document_id,
        details={"filename": document.filename or document.title},
        ip_address=client_ip,
    )

    await session.delete(document)
    await session.commit()
    return {"status": "deleted", "document_id": document_id}
