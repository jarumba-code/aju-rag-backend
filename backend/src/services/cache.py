"""
Redis-backed caching for the AJU RAG platform.

Two caches share one connection pool:

  embeddings  — keyed by (model, text) sha256, stores the raw 1536-dim vector.
                Embeddings are deterministic per model, so this is a pure win:
                repeat queries and re-ingested duplicate chunks skip the API call.
  responses   — keyed by (persona, normalized query, retrieval filters), stores the
                finished answer + sources + confidence for a stateless first turn.

Every operation degrades gracefully: if Redis is unreachable the helpers log once
and behave as a permanent cache miss so the request path never fails on cache I/O.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any, Dict, List, Optional

import redis.asyncio as redis

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() not in {"0", "false", "no"}
EMBEDDING_CACHE_TTL = int(os.getenv("EMBEDDING_CACHE_TTL_SECONDS", str(60 * 60 * 24 * 30)))
RESPONSE_CACHE_TTL = int(os.getenv("RESPONSE_CACHE_TTL_SECONDS", str(60 * 15)))

_EMBEDDING_PREFIX = "aju:embed:"
_RESPONSE_PREFIX = "aju:resp:"

_client: Optional[redis.Redis] = None
_unavailable_logged = False


def get_redis() -> Optional[redis.Redis]:
    """Return the shared Redis client, or None when caching is disabled."""
    global _client
    if not CACHE_ENABLED:
        return None
    if _client is None:
        _client = redis.from_url(
            REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
    return _client


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def _note_unavailable(exc: Exception) -> None:
    global _unavailable_logged
    if not _unavailable_logged:
        logger.warning("Redis cache unavailable, continuing without cache: %s", exc)
        _unavailable_logged = True


def _digest(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Embedding cache
# ---------------------------------------------------------------------------

def embedding_key(model: str, text: str) -> str:
    return f"{_EMBEDDING_PREFIX}{_digest(model, text)}"


async def get_cached_embeddings(model: str, texts: List[str]) -> Dict[int, List[float]]:
    """Return {index_in_texts: vector} for the texts already cached."""
    client = get_redis()
    if client is None or not texts:
        return {}
    try:
        values = await client.mget([embedding_key(model, text) for text in texts])
    except Exception as exc:
        _note_unavailable(exc)
        return {}

    hits: Dict[int, List[float]] = {}
    for index, raw in enumerate(values):
        if not raw:
            continue
        try:
            vector = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(vector, list) and vector:
            hits[index] = vector
    return hits


async def set_cached_embeddings(model: str, pairs: List[tuple[str, List[float]]]) -> None:
    client = get_redis()
    if client is None or not pairs:
        return
    try:
        async with client.pipeline(transaction=False) as pipe:
            for text, vector in pairs:
                if not vector:
                    continue
                pipe.set(embedding_key(model, text), json.dumps(vector), ex=EMBEDDING_CACHE_TTL)
            await pipe.execute()
    except Exception as exc:
        _note_unavailable(exc)


# ---------------------------------------------------------------------------
# Response cache
# ---------------------------------------------------------------------------

def response_key(normalized_query: str, persona: str, filters_fingerprint: str) -> str:
    return f"{_RESPONSE_PREFIX}{_digest(normalized_query, persona.lower(), filters_fingerprint)}"


def fingerprint_filters(filters: Optional[Dict[str, Any]]) -> str:
    """Stable fingerprint of retrieval filters so different filters never share a cache entry."""
    if not filters:
        return "-"
    cleaned = {key: value for key, value in sorted(filters.items()) if value is not None}
    return json.dumps(cleaned, default=str, sort_keys=True)


async def get_cached_response(
    normalized_query: str, persona: str, filters_fingerprint: str
) -> Optional[Dict[str, Any]]:
    client = get_redis()
    if client is None:
        return None
    try:
        raw = await client.get(response_key(normalized_query, persona, filters_fingerprint))
    except Exception as exc:
        _note_unavailable(exc)
        return None
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


async def set_cached_response(
    normalized_query: str,
    persona: str,
    filters_fingerprint: str,
    payload: Dict[str, Any],
) -> None:
    client = get_redis()
    if client is None:
        return
    try:
        await client.set(
            response_key(normalized_query, persona, filters_fingerprint),
            json.dumps(payload, default=str),
            ex=RESPONSE_CACHE_TTL,
        )
    except Exception as exc:
        _note_unavailable(exc)


async def invalidate_response_cache() -> int:
    """
    Drop every cached answer. Called after ingestion/deletion changes the corpus,
    since previously cached answers may now be stale or incomplete.
    """
    client = get_redis()
    if client is None:
        return 0
    removed = 0
    try:
        async for key in client.scan_iter(match=f"{_RESPONSE_PREFIX}*", count=500):
            await client.delete(key)
            removed += 1
    except Exception as exc:
        _note_unavailable(exc)
    return removed
