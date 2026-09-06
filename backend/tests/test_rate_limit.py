"""Rate limiting: 10 requests per IP per window, isolated per client IP."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.services import rate_limit
from src.services.rate_limit import RateLimitMiddleware


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(rate_limit, "_local_hits", type(rate_limit._local_hits)(list))
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware)

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    @app.get("/api/v1/thing")
    async def thing():
        return {"ok": True}

    return TestClient(app)


def test_eleventh_request_from_same_ip_is_rejected(client):
    headers = {"X-Forwarded-For": "203.0.113.10"}
    for _ in range(rate_limit.RATE_LIMIT_REQUESTS):
        assert client.get("/api/v1/thing", headers=headers).status_code == 200

    blocked = client.get("/api/v1/thing", headers=headers)
    assert blocked.status_code == 429
    assert blocked.headers["X-RateLimit-Remaining"] == "0"
    assert int(blocked.headers["Retry-After"]) >= 1


def test_limit_is_per_ip(client):
    for _ in range(rate_limit.RATE_LIMIT_REQUESTS + 1):
        client.get("/api/v1/thing", headers={"X-Forwarded-For": "203.0.113.11"})

    other = client.get("/api/v1/thing", headers={"X-Forwarded-For": "203.0.113.12"})
    assert other.status_code == 200
    assert other.headers["X-RateLimit-Limit"] == str(rate_limit.RATE_LIMIT_REQUESTS)


def test_health_probe_is_exempt(client):
    headers = {"X-Forwarded-For": "203.0.113.13"}
    for _ in range(rate_limit.RATE_LIMIT_REQUESTS + 5):
        assert client.get("/health", headers=headers).status_code == 200


@pytest.mark.asyncio
async def test_window_expiry_releases_the_limit(monkeypatch):
    monkeypatch.setattr(rate_limit, "_local_hits", type(rate_limit._local_hits)(list))
    for _ in range(3):
        await rate_limit.check_rate_limit("ip:198.51.100.1", limit=3, window_seconds=1)

    allowed, remaining, _ = await rate_limit.check_rate_limit(
        "ip:198.51.100.1", limit=3, window_seconds=1
    )
    assert not allowed and remaining == 0

    now = rate_limit.time.time()
    monkeypatch.setattr(rate_limit.time, "time", lambda: now + 2)
    allowed, remaining, _ = await rate_limit.check_rate_limit(
        "ip:198.51.100.1", limit=3, window_seconds=1
    )
    assert allowed and remaining == 2
