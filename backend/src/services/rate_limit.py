"""
Per-IP rate limiting for every API endpoint.

A fixed window counter (default 10 requests per IP per 60s) is kept in Redis so the
limit holds across multiple backend workers/containers. When Redis is unreachable the
limiter falls back to an in-process counter — it still protects a single worker and
never takes the API down because the cache is missing.

Clients receive standard headers on every limited response:
``X-RateLimit-Limit``, ``X-RateLimit-Remaining``, ``X-RateLimit-Reset`` and, on 429,
``Retry-After``.
"""

from __future__ import annotations

import logging
import os
import time
from collections import defaultdict
from typing import Dict, List, Tuple

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.services.cache import get_redis

logger = logging.getLogger(__name__)

RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() not in {"0", "false", "no"}
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "10"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
RATE_LIMIT_EXEMPT_PATHS = {"/health", "/docs", "/redoc", "/openapi.json"}

_KEY_PREFIX = "aju:ratelimit:"

# Fallback store: ip -> list of request timestamps within the current window.
_local_hits: Dict[str, List[float]] = defaultdict(list)


def client_ip(request: Request) -> str:
    """
    Resolve the caller IP, honouring X-Forwarded-For so the limit applies to real
    clients rather than the reverse proxy when the app runs behind one.
    """
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"


async def _hit_redis(key: str, window_seconds: int) -> Tuple[int, int]:
    """Increment the window counter. Returns (count, seconds_until_reset)."""
    client = get_redis()
    if client is None:
        raise RuntimeError("redis disabled")
    async with client.pipeline(transaction=True) as pipe:
        pipe.incr(key)
        pipe.ttl(key)
        count, ttl = await pipe.execute()
    if ttl is None or ttl < 0:
        await client.expire(key, window_seconds)
        ttl = window_seconds
    return int(count), int(ttl)


def _hit_local(key: str, window_seconds: int) -> Tuple[int, int]:
    now = time.time()
    window_start = now - window_seconds
    hits = [ts for ts in _local_hits[key] if ts > window_start]
    hits.append(now)
    _local_hits[key] = hits
    reset_in = int(window_seconds - (now - hits[0])) + 1
    return len(hits), max(reset_in, 1)


async def check_rate_limit(
    identity: str,
    limit: int = RATE_LIMIT_REQUESTS,
    window_seconds: int = RATE_LIMIT_WINDOW_SECONDS,
) -> Tuple[bool, int, int]:
    """Consume one token for *identity*; returns (allowed, remaining, reset_seconds)."""
    key = f"{_KEY_PREFIX}{identity}"
    try:
        count, reset_seconds = await _hit_redis(key, window_seconds)
    except Exception:
        count, reset_seconds = _hit_local(key, window_seconds)
    remaining = max(limit - count, 0)
    return count <= limit, remaining, reset_seconds


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Applies the per-IP limit to every request except health/documentation probes."""

    async def dispatch(self, request: Request, call_next):
        if not RATE_LIMIT_ENABLED or request.url.path in RATE_LIMIT_EXEMPT_PATHS:
            return await call_next(request)

        if request.method == "OPTIONS":  # CORS preflight must never be throttled
            return await call_next(request)

        identity = client_ip(request)
        allowed, remaining, reset_seconds = await check_rate_limit(identity)

        if not allowed:
            logger.warning("Rate limit exceeded for IP=%s path=%s", identity, request.url.path)
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please retry shortly."},
                headers={
                    "Retry-After": str(reset_seconds),
                    "X-RateLimit-Limit": str(RATE_LIMIT_REQUESTS),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_seconds),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT_REQUESTS)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_seconds)
        return response
