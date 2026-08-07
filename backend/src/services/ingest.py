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

from src.models import DocumentChunk, KnowledgeSource, ContentStatus, VisibilityLevel

load_dotenv(override=True)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# OpenRouter embedding client (shared config with rag.py)
# ---------------------------------------------------------------------------
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "openai/text-embedding-3-small")

_embedding_client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    default_headers={
        "HTTP-Referer": "https://arthurjarvisuniversity.edu.ng",
        "X-Title": "AJU Knowledge Management Platform",
    },
)

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
# 2. Async Batched Embedding Generation
# ---------------------------------------------------------------------------
EMBEDDING_BATCH_SIZE = 64  # OpenRouter / OpenAI supports up to ~2048 inputs


async def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generate 1536-dim embeddings for a list of texts via OpenRouter.
    Processes in batches of EMBEDDING_BATCH_SIZE to respect API limits.

    Returns a list of embedding vectors (one per input text).
    """
    if not texts:
        return []

    all_embeddings: List[List[float]] = []

    for batch_start in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = texts[batch_start : batch_start + EMBEDDING_BATCH_SIZE]
        try:
            response = await _embedding_client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=batch,
            )
            # Sort by index to guarantee order matches input
            sorted_data = sorted(response.data, key=lambda d: d.index)
            all_embeddings.extend([item.embedding for item in sorted_data])
        except Exception as e:
            logger.error(
                f"Embedding batch failed (items {batch_start}-"
                f"{batch_start + len(batch)}): {e}"
            )
            # Insert empty vectors so indices stay aligned
            all_embeddings.extend([[] for _ in batch])

    return all_embeddings


# ---------------------------------------------------------------------------
# 3. Full Ingestion Pipeline
# ---------------------------------------------------------------------------

async def process_and_store_document(
    db: AsyncSession,
    source_id: int,
    content: str,
    visibility: VisibilityLevel,
    department_id: Optional[int] = None,
) -> int:
    """
    End-to-end ingestion pipeline for a single document.

    1. Chunks the raw text with recursive splitting.
    2. Generates batched embeddings via OpenRouter.
    3. Bulk inserts DocumentChunk rows with replicated visibility & department_id.
    4. Updates the parent KnowledgeSource status to PUBLISHED.

    Returns the number of chunks created.
    """
    # --- Step 1: Chunk ---
    chunks = recursive_chunk_text(content, chunk_size=800, overlap=100)
    if not chunks:
        logger.warning(f"Source {source_id}: no chunks produced from content.")
        return 0

    logger.info(f"Source {source_id}: split into {len(chunks)} chunks.")

    # --- Step 2: Embed (fire-and-forget for now — vectors stored when pgvector is ready) ---
    embeddings = await generate_embeddings(chunks)
    logger.info(f"Source {source_id}: generated {len(embeddings)} embeddings.")

    # --- Step 3: Bulk persist chunks ---
    chunk_objects = [
        DocumentChunk(
            source_id=source_id,
            chunk_content=chunk_text,
            visibility=visibility,
            department_id=department_id,
            vector_embedding=embedding if embedding else None,
        )
        for chunk_text, embedding in zip(chunks, embeddings)
    ]
    db.add_all(chunk_objects)

    # --- Step 4: Mark source as PUBLISHED ---
    from sqlalchemy import update

    await db.execute(
        update(KnowledgeSource)
        .where(KnowledgeSource.id == source_id)
        .values(status=ContentStatus.PUBLISHED)
    )

    await db.commit()
    logger.info(
        f"Source {source_id}: persisted {len(chunk_objects)} chunks, status → PUBLISHED."
    )
    return len(chunk_objects)
