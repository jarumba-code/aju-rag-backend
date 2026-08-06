import hashlib
import io
import logging
import os
from pathlib import Path
from typing import Any

import pypdf
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Document, DocumentChunk

logger = logging.getLogger(__name__)
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL"),
)

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1500,
    chunk_overlap=150,
    separators=["\n\n", "\n", " ", ""],
)


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def extract_text_from_pdf(file_bytes: bytes) -> list[dict[str, Any]]:
    reader = pypdf.PdfReader(io.BytesIO(file_bytes))
    pages: list[dict[str, Any]] = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append({"page": page_number, "text": text.strip()})
    return pages


async def embed_texts(texts: list[str], openai_client: AsyncOpenAI | None = None) -> list[list[float]]:
    if not texts:
        return []
    embedding_client = openai_client or client
    response = await embedding_client.embeddings.create(
        model=os.getenv("EMBEDDING_MODEL", "openai/text-embedding-3-small"),
        input=texts,
    )
    return [item.embedding for item in response.data]


async def process_and_ingest_pdf(
    session: AsyncSession,
    openai_client: AsyncOpenAI,
    file_bytes: bytes,
    filename: str,
    department: str | None = None,
    doc_type: str | None = None,
) -> Document:
    if not file_bytes:
        raise ValueError("Uploaded file is empty.")
    if not filename.lower().endswith(".pdf"):
        raise ValueError("Only PDF files are supported.")

    source_hash = compute_sha256(file_bytes)

    existing_result = await session.execute(
        select(Document).where(Document.file_hash == source_hash)
    )
    existing_doc = existing_result.scalar_one_or_none()
    if existing_doc is not None:
        raise ValueError("A document with the same content already exists.")

    document = Document(
        title=filename,
        filename=filename,
        file_hash=source_hash,
        department=department,
        doc_type=doc_type or "general",
        category=department or "general",
        source_hash=source_hash,
        source_name=filename,
    )
    session.add(document)
    await session.flush()

    pages = extract_text_from_pdf(file_bytes)
    if not pages:
        raise ValueError("No readable text could be extracted from the PDF.")

    chunk_texts: list[str] = []
    chunk_meta: list[dict[str, Any]] = []
    for page in pages:
        chunks = splitter.split_text(page["text"])
        for chunk in chunks:
            chunk_texts.append(chunk)
            chunk_meta.append({"page_number": page["page"]})

    if chunk_texts:
        embeddings = await embed_texts(chunk_texts, openai_client)
        for chunk, embedding, meta in zip(chunk_texts, embeddings, chunk_meta):
            session.add(
                DocumentChunk(
                    document_id=document.id,
                    content=chunk,
                    embedding=embedding,
                    page_number=meta["page_number"],
                )
            )

    document.chunk_count = len(chunk_texts)
    await session.commit()
    await session.refresh(document)
    return document


async def ingest_document(file_bytes: bytes, filename: str, session: AsyncSession) -> Document:
    return await process_and_ingest_pdf(session, client, file_bytes, filename)
