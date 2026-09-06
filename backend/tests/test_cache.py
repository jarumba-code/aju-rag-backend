"""Cache key derivation and graceful degradation when Redis is unavailable."""

import json

import pytest

from src.schemas.retrieval import RetrievalFilters
from src.services import cache


def test_embedding_keys_depend_on_model_and_text():
    assert cache.embedding_key("m1", "hello") == cache.embedding_key("m1", "hello")
    assert cache.embedding_key("m1", "hello") != cache.embedding_key("m2", "hello")
    assert cache.embedding_key("m1", "hello") != cache.embedding_key("m1", "hello!")
    # Raw text must never end up in the key.
    assert "hello" not in cache.embedding_key("m1", "hello")


def test_response_key_separates_persona_and_filters():
    base = cache.response_key("fees", "public", "-")
    assert base != cache.response_key("fees", "student", "-")
    assert base != cache.response_key(
        "fees", "public", cache.fingerprint_filters({"department": "law"})
    )


def test_filter_fingerprint_is_order_independent():
    a = cache.fingerprint_filters({"doc_type": "pdf", "department": "law"})
    b = cache.fingerprint_filters({"department": "law", "doc_type": "pdf"})
    assert a == b
    assert json.loads(a) == {"department": "law", "doc_type": "pdf"}
    assert cache.fingerprint_filters(None) == "-"
    assert cache.fingerprint_filters(RetrievalFilters().fingerprint()) == "-"


@pytest.mark.asyncio
async def test_cache_disabled_behaves_as_permanent_miss(monkeypatch):
    monkeypatch.setattr(cache, "CACHE_ENABLED", False)
    monkeypatch.setattr(cache, "_client", None)

    assert await cache.get_cached_embeddings("m", ["a"]) == {}
    await cache.set_cached_embeddings("m", [("a", [0.1])])  # must not raise
    assert await cache.get_cached_response("q", "public", "-") is None
    await cache.set_cached_response("q", "public", "-", {"answer": "x"})
    assert await cache.invalidate_response_cache() == 0


@pytest.mark.asyncio
async def test_cache_errors_do_not_propagate(monkeypatch):
    class BrokenClient:
        async def mget(self, keys):
            raise ConnectionError("redis down")

        async def get(self, key):
            raise ConnectionError("redis down")

    monkeypatch.setattr(cache, "get_redis", lambda: BrokenClient())

    assert await cache.get_cached_embeddings("m", ["a"]) == {}
    assert await cache.get_cached_response("q", "public", "-") is None
