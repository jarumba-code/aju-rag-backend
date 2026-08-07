import asyncio
import logging
import os
import re
import uuid
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import AsyncSessionLocal
from src.models import ChatMessage, Conversation, KnowledgeSource, SystemSetting, UnansweredQuery

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "meta-llama/llama-3.3-70b-instruct")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "openai/text-embedding-3-small")


def get_openai_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
        default_headers={
            "HTTP-Referer": "https://arthurjarvisuniversity.edu.ng",
            "X-Title": "AJU Knowledge Management Platform",
        },
    )


async def get_system_setting(db: AsyncSession, key: str, default: str) -> str:
    """Fetch dynamic system settings from database."""
    result = await db.execute(select(SystemSetting).filter(SystemSetting.key == key))
    setting = result.scalars().first()
    return setting.value if setting else default


async def retrieve_relevant_chunks(
    db: AsyncSession,
    query: str,
    persona: str = "public",
    department_id: Optional[int] = None,
    limit: int = 4,
) -> List[KnowledgeSource]:
    """Retrieve a small set of knowledge sources relevant to the incoming query."""
    stmt = select(KnowledgeSource)
    if department_id is not None:
        stmt = stmt.filter(KnowledgeSource.department_id == department_id)

    result = await db.execute(stmt.limit(limit))
    sources = result.scalars().all()

    if not sources:
        return []

    keywords = [word.lower() for word in query.split() if word.isalnum()]
    if not keywords:
        return sources[:limit]

    scored_sources: List[tuple[int, KnowledgeSource]] = []
    for source in sources:
        haystack = " ".join(
            filter(None, [source.title, getattr(source, "content", None), getattr(source, "content_type", None)])
        ).lower()
        score = sum(1 for keyword in keywords if keyword in haystack)
        scored_sources.append((score, source))

    scored_sources.sort(key=lambda item: item[0], reverse=True)
    return [source for _, source in scored_sources[:limit]]


def normalize_query_text(text: str) -> str:
    normalized = text.lower()
    normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


async def log_unanswered_query(
    query_text: str,
    normalized_query: str,
    reason: str,
    confidence_score: Optional[float],
    retrieved_documents: int,
    conversation_id: Optional[uuid.UUID] = None,
    user_id: Optional[uuid.UUID] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    try:
        async with AsyncSessionLocal() as session:
            unanswered = UnansweredQuery(
                query_text=query_text,
                normalized_query=normalized_query,
                reason=reason,
                confidence_score=confidence_score,
                retrieved_documents=retrieved_documents,
                conversation_id=conversation_id,
                user_id=user_id,
                metadata=metadata,
            )
            session.add(unanswered)
            await session.commit()
    except Exception as exc:
        logger.warning("Failed to log unanswered query: %s", exc)


async def generate_rag_response(
    db: AsyncSession,
    query: str,
    persona: str = "public",
    department_id: Optional[int] = None,
    conversation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a persona-aware response and persist the conversation history."""
    conversation = None
    if conversation_id:
        try:
            conversation_uuid = uuid.UUID(conversation_id)
        except ValueError:
            conversation_uuid = None
        if conversation_uuid:
            result = await db.execute(select(Conversation).where(Conversation.id == conversation_uuid))
            conversation = result.scalars().first()

    if conversation is None:
        conversation = Conversation(persona=persona, department_id=department_id)
        db.add(conversation)
        await db.flush()

    history_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation.id)
        .order_by(ChatMessage.created_at.asc())
        .limit(6)
    )
    history = history_result.scalars().all()

    sources = await retrieve_relevant_chunks(db, query=query, persona=persona, department_id=department_id)
    context_chunks = [
        f"[{getattr(source, 'title', 'Knowledge')}]: {getattr(source, 'content', getattr(source, 'content_type', ''))}"
        for source in sources
        if getattr(source, 'content', None) or getattr(source, 'title', None)
    ]

    message_history = [
        {"role": msg.role, "content": msg.content}
        for msg in history
        if msg.role in {"user", "assistant"}
    ]

    system_instruction = (
        "You are the assistant for Arthur Jarvis University. Use the retrieved context to answer the user. "
        "If the information is not provided in the context, say so clearly."
    )
    context_str = "\n\n".join(context_chunks) if context_chunks else "No relevant context found."

    messages = [
        {"role": "system", "content": f"{system_instruction}\n\nContext:\n{context_str}"},
        *message_history,
        {"role": "user", "content": query},
    ]

    gap_reason: Optional[str] = None
    confidence_score: Optional[float] = None
    retrieved_documents = len(sources)
    normalized_query = normalize_query_text(query)

    if not sources:
        gap_reason = "no_sources"
    
    try:
        client = get_openai_client()
        completion = await client.chat.completions.create(model=LLM_MODEL, messages=messages, temperature=0.2)
        answer_text = completion.choices[0].message.content or ""
    except Exception as exc:
        logger.error("OpenRouter LLM completion error: %s", exc)
        answer_text = "An error occurred while communicating with the inference model."
        gap_reason = gap_reason or "llm_refused"

    # Rough confidence estimate based on context availability
    if not gap_reason and not context_chunks:
        gap_reason = "low_confidence"
        confidence_score = 0.0
    elif not gap_reason:
        confidence_score = 1.0

    if gap_reason:
        asyncio.create_task(
            log_unanswered_query(
                query_text=query,
                normalized_query=normalized_query,
                reason=gap_reason,
                confidence_score=confidence_score,
                retrieved_documents=retrieved_documents,
                conversation_id=conversation.id if conversation else None,
                user_id=None,
                metadata={"context_count": len(context_chunks)},
            )
        )

    user_message = ChatMessage(conversation_id=conversation.id, role="user", content=query)
    assistant_message = ChatMessage(
        conversation_id=conversation.id,
        role="assistant",
        content=answer_text,
        sources=[source.title for source in sources if getattr(source, "title", None)],
    )
    db.add_all([user_message, assistant_message])
    await db.commit()

    return {
        "answer": answer_text,
        "sources": [source.title for source in sources if getattr(source, "title", None)],
        "conversation_id": str(conversation.id),
        "confidence_met": bool(context_chunks),
    }


async def answer_query(
    db: AsyncSession,
    query: str,
    persona: str = "public",
    department_id: Optional[int] = None,
    conversation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Backward-compatible wrapper around generate_rag_response."""
    return await generate_rag_response(
        db=db,
        query=query,
        persona=persona,
        department_id=department_id,
        conversation_id=conversation_id,
    )