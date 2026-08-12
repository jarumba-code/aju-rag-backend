"""Admin document-management API (PDF upload, list, delete)."""
import hashlib
import logging
from typing import Optional

import fitz
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import require_admin_auth
from src.database import get_db
from src.models import ContentStatus, Document, KnowledgeSource, VisibilityLevel
from src.services.audit import record_audit
from src.services.ingest import process_and_store_document

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["Admin Documents"],
    dependencies=[Depends(require_admin_auth)],
)


def _extract_pdf_text(file_bytes: bytes) -> str:
    try:
        with fitz.open(stream=file_bytes, filetype="pdf") as doc:
            pages = [page.get_text() for page in doc]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to parse PDF.",
        ) from exc

    text = "\n\n".join(page for page in pages if page and page.strip()).strip()
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

    source = KnowledgeSource(
        title=file.filename,
        status=ContentStatus.DRAFT,
        visibility=VisibilityLevel.PUBLIC,
    )
    session.add(source)
    await session.flush()

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
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except Exception as exc:
        await session.rollback()
        logger.exception("Document ingestion failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to ingest document.",
        ) from exc

    result = await session.execute(select(Document).where(Document.file_hash == file_hash))
    document = result.scalar_one_or_none()
    if document is None:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document ingestion completed without creating a document record.",
        )

    client_ip = request.client.host if request and request.client else None
    await record_audit(
        db=session,
        action="document_upload",
        status="success",
        user_role="admin",
        resource_type="document",
        resource_id=str(document.id),
        details={
            "filename": file.filename,
            "department": department,
            "doc_type": doc_type or "pdf",
        },
        ip_address=client_ip,
    )
    await session.commit()

    return {
        "status": "success",
        "document_id": str(document.id),
        "filename": document.filename or document.title,
        "department": document.department,
        "doc_type": document.doc_type,
        "chunk_count": document.chunk_count,
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
            "created_at": document.created_at.isoformat() if document.created_at else None,
        }
        for document in documents
    ]


@router.delete("/documents/{document_id}", summary="Delete a document and its chunks")
async def delete_document(
    document_id: str,
    session: AsyncSession = Depends(get_db),
    request: Request = None,
):
    result = await session.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

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
