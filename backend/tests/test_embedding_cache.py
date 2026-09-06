"""Only cache misses are sent to the embedding provider, and ordering is preserved."""

import pytest

from src.services import embeddings


class _FakeClient:
    def __init__(self, create):
        self.embeddings = type("E", (), {"create": staticmethod(create)})()


class _FakeEmbeddingResponse:
    def __init__(self, vectors):
        self.data = [
            type("Item", (), {"index": index, "embedding": vector})()
            for index, vector in enumerate(vectors)
        ]


@pytest.mark.asyncio
async def test_cached_vectors_skip_the_provider(monkeypatch):
    sent_batches = []

    async def fake_create(model, input):
        sent_batches.append(list(input))
        return _FakeEmbeddingResponse([[float(len(text))] for text in input])

    stored = []

    async def fake_get(model, texts):
        return {0: [99.0]}  # "alpha" is already cached

    async def fake_set(model, pairs):
        stored.extend(pairs)

    monkeypatch.setattr(embeddings, "get_embedding_client", lambda: _FakeClient(fake_create))
    monkeypatch.setattr(embeddings, "get_cached_embeddings", fake_get)
    monkeypatch.setattr(embeddings, "set_cached_embeddings", fake_set)

    result = await embeddings.generate_embeddings(["alpha", "bb", "cccc"])

    assert sent_batches == [["bb", "cccc"]]
    assert result == [[99.0], [2.0], [4.0]]
    assert [text for text, _ in stored] == ["bb", "cccc"]


@pytest.mark.asyncio
async def test_empty_input_short_circuits(monkeypatch):
    async def fail(*args, **kwargs):  # pragma: no cover - must not be called
        raise AssertionError("provider should not be called")

    monkeypatch.setattr(embeddings, "get_embedding_client", lambda: _FakeClient(fail))
    assert await embeddings.generate_embeddings([]) == []
