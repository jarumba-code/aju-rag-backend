import traceback, sys
from pathlib import Path
sys.path.insert(0, '.')
from fastapi.testclient import TestClient
from src.config import settings
from src.main import app

settings.ADMIN_API_KEY = 'test-api-key'
settings.ADMIN_PASSWORD_HASH = ''

client = TestClient(app, raise_server_exceptions=True)
try:
    resp = client.get('/api/v1/admin/documents', headers={'X-API-Key': 'test-api-key'})
    print('STATUS:', resp.status_code)
except Exception:
    traceback.print_exc()
