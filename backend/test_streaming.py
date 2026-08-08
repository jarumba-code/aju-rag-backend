"""
Streaming endpoint tests for POST /api/v1/query/stream.

Uses unittest.mock to patch OpenRouter LLM calls — no live API dependency.
Uses a single shared TestClient across all tests to avoid asyncpg event-loop
teardown issues that occur when TestClient context managers are nested.

Tests:
  1. HTTP 200 + content-type text/event-stream
  2. Multiple token events emitted
  3. Final done event with confidence_score, sources, telemetry
  4. Citations emitted for retrieved chunks
  5. No-result query graceful handling (confidence=0, sources=[])
  6. LLM error yields error event, not a crash
  7. Existing /api/v1/query still works (regression)
  8. Confidence score present in done event
  9. Start event emitted first
"""
import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient
from src.main import app

# ---------------------------------------------------------------------------
# Single shared client — avoids repeated asyncpg pool teardown
# ---------------------------------------------------------------------------
CLIENT = TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# SSE parser
# ---------------------------------------------------------------------------

def parse_sse(raw: str) -> list:
    events = []
    current = {}
    for line in raw.splitlines():
        if line.startswith("event:"):
            current["event"] = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            try:
                current["data"] = json.loads(line.split(":", 1)[1].strip())
            except json.JSONDecodeError:
                current["data"] = line.split(":", 1)[1].strip()
        elif line == "" and current:
            events.append(current)
            current = {}
    if current:
        events.append(current)
    return events


def by_type(events, event_type):
    return [e for e in events if e.get("event") == event_type]


# ---------------------------------------------------------------------------
# Mock factories
# ---------------------------------------------------------------------------

def mock_retrieve_ok(db, query, persona, department_id=None, **kw):
    from src.schemas.retrieval import RetrievalResult
    async def _inner(*a, **k):
        return [RetrievalResult(
            chunk_id=1, document_id="doc-1", source_id=1,
            chunk_content="Students must register for courses before the semester deadline.",
            similarity_score=0.82, source_title="Test Source",
            department=None, doc_type=None, visibility="PUBLIC",
        )]
    import asyncio
    return _inner(db, query, persona, department_id=department_id, **kw)


def mock_retrieve_empty(db, query, persona, department_id=None, **kw):
    async def _inner(*a, **k):
        return []
    return _inner(db, query, persona, department_id=department_id, **kw)


async def mock_stream_ok(messages, model=None, temperature=0.2):
    from src.services.llm import StreamEvent
    yield StreamEvent(event_type="first_token", text="Hello", llm_latency_ms=120.0)
    yield StreamEvent(event_type="token", text=" world")
    yield StreamEvent(event_type="token", text="!")
    yield StreamEvent(event_type="done", llm_latency_ms=400.0, prompt_tokens=50, completion_tokens=10)


async def mock_stream_error(messages, model=None, temperature=0.2):
    from src.services.llm import StreamEvent
    yield StreamEvent(event_type="error", error_detail="LLM request timed out.")


from src.services.llm import ChatResult
MOCK_CHAT_RESULT = ChatResult(answer="Mocked answer.", prompt_tokens=30, completion_tokens=8, llm_latency_ms=200.0)


def stream_post(payload):
    return CLIENT.post("/api/v1/query/stream", json=payload)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_1_http_200_and_content_type():
    with patch("src.rag.retrieve_relevant_chunks", side_effect=mock_retrieve_ok), \
         patch("src.rag.stream_chat", side_effect=mock_stream_ok):
        resp = stream_post({"query": "test", "persona": "public"})
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    assert "text/event-stream" in resp.headers.get("content-type", "")
    print("TEST 1 PASS: HTTP 200 + text/event-stream")


def test_2_token_events():
    with patch("src.rag.retrieve_relevant_chunks", side_effect=mock_retrieve_ok), \
         patch("src.rag.stream_chat", side_effect=mock_stream_ok):
        resp = stream_post({"query": "test", "persona": "student"})
    events = parse_sse(resp.text)
    tokens = by_type(events, "token")
    assert len(tokens) >= 1, f"Expected >=1 token events, got {len(tokens)}"
    assembled = "".join(t["data"].get("text", "") for t in tokens)
    assert len(assembled) > 0
    print(f"TEST 2 PASS: {len(tokens)} token events, text={repr(assembled)}")


