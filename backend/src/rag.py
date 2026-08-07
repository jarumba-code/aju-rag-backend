"""
RAG Query Engine for Arthur Jarvis University Knowledge Platform.

Pipeline:
  Query Text -> Embedding -> pgvector cosine similarity search -> LLM completion
"""

import os
import logging
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_
from openai import AsyncOpenAI

from src.models import DocumentChunk, KnowledgeSource, SystemSetting, ContentStatus, VisibilityLevel
from src.services.ingest import generate_embeddings

load_dotenv(override=True)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# OpenRouter LLM client
# ---------------------------------------------------------------------------
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
LLM_MODEL = os.getenv("DEFAULT_LLM_MODEL", "google/gemini-2.5-flash")

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    default_headers={
        "HTTP-Referer": "https://arthurjarvisuniversity.edu.ng",
        "X-Title": "AJU Knowledge Management Platform",
    },
)

# ---------------------------------------------------------------------------
# Persona System Prompts
# ---------------------------------------------------------------------------
PERSONA_PROMPTS: Dict[str, str] = {
    "public": (
        "You are the Official Public Information Assistant for Arthur Jarvis University (AJU), "
        "Nigeria. Your role is to serve prospective students, parents, and general visitors on the "
        "main university website.\n\n"
        "Tone: Welcoming, professional, and informative.\n"
        "Scope: ONLY provide information visible to the general public — admission requirements, "
        "programmes offered, campus life, contact information, and institutional news.\n"
        "Restrictions: NEVER reveal student records, internal policies, fee structures marked "
        "confidential, staff HR data, or any content marked as STUDENT or STAFF visibility.\n"
        "If a question falls outside your scope, politely guide the user to contact the relevant "
        "AJU office directly."
    ),
    "student": (
        "You are the Official Student Portal Assistant for Arthur Jarvis University (AJU), Nigeria. "
        "Your role is to support enrolled students navigating the student portal and administrative "
        "processes.\n\n"
        "Tone: Clear, direct, and step-by-step. Assume the user is a registered AJU student.\n"
        "Scope: Course registration, fee payment and clearance, exam clearance, portal login issues, "
        "result checking, accommodation booking, and departmental queries.\n"
        "When answering: Break down procedures into numbered steps wherever possible. "
        "Mention relevant portal menus or offices where applicable.\n"
        "If the information is not in the provided context, explicitly say so and direct the student "
        "to the appropriate office or portal section."
    ),
    "staff": (
        "You are the Internal Staff Knowledge Assistant for Arthur Jarvis University (AJU), Nigeria. "
        "Your role is to assist academic and administrative staff with institutional processes.\n\n"
        "Tone: Professional and concise.\n"
        "Scope: All visibility levels including STAFF-only content such as HR policies, internal "
        "memos, administrative procedures, and departmental guidelines.\n"
        "Provide accurate, direct answers based on the verified institutional context provided."
    ),
}


# ---------------------------------------------------------------------------
# Utility: Fetch a system setting from DB with fallback
# ---------------------------------------------------------------------------
async def get_system_setting(db: AsyncSession, key: str, default: str) -> str:
    """Fetch a dynamic setting from the system_settings table."""
    result = await db.execute(
        select(SystemSetting).filter(SystemSetting.key == key)
    )
    setting = result.scalars().first()
    return setting.value if setting else default


