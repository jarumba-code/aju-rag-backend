"""
RAG orchestration layer for the AJU Knowledge Management Platform.

Provides:
  generate_rag_response()  — full non-streaming response (used by /api/v1/query)
  stream_rag_response()    — async SSE generator (used by /api/v1/query/stream)
  answer_query()           — backward-compatible wrapper

Per-request structured telemetry is emitted at INFO level using the key
``rag_telemetry`` so log aggregators can parse it without scanning full message text.
No API keys, credentials, or document content are included in log output.
"""

import asyncio
import logging
import os
import re
import time
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import AsyncSessionLocal
from src.models import ChatMessage, Conversation, KnowledgeSource, SystemSetting, UnansweredQuery
from src.services.retrieval import retrieve_relevant_chunks
from src.services.llm import complete_chat, stream_chat, LLM_MODEL, ChatResult
from src.services.sse import format_sse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalize_query_text(text: str) -> str:
    normalized = text.lower()
    normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


async def get_system_setting(db: AsyncSession, key: str, default: str) -> str:
    result = await db.execute(select(SystemSetting).filter(SystemSetting.key == key))
    setting = result.scalars().first()
    return setting.value if setting else default


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


# ---------------------------------------------------------------------------
# Shared pipeline helpers
# ---------------------------------------------------------------------------

async def _get_or_create_conversation(
    db: AsyncSession,
    conversation_id: Optional[str],
    persona: str,
    department_id: Optional[int],
) -> Conversation:
    if conversation_id:
        try:
            conversation_uuid = uuid.UUID(conversation_id)
            result = await db.execute(
                select(Conversation).where(Conversation.id == conversation_uuid)
            )
            conv = result.scalars().first()
            if conv:
                return conv
        except ValueError:
            pass
    conv = Conversation(persona=persona, department_id=department_id)
    db.add(conv)
    await db.flush()
    return conv


async def _fetch_history(db: AsyncSession, conversation_id: uuid.UUID) -> List[ChatMessage]:
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.created_at.asc())
        .limit(6)
    )
    return result.scalars().all()


def _build_context_and_sources(chunks) -> tuple[str, List[str], float]:
    """Returns (context_str, source_titles, avg_similarity)."""
    if not chunks:
        return "No relevant context found.", [], 0.0

    context_parts = []
    source_titles = []
    for chunk in chunks:
        title = chunk.source_title or "Knowledge Base"
        context_parts.append(f"[{title} (Similarity: {chunk.similarity_score:.2f})]: {chunk.chunk_content}")
        if title not in source_titles:
            source_titles.append(title)

    avg_sim = sum(c.similarity_score for c in chunks) / len(chunks)
    return "\n\n".join(context_parts), source_titles, avg_sim


def _build_messages(history: List[ChatMessage], context_str: str, query: str) -> List[Dict[str, str]]:
    system_instruction = (
        "You are the assistant for Arthur Jarvis University. "
        "Use the retrieved context to answer the user. "
        "If the information is not provided in the context, say so clearly."
    )
    message_history = [
        {"role": msg.role, "content": msg.content}
        for msg in history
        if msg.role in {"user", "assistant"}
    ]
    return [
        {"role": "system", "content": f"{system_instruction}\n\nContext:\n{context_str}"},
        *message_history,
        {"role": "user", "content": query},
    ]


def _compute_confidence(chunks, gap_reason: Optional[str], avg_similarity: float) -> Optional[float]:
    if gap_reason or not chunks:
        return 0.0
    return min(avg_similarity * 1.2, 1.0)


# ---------------------------------------------------------------------------
# Non-streaming RAG response
# ---------------------------------------------------------------------------