def test_3_done_event_structure():
    with patch("src.rag.retrieve_relevant_chunks", side_effect=mock_retrieve_ok), \
         patch("src.rag.stream_chat", side_effect=mock_stream_ok):
        resp = stream_post({"query": "test", "persona": "student"})
    events = parse_sse(resp.text)
    done_list = by_type(events, "done")
    assert len(done_list) == 1, f"Expected 1 done event, got {len(done_list)}"
    done = done_list[0]["data"]
    for key in ("conversation_id", "confidence_score", "sources", "telemetry", "answer"):
        assert key in done, f"Missing key '{key}' in done event"
    print(f"TEST 3 PASS: done event OK, confidence={done.get('confidence_score')}")


def test_4_citation_events():
    with patch("src.rag.retrieve_relevant_chunks", side_effect=mock_retrieve_ok), \
         patch("src.rag.stream_chat", side_effect=mock_stream_ok):
        resp = stream_post({"query": "course registration", "persona": "student"})
    events = parse_sse(resp.text)
    citations = by_type(events, "citation")
    assert len(citations) >= 1, f"Expected >=1 citation events, got {len(citations)}"
    assert citations[0]["data"].get("source_title") == "Test Source"
    print(f"TEST 4 PASS: {len(citations)} citation events")


def test_5_no_result_graceful():
    with patch("src.rag.retrieve_relevant_chunks", side_effect=mock_retrieve_empty), \
         patch("src.rag.stream_chat", side_effect=mock_stream_ok):
        resp = stream_post({"query": "alien invasion mars", "persona": "public"})
    assert resp.status_code == 200
    events = parse_sse(resp.text)
    done_list = by_type(events, "done")
    assert len(done_list) == 1
    done = done_list[0]["data"]
    assert done.get("confidence_score", 1.0) == 0.0
    assert done.get("sources", ["x"]) == []
    print(f"TEST 5 PASS: no-result => confidence={done.get('confidence_score')}, sources={done.get('sources')}")


def test_6_llm_error_emits_error_event():
    with patch("src.rag.retrieve_relevant_chunks", side_effect=mock_retrieve_ok), \
         patch("src.rag.stream_chat", side_effect=mock_stream_error):
        resp = stream_post({"query": "test", "persona": "public"})
    assert resp.status_code == 200
    events = parse_sse(resp.text)
    error_events = by_type(events, "error")
    assert len(error_events) >= 1, f"Expected error event, got events: {[e.get('event') for e in events]}"
    assert "timed out" in error_events[0]["data"].get("detail", "").lower()
    print(f"TEST 6 PASS: error event emitted => {error_events[0]['data'].get('detail')}")


def test_7_existing_query_regression():
    with patch("src.rag.retrieve_relevant_chunks", side_effect=mock_retrieve_ok), \
         patch("src.rag.complete_chat", return_value=MOCK_CHAT_RESULT):
        resp = CLIENT.post("/api/v1/query", json={"query": "test", "persona": "public"})
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    for key in ("answer", "sources", "conversation_id"):
        assert key in data, f"Missing key '{key}'"
    print(f"TEST 7 PASS: /api/v1/query still works, answer={repr(data['answer'][:40])}")


def test_8_confidence_score_in_stream():
    with patch("src.rag.retrieve_relevant_chunks", side_effect=mock_retrieve_ok), \
         patch("src.rag.stream_chat", side_effect=mock_stream_ok):
        resp = stream_post({"query": "test", "persona": "student"})
    events = parse_sse(resp.text)
    done = by_type(events, "done")[0]["data"]
    conf = done.get("confidence_score")
    assert conf is not None
    assert 0.0 <= conf <= 1.0
    print(f"TEST 8 PASS: confidence_score={conf}")


def test_9_start_event_first():
    with patch("src.rag.retrieve_relevant_chunks", side_effect=mock_retrieve_ok), \
         patch("src.rag.stream_chat", side_effect=mock_stream_ok):
        resp = stream_post({"query": "test", "persona": "public"})
    events = parse_sse(resp.text)
    assert events, "No events received"
    assert events[0].get("event") == "start", f"First event should be 'start', got '{events[0].get('event')}'"
    print("TEST 9 PASS: start event emitted first")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

TESTS = [
    test_1_http_200_and_content_type,
    test_2_token_events,
    test_3_done_event_structure,
    test_4_citation_events,
    test_5_no_result_graceful,
    test_6_llm_error_emits_error_event,
    test_7_existing_query_regression,
    test_8_confidence_score_in_stream,
    test_9_start_event_first,
]


def run_all():
    passed = 0
    failed = 0
    for test in TESTS:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"FAIL [{test.__name__}]: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR [{test.__name__}]: {type(e).__name__}: {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"STREAMING TESTS: {passed} passed, {failed} failed")
    print(f"{'='*50}")
    return failed == 0


if __name__ == "__main__":
    ok = run_all()
    sys.exit(0 if ok else 1)
