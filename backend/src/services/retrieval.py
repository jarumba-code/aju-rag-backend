import logging
import os
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import DocumentChunk, VisibilityLevel
from src.schemas.retrieval import RetrievalResult
from src.services.embeddings import generate_embeddings

logger = logging.getLogger(__name__)

RAG_TOP_K = int(os.getenv("RAG_TOP_K", "4"))
RAG_SIMILARITY_THRESHOLD = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.70"))

async def retrieve_relevant_chunks(
    db: AsyncSession,
    query: str,
    persona: str = "public",
    department_id: Optional[int] = None,
    limit: int = RAG_TOP_K,
    similarity_threshold: float = RAG_SIMILARITY_THRESHOLD,
) -> List[RetrievalResult]:
    """
    Perform pgvector semantic similarity search.
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
    if persona == "public":
        stmt = stmt.filter(DocumentChunk.visibility == VisibilityLevel.PUBLIC)
    elif persona == "student":
        stmt = stmt.filter(DocumentChunk.visibility.in_([VisibilityLevel.PUBLIC, VisibilityLevel.STUDENT]))
    elif persona == "staff":
        stmt = stmt.filter(DocumentChunk.visibility.in_([VisibilityLevel.PUBLIC, VisibilityLevel.STUDENT, VisibilityLevel.STAFF]))
    else:
        # Fallback to public if unknown persona
        stmt = stmt.filter(DocumentChunk.visibility == VisibilityLevel.PUBLIC)

    # 4. Department Filtering
    if department_id is not None:
        stmt = stmt.filter(DocumentChunk.department_id == department_id)
        
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
    
    logger.info(f"Retrieved {len(retrieval_results)} chunks for query (Top-K: {limit}, Threshold: {similarity_threshold})")
    return retrieval_results