async def generate_rag_response(
    db: AsyncSession,
    query: str,
    persona: str = "public",
    department_id: Optional[int] = None,
    conversation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a persona-aware response and persist the conversation history."""
    t_total_start = time.perf_counter()
    normalized_query = normalize_query_text(query)
    gap_reason: Optional[str] = None

    # --- Conversation / history ---
    conversation = await _get_or_create_conversation(db, conversation_id, persona, department_id)
    history = await _fetch_history(db, conversation.id)

    # --- Retrieval ---
    t_retrieval_start = time.perf_counter()
    try:
        retrieved_chunks = await retrieve_relevant_chunks(
            db, query=query, persona=persona, department_id=department_id
        )
    except Exception as exc:
        logger.error("Retrieval failed: %s", exc)
        retrieved_chunks = []
        gap_reason = "retrieval_error"
    retrieval_latency_ms = (time.perf_counter() - t_retrieval_start) * 1000

    # --- Prompt build ---
    t_prompt_start = time.perf_counter()
    context_str, source_titles, avg_similarity = _build_context_and_sources(retrieved_chunks)
    messages = _build_messages(history, context_str, query)
    prompt_build_latency_ms = (time.perf_counter() - t_prompt_start) * 1000

    if not retrieved_chunks and not gap_reason:
        gap_reason = "no_sources"

    # --- LLM ---
    try:
        result: ChatResult = await complete_chat(messages=messages)
        answer_text = result.answer
        llm_latency_ms = result.llm_latency_ms
        prompt_tokens = result.prompt_tokens
        completion_tokens = result.completion_tokens
    except Exception as exc:
        logger.error("LLM call failed: %s", exc)
        answer_text = "An error occurred while communicating with the inference model."
        llm_latency_ms = 0.0
        prompt_tokens = None
        completion_tokens = None
        gap_reason = gap_reason or "llm_refused"

    confidence_score = _compute_confidence(retrieved_chunks, gap_reason, avg_similarity)
    total_latency_ms = (time.perf_counter() - t_total_start) * 1000

    # --- Structured telemetry log ---
    logger.info(
        "rag_telemetry retrieval_ms=%.1f prompt_ms=%.1f llm_ms=%.1f total_ms=%.1f "
        "chunks=%d avg_sim=%.3f confidence=%.3f prompt_tokens=%s completion_tokens=%s",
        retrieval_latency_ms,
        prompt_build_latency_ms,
        llm_latency_ms,
        total_latency_ms,
        len(retrieved_chunks),
        avg_similarity,
        confidence_score or 0.0,
        prompt_tokens,
        completion_tokens,
    )

    # --- Log unanswered ---
    if gap_reason:
        asyncio.create_task(
            log_unanswered_query(
                query_text=query,
                normalized_query=normalized_query,
                reason=gap_reason,
                confidence_score=confidence_score,
                retrieved_documents=len(retrieved_chunks),
                conversation_id=conversation.id,
                user_id=None,
                metadata={"context_count": len(source_titles)},
            )
        )

    # --- Persist chat ---
    db.add_all([
        ChatMessage(conversation_id=conversation.id, role="user", content=query),
        ChatMessage(conversation_id=conversation.id, role="assistant", content=answer_text, sources=source_titles),
    ])
    await db.commit()

    return {
        "answer": answer_text,
        "sources": source_titles,
        "conversation_id": str(conversation.id),
        "confidence_met": bool(retrieved_chunks),
        "confidence_score": confidence_score,
        "telemetry": {
            "retrieval_latency_ms": round(retrieval_latency_ms, 1),
            "prompt_build_latency_ms": round(prompt_build_latency_ms, 1),
            "llm_latency_ms": round(llm_latency_ms, 1),
            "total_latency_ms": round(total_latency_ms, 1),
            "retrieved_chunk_count": len(retrieved_chunks),
            "avg_similarity_score": round(avg_similarity, 3),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        },
    }


# ---------------------------------------------------------------------------
# Streaming RAG response
# ---------------------------------------------------------------------------

async def stream_rag_response(
    db: AsyncSession,
    query: str,
    persona: str = "public",
    department_id: Optional[int] = None,
    conversation_id: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """
    Async generator yielding SSE frames for the streaming endpoint.
    Reuses the same retrieval, access control, and prompt construction as
    generate_rag_response — no business logic is duplicated.
    """
    t_total_start = time.perf_counter()
    normalized_query = normalize_query_text(query)
    gap_reason: Optional[str] = None

    # start event
    yield format_sse("start", {"query": query, "persona": persona})

    # --- Conversation / history ---
    conversation = await _get_or_create_conversation(db, conversation_id, persona, department_id)
    history = await _fetch_history(db, conversation.id)

    # --- Retrieval ---
    t_retrieval_start = time.perf_counter()
    try:
        retrieved_chunks = await retrieve_relevant_chunks(
            db, query=query, persona=persona, department_id=department_id
        )
    except Exception as exc:
        logger.error("Streaming retrieval failed: %s", exc)
        yield format_sse("error", {"detail": "Retrieval failed. Cannot answer query."})
        return
    retrieval_latency_ms = (time.perf_counter() - t_retrieval_start) * 1000

    # Emit citation events immediately so client can show sources while tokens stream
    for chunk in retrieved_chunks:
        yield format_sse("citation", {
            "source_title": chunk.source_title or "Knowledge Base",
            "similarity_score": round(chunk.similarity_score, 3),
            "chunk_id": chunk.chunk_id,
        })

    # --- Prompt build ---
    t_prompt_start = time.perf_counter()
    context_str, source_titles, avg_similarity = _build_context_and_sources(retrieved_chunks)
    messages = _build_messages(history, context_str, query)
    prompt_build_latency_ms = (time.perf_counter() - t_prompt_start) * 1000

    if not retrieved_chunks:
        gap_reason = "no_sources"

    yield format_sse("metadata", {
        "retrieved_chunk_count": len(retrieved_chunks),
        "avg_similarity_score": round(avg_similarity, 3),
        "retrieval_latency_ms": round(retrieval_latency_ms, 1),
    })

    # --- LLM streaming ---
    assembled_answer = ""
    llm_latency_ms = 0.0
    first_token_latency_ms = 0.0
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    had_error = False

    t_llm_start = time.perf_counter()
    async for event in stream_chat(messages=messages):
        if event.event_type == "first_token":
            first_token_latency_ms = (time.perf_counter() - t_llm_start) * 1000
            assembled_answer += event.text
            yield format_sse("token", {"text": event.text})

        elif event.event_type == "token":
            assembled_answer += event.text
            yield format_sse("token", {"text": event.text})

        elif event.event_type == "done":
            llm_latency_ms = event.llm_latency_ms
            prompt_tokens = event.prompt_tokens
            completion_tokens = event.completion_tokens

        elif event.event_type == "error":
            had_error = True
            gap_reason = gap_reason or "llm_error"
            yield format_sse("error", {"detail": event.error_detail})
            if not assembled_answer:
                # No partial answer — stop here
                return

    if had_error and not assembled_answer:
        return

    total_latency_ms = (time.perf_counter() - t_total_start) * 1000
    confidence_score = _compute_confidence(retrieved_chunks, gap_reason, avg_similarity)

    # --- Structured telemetry ---
    logger.info(
        "rag_stream_telemetry retrieval_ms=%.1f prompt_ms=%.1f llm_ms=%.1f "
        "first_token_ms=%.1f total_ms=%.1f chunks=%d confidence=%.3f",
        retrieval_latency_ms,
        prompt_build_latency_ms,
        llm_latency_ms,
        first_token_latency_ms,
        total_latency_ms,
        len(retrieved_chunks),
        confidence_score or 0.0,
    )

    # --- Log unanswered ---
    if gap_reason:
        asyncio.create_task(
            log_unanswered_query(
                query_text=query,
                normalized_query=normalized_query,
                reason=gap_reason,
                confidence_score=confidence_score,
                retrieved_documents=len(retrieved_chunks),
                conversation_id=conversation.id,
                user_id=None,
                metadata={"context_count": len(source_titles), "streaming": True},
            )
        )

    # --- Persist chat ---
    if assembled_answer:
        db.add_all([
            ChatMessage(conversation_id=conversation.id, role="user", content=query),
            ChatMessage(
                conversation_id=conversation.id,
                role="assistant",
                content=assembled_answer,
                sources=source_titles,
            ),
        ])
        await db.commit()

    # --- done event with full metadata ---
    yield format_sse("done", {
        "answer": assembled_answer,
        "conversation_id": str(conversation.id),
        "confidence_score": confidence_score,
        "confidence_met": bool(retrieved_chunks),
        "sources": source_titles,
        "telemetry": {
            "retrieval_latency_ms": round(retrieval_latency_ms, 1),
            "prompt_build_latency_ms": round(prompt_build_latency_ms, 1),
            "llm_latency_ms": round(llm_latency_ms, 1),
            "first_token_latency_ms": round(first_token_latency_ms, 1),
            "total_latency_ms": round(total_latency_ms, 1),
            "retrieved_chunk_count": len(retrieved_chunks),
            "avg_similarity_score": round(avg_similarity, 3),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        },
    })


# ---------------------------------------------------------------------------
# Backward-compatible wrapper
# ---------------------------------------------------------------------------

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