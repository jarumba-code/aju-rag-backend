import json
import logging
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient

from src.auth import create_access_token, hash_password
from src.config import settings

# Set config BEFORE importing app
TEST_PASSWORD = "SuperSecretAdminPassword123!"
TEST_PASSWORD_HASH = hash_password(TEST_PASSWORD)
settings.ADMIN_PASSWORD_HASH = TEST_PASSWORD_HASH
settings.ADMIN_API_KEY = "test-api-key"
settings.SECRET_KEY = "test-secret-key-for-unit-tests-only"

logging.getLogger("src.auth").setLevel(logging.CRITICAL)

# Mock DB and engine before importing app
with patch('src.database.engine') as mock_engine, \
     patch('src.database.AsyncSessionLocal') as mock_session_local:
    
    mock_conn = MagicMock()
    mock_conn.run_sync = MagicMock()
    mock_engine.begin = AsyncMock(return_value=MagicMock(__aenter__=AsyncMock(return_value=mock_conn), __aexit__=AsyncMock(return_value=False)))
    
    mock_db = MagicMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))))
    mock_db.commit = AsyncMock()
    mock_db.close = AsyncMock()
    mock_session_local.return_value.__aenter__ = AsyncMock(return_value=mock_db)
    mock_session_local.return_value.__aexit__ = AsyncMock(return_value=False)
    
    from src.main import app
    from src.database import get_db
    
    app.dependency_overrides[get_db] = lambda: mock_db
    
    client = TestClient(app, raise_server_exceptions=False)


def login(password: str) -> tuple[int, dict]:
    resp = client.post("/api/v1/admin/auth/login", json={"password": password})
    try:
        body = resp.json()
    except Exception:
        body = {}
    return resp.status_code, body


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def me(headers: dict) -> tuple[int, dict]:
    resp = client.get("/api/v1/admin/auth/me", headers=headers)
    try:
        body = resp.json()
    except Exception:
        body = {}
    return resp.status_code, body


def admin_documents(headers: dict) -> tuple[int, list]:
    resp = client.get("/api/v1/admin/documents", headers=headers)
    try:
        body = resp.json()
    except Exception:
        body = []
    return resp.status_code, body


def test_01_correct_password_login_succeeds():
    status_code, body = login(TEST_PASSWORD)
    assert status_code == 200, f"Expected 200, got {status_code}: {body}"
    assert body.get("access_token")
    print("TEST 1 PASS")


def test_02_wrong_password_returns_401():
    status_code, body = login("wrong-password")
    assert status_code == 401
    print("TEST 2 PASS")


def test_03_missing_password_validation_error():
    resp = client.post("/api/v1/admin/auth/login", json={})
    assert resp.status_code == 422
    print("TEST 3 PASS")


def test_04_login_creates_authenticated_state():
    status_code, body = login(TEST_PASSWORD)
    assert status_code == 200
    token = body["access_token"]
    status_me, body_me = me(auth_header(token))
    assert status_me == 200, f"Expected 200, got {status_me}: {body_me}"
    print("TEST 4 PASS")


def test_05_me_unauthenticated_returns_401():
    status_code, body = me({})
    assert status_code == 401
    print("TEST 5 PASS")


def test_06_logout_removes_authentication():
    status_code, body = login(TEST_PASSWORD)
    assert status_code == 200
    token = body["access_token"]
    resp = client.post("/api/v1/admin/auth/logout", headers=auth_header(token))
    assert resp.status_code == 200
    print("TEST 6 PASS")


def test_07_protected_endpoint_no_auth_returns_401():
    status_code, _ = admin_documents({})
    assert status_code == 401
    print("TEST 7 PASS")


def test_08_protected_endpoint_with_jwt_allowed():
    status_code, body = login(TEST_PASSWORD)
    assert status_code == 200
    token = body["access_token"]
    status_code, docs = admin_documents(auth_header(token))
    assert status_code == 200, f"Expected 200, got {status_code}: {docs}"
    assert isinstance(docs, list)
    print("TEST 8 PASS")


def test_09_protected_endpoint_with_api_key_allowed():
    status_code, _ = admin_documents({"X-API-Key": "test-api-key"})
    assert status_code == 200
    print("TEST 9 PASS")


def test_10_malformed_jwt_returns_401():
    status_code, _ = admin_documents(auth_header("not-a-jwt-token"))
    assert status_code == 401
    print("TEST 10 PASS")


def test_11_expired_jwt_returns_401():
    from datetime import datetime, timezone, timedelta
    expired_payload = {"role": "admin", "exp": datetime.now(timezone.utc) - timedelta(seconds=100)}
    expired_token = create_access_token(expired_payload)
    status_code, _ = admin_documents(auth_header(expired_token))
    assert status_code == 401, f"Expected 401, got {status_code}"
    print("TEST 11 PASS")


def test_12_password_never_in_response():
    status_code, body = login(TEST_PASSWORD)
    assert status_code == 200
    raw = json.dumps(body)
    assert TEST_PASSWORD not in raw
    print("TEST 12 PASS")


def test_13_password_never_in_logs():
    with patch("src.auth.logger.warning") as mock_warning:
        login("wrong-password")
        for call in mock_warning.call_args_list:
            assert TEST_PASSWORD not in str(call)
    print("TEST 13 PASS")


tests = [
    test_01_correct_password_login_succeeds,
    test_02_wrong_password_returns_401,
    test_03_missing_password_validation_error,
    test_04_login_creates_authenticated_state,
    test_05_me_unauthenticated_returns_401,
    test_06_logout_removes_authentication,
    test_07_protected_endpoint_no_auth_returns_401,
    test_08_protected_endpoint_with_jwt_allowed,
    test_09_protected_endpoint_with_api_key_allowed,
    test_10_malformed_jwt_returns_401,
    test_11_expired_jwt_returns_401,
    test_12_password_never_in_response,
    test_13_password_never_in_logs,
]

passed = 0
failed = 0
for test in tests:
    try:
        test()
        passed += 1
    except AssertionError as exc:
        print(f"FAIL [{test.__name__}]: {exc}")
        failed += 1
    except Exception as exc:
        print(f"ERROR [{test.__name__}]: {type(exc).__name__}: {exc}")
        failed += 1

print(f"\n{'='*50}")
print(f"ADMIN AUTH TESTS: {passed} passed, {failed} failed")
print(f"{'='*50}")
sys.exit(0 if failed == 0 else 1)
