"""
Ingestion pipeline: chunking, embedding, and persistence for the AJU RAG system.

Pipeline:
  Raw Text -> Recursive Character Splitter (800 chars, 100 overlap)
           -> Batched OpenRouter Embedding (text-embedding-3-small, 1536-dim)
           -> Bulk insert into document_chunks with replicated visibility & department_id
"""

import logging
import os
from typing import List, Optional

from dotenv import load_dotenv
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Document, DocumentChunk, KnowledgeSource, ContentStatus, VisibilityLevel

load_dotenv(override=True)

logger = logging.getLogger(__name__)

from src.services.embeddings import generate_embeddings
# ---------------------------------------------------------------------------
# 1. Recursive Character Splitter
# ---------------------------------------------------------------------------
_DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


def recursive_chunk_text(
    text: str,
    chunk_size: int = 800,
    overlap: int = 100,
    separators: Optional[List[str]] = None,
) -> List[str]:
    """
    Split *text* into overlapping chunks using a recursive separator strategy.

    Tries each separator in order; when a split produces pieces smaller than
    *chunk_size* they are kept as-is, otherwise the next separator is tried
    on the oversized fragment.

    Returns a flat list of chunk strings, each ≤ *chunk_size* characters
    (best-effort — a single word longer than *chunk_size* is kept whole).
    """
    if separators is None:
        separators = _DEFAULT_SEPARATORS

    if not text or not text.strip():
        return []

    chunks: List[str] = []
    _recursive_split(text.strip(), chunk_size, overlap, separators, 0, chunks)
    return chunks


def _recursive_split(
    text: str,
    chunk_size: int,
    overlap: int,
    separators: List[str],
    sep_idx: int,
    out: List[str],
) -> None:
    """Internal recursive helper."""
    # Base case: text fits in one chunk
    if len(text) <= chunk_size:
        if text.strip():
            out.append(text.strip())
        return

    # If we've exhausted separators, hard-split by character window
    if sep_idx >= len(separators):
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            fragment = text[start:end].strip()
            if fragment:
                out.append(fragment)
            start += chunk_size - overlap
        return

    sep = separators[sep_idx]
    parts = text.split(sep) if sep else list(text)

    current_chunk = ""
    for part in parts:
        candidate = (current_chunk + sep + part) if current_chunk else part

        if len(candidate) <= chunk_size:
            current_chunk = candidate
        else:
            # Flush current_chunk
            if current_chunk.strip():
                if len(current_chunk) <= chunk_size:
                    out.append(current_chunk.strip())
                else:
                    _recursive_split(current_chunk, chunk_size, overlap, separators, sep_idx + 1, out)

            # If the new part itself is oversized, recurse deeper
            if len(part) > chunk_size:
                _recursive_split(part, chunk_size, overlap, separators, sep_idx + 1, out)
                current_chunk = ""
            else:
                current_chunk = part

    # Flush remaining
    if current_chunk.strip():
        if len(current_chunk) <= chunk_size:
            out.append(current_chunk.strip())
        else:
            _recursive_split(current_chunk, chunk_size, overlap, separators, sep_idx + 1, out)

    # Apply overlap: prepend tail of previous chunk to the next chunk
    if overlap > 0 and len(out) > 1:
        merged: List[str] = [out[0]]
        for i in range(1, len(out)):
            prev_tail = merged[-1][-overlap:]
            # Only prepend if it doesn't duplicate the start of the next chunk
            if not out[i].startswith(prev_tail):
                merged.append(prev_tail + " " + out[i])
            else:
                merged.append(out[i])
        out.clear()
        out.extend(merged)




# ---------------------------------------------------------------------------
# 3. Full Ingestion Pipeline
# ---------------------------------------------------------------------------

async def process_and_store_document(
    db: AsyncSession,
    source_id: int,
    content: str,
    visibility: VisibilityLevel,
    department_id: Optional[int] = None,
    title: Optional[str] = None,
) -> int:
    """
    End-to-end ingestion pipeline for a single document.

    1. Checks if Document with identical hash exists to prevent duplicate ingestion.
    2. Chunks the raw text with recursive splitting.
    3. Generates batched embeddings via OpenRouter.
    4. Creates and inserts Document record.
    5. Bulk inserts DocumentChunk rows with replicated visibility & department_id.
    6. Updates the parent KnowledgeSource status to PUBLISHED.

    Returns the number of chunks created.
    """
    # --- Step 1: Duplicate check & Hash generation ---
    import hashlib
    file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    from sqlalchemy import select
    existing_result = await db.execute(
        select(Document).where(Document.file_hash == file_hash)
    )
    existing_doc = existing_result.scalar_one_or_none()
    if existing_doc is not None:
        raise ValueError("A document with the same content already exists.")

    # --- Step 2: Chunk ---
    chunks = recursive_chunk_text(content, chunk_size=800, overlap=100)
    if not chunks:
        logger.warning(f"Source {source_id}: no chunks produced from content.")
        return 0

    logger.info(f"Source {source_id}: split into {len(chunks)} chunks.")

    # --- Step 3: Embed ---
    embeddings = await generate_embeddings(chunks)
    logger.info(f"Source {source_id}: generated {len(embeddings)} embeddings.")

    # --- Step 4: Create Document record ---
    document = Document(
        title=title or f"Doc_{source_id}",
        filename=None,
        file_hash=file_hash,
        department=str(department_id) if department_id is not None else None,
        doc_type="text",
        source_name="api_ingest",
        chunk_count=len(chunks),
    )
    db.add(document)
    await db.flush()  # Generate document ID

    # --- Step 5: Bulk persist chunks ---
    chunk_objects = [
        DocumentChunk(
            source_id=source_id,
            document_id=document.id,
            chunk_content=chunk_text,
            visibility=visibility,
            department_id=department_id,
            vector_embedding=embedding if embedding else None,
        )
        for chunk_text, embedding in zip(chunks, embeddings)
    ]
    db.add_all(chunk_objects)

    # --- Step 6: Mark source as PUBLISHED ---
    from sqlalchemy import update

    await db.execute(
        update(KnowledgeSource)
        .where(KnowledgeSource.id == source_id)
        .values(status=ContentStatus.PUBLISHED)
    )

    await db.flush()
    logger.info(
        f"Source {source_id}: persisted {len(chunk_objects)} chunks, status → PUBLISHED (flushed, waiting for commit)."
    )
    return len(chunk_objects)