# ---------------------------------------------------------------------------
# Step 1: Retrieve relevant chunks via pgvector cosine similarity
# ---------------------------------------------------------------------------
async def retrieve_relevant_chunks(
    db: AsyncSession,
    query_text: str,
    persona: str,
    department_id: Optional[int] = None,
    limit: int = 5,
) -> List[DocumentChunk]:
    """
    Embed the query and run a pgvector cosine similarity search against document_chunks.

    Visibility rules:
      - public  → only PUBLIC chunks
      - student → PUBLIC + STUDENT chunks
      - staff   → PUBLIC + STUDENT + STAFF chunks

    Optionally filters by department_id (matches specified dept OR NULL dept).
    Returns the top-k most similar DocumentChunk rows ordered by cosine distance.
    """
    # 1. Generate query embedding
    embeddings = await generate_embeddings([query_text])
    if not embeddings or not embeddings[0]:
        logger.warning("Failed to generate query embedding — returning empty context.")
        return []

    query_vector = embeddings[0]

    # 2. Build visibility filter
    persona_lower = persona.lower()
    if persona_lower == "public":
        visibility_filter = DocumentChunk.visibility == VisibilityLevel.PUBLIC
    elif persona_lower == "student":
        visibility_filter = DocumentChunk.visibility.in_([
            VisibilityLevel.PUBLIC, VisibilityLevel.STUDENT
        ])
    else:  # staff or any other elevated role
        visibility_filter = DocumentChunk.visibility.in_([
            VisibilityLevel.PUBLIC, VisibilityLevel.STUDENT, VisibilityLevel.STAFF
        ])

    # 3. Build base query — cosine distance (<=> operator), only chunks WITH embeddings
    stmt = (
        select(DocumentChunk)
        .where(DocumentChunk.vector_embedding.isnot(None))
        .where(visibility_filter)
        .order_by(
            DocumentChunk.vector_embedding.op("<=>")(query_vector)
        )
        .limit(limit)
    )

    # 4. Optionally scope by department (match specified dept OR unassigned chunks)
    if department_id is not None:
        stmt = stmt.where(
            or_(
                DocumentChunk.department_id == department_id,
                DocumentChunk.department_id.is_(None),
            )
        )

    result = await db.execute(stmt)
    chunks = result.scalars().all()
    logger.info(
        f"retrieve_relevant_chunks: persona={persona}, dept={department_id}, "
        f"returned {len(chunks)} chunks."
    )
    return chunks


# ---------------------------------------------------------------------------
# Step 2: Generate RAG response from retrieved chunks + LLM
# ---------------------------------------------------------------------------
async def generate_rag_response(
    db: AsyncSession,
    query: str,
    persona: str = "public",
    department_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Full RAG pipeline:
      1. Retrieve top-k chunks via pgvector similarity.
      2. If no chunks found, return polite fallback.
      3. Format context and call LLM via OpenRouter.
      4. Return answer + sources metadata.
    """
    # 1. Retrieve chunks
    chunks = await retrieve_relevant_chunks(
        db=db,
        query_text=query,
        persona=persona,
        department_id=department_id,
        limit=5,
    )

    # 2. Fallback if no relevant context found
    if not chunks:
        fallback_msg = (
            "I'm sorry, I don't have verified institutional information to answer that query. "
            "Please contact the relevant AJU office directly or visit the official website at "
            "www.arthurjarvisuniversity.edu.ng."
        )
        return {
            "answer": fallback_msg,
            "sources": [],
            "confidence_met": False,
        }

    # 3. Build context string from chunks
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(f"[Context {i}]:\n{chunk.chunk_content}")
    context_str = "\n\n".join(context_parts)

    # 4. Select persona system prompt
    system_prompt = PERSONA_PROMPTS.get(persona.lower(), PERSONA_PROMPTS["public"])

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                f"--- VERIFIED INSTITUTIONAL CONTEXT ---\n{context_str}\n\n"
                f"--- STUDENT/USER QUESTION ---\n{query}\n\n"
                "Answer strictly based on the context above. "
                "If the context does not contain a clear answer, say so honestly."
            ),
        },
    ]

    # 5. Call LLM
    try:
        completion = await client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            temperature=0.2,
            max_tokens=1024,
        )
        answer_text = completion.choices[0].message.content or ""
    except Exception as e:
        logger.error(f"LLM completion error: {e}")
        answer_text = "An error occurred while generating the response. Please try again."

    # 6. Build sources metadata
    sources = [
        {
            "chunk_id": chunk.id,
            "source_id": chunk.source_id,
            "visibility": chunk.visibility.value if chunk.visibility else None,
        }
        for chunk in chunks
    ]

    return {
        "answer": answer_text,
        "sources": sources,
        "confidence_met": True,
    }


# ---------------------------------------------------------------------------
# Legacy shim — keeps the existing /api/v1/query endpoint working
# ---------------------------------------------------------------------------
async def answer_query(
    db: AsyncSession,
    query: str,
    persona: str = "public",
    department_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Thin wrapper around generate_rag_response for backward compatibility."""
    result = await generate_rag_response(
        db=db,
        query=query,
        persona=persona,
        department_id=department_id,
    )
    # Normalise sources to List[str] for the existing QueryResponse schema
    raw_sources = result.get("sources", [])
    if raw_sources and isinstance(raw_sources[0], dict):
        result["sources"] = [str(s["source_id"]) for s in raw_sources]
    return result