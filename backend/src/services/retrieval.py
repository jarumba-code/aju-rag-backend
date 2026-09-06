import logging
import os
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import Document, DocumentChunk, VisibilityLevel
from src.schemas.retrieval import RetrievalFilters, RetrievalResult
from src.services.embeddings import generate_embeddings

logger = logging.getLogger(__name__)

RAG_TOP_K = int(os.getenv("RAG_TOP_K", "4"))
RAG_SIMILARITY_THRESHOLD = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.70"))


def visibility_levels_for_persona(persona: str) -> List[VisibilityLevel]:
    """
    Map a persona to the set of visibility levels its retrieval may access.

    PUBLIC  -> {PUBLIC}
    STUDENT -> {PUBLIC, STUDENT}
    STAFF   -> {PUBLIC, STUDENT, STAFF}
    unknown -> {PUBLIC}  (fail closed — unknown callers only see public content)

    This is the *backend* security boundary: the frontend only selects a persona;
    the actual access decision always lives here.
    """
    key = (persona or "").lower()
    if key == "student":
        return [VisibilityLevel.PUBLIC, VisibilityLevel.STUDENT]
    if key == "staff":
        return [VisibilityLevel.PUBLIC, VisibilityLevel.STUDENT, VisibilityLevel.STAFF]
    # "public" and any unrecognised persona default to public-only content.
    return [VisibilityLevel.PUBLIC]


def _apply_metadata_filters(stmt, filters: RetrievalFilters):
    """
    Narrow the candidate set by document metadata before the top-k cut.

    Document-level attributes live on ``documents``; chunk-level ones are replicated
    onto ``document_chunks``, so only the document-level predicates need the join.
    """
    needs_document_join = any(
        value is not None
        for value in (
            filters.department,
            filters.doc_type,
            filters.created_after,
            filters.created_before,
        )
    )
    if needs_document_join:
        stmt = stmt.join(Document, DocumentChunk.document_id == Document.id)

    if filters.department is not None:
        stmt = stmt.filter(func.lower(Document.department) == filters.department.lower())
    if filters.doc_type is not None:
        stmt = stmt.filter(func.lower(Document.doc_type) == filters.doc_type.lower())
    if filters.created_after is not None:
        stmt = stmt.filter(Document.created_at >= filters.created_after)
    if filters.created_before is not None:
        stmt = stmt.filter(Document.created_at <= filters.created_before)
    if filters.department_id is not None:
        stmt = stmt.filter(DocumentChunk.department_id == filters.department_id)
    if filters.document_ids:
        stmt = stmt.filter(DocumentChunk.document_id.in_(filters.document_ids))
    if filters.source_ids:
        stmt = stmt.filter(DocumentChunk.source_id.in_(filters.source_ids))

    return stmt


async def retrieve_relevant_chunks(
    db: AsyncSession,
    query: str,
    persona: str = "public",
    department_id: Optional[int] = None,
    limit: int = RAG_TOP_K,
    similarity_threshold: float = RAG_SIMILARITY_THRESHOLD,
    filters: Optional[RetrievalFilters] = None,
) -> List[RetrievalResult]:
    """
    Perform pgvector semantic similarity search, optionally narrowed by metadata.
    """
    # 1. Generate query embedding
    query_embeddings = await generate_embeddings([query])
    if not query_embeddings or not query_embeddings[0]:
        logger.warning("Failed to generate embedding for query.")
        return []
    
    query_vector = query_embeddings[0]

    # 2. Base query
    # Compute similarity = 1 - cosine_distance
    similarity_col = (1 - DocumentChunk.vector_embedding.cosine_distance(query_vector)).label("similarity")
    
    stmt = select(DocumentChunk, similarity_col).options(
        selectinload(DocumentChunk.document),
        selectinload(DocumentChunk.source)
    )

    # 3. Access Control (Visibility Filtering)
    # The persona -> visibility mapping is enforced here on the backend — this is
    # the final security boundary, independent of anything the frontend sends.
    stmt = stmt.filter(DocumentChunk.visibility.in_(visibility_levels_for_persona(persona)))

    # 4. Department Filtering
    if department_id is not None:
        stmt = stmt.filter(DocumentChunk.department_id == department_id)

    # 4b. Metadata Filtering (department name, doc type, ingestion date, ids)
    if filters is not None and not filters.is_empty():
        stmt = _apply_metadata_filters(stmt, filters)

    # 5. Threshold and Ordering
    stmt = stmt.filter(similarity_col >= similarity_threshold)
    stmt = stmt.order_by(similarity_col.desc())
    stmt = stmt.limit(limit)

    result = await db.execute(stmt)
    rows = result.all()

    # 6. Map to structured output
    retrieval_results = []
    for chunk, similarity in rows:
        title = None
        if chunk.document and chunk.document.title:
            title = chunk.document.title
        elif chunk.source and chunk.source.title:
            title = chunk.source.title

        doc_type = chunk.document.doc_type if chunk.document else None
        dept = chunk.document.department if chunk.document else None

        retrieval_results.append(
            RetrievalResult(
                chunk_id=chunk.id,
                document_id=str(chunk.document_id) if chunk.document_id else "",
                source_id=chunk.source_id,
                chunk_content=chunk.chunk_content,
                similarity_score=float(similarity),
                source_title=title,
                department=dept,
                doc_type=doc_type,
                visibility=chunk.visibility.value if chunk.visibility else "",
            )
        )
    
    logger.info(
        "Retrieved %d chunks for query (Top-K: %d, Threshold: %.2f, Filters: %s)",
        len(retrieval_results),
        limit,
        similarity_threshold,
        filters.fingerprint() if filters is not None else {},
    )
    return retrieval_results
