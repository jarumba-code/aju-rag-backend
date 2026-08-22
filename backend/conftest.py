"""
Pytest configuration: ensures proper module import ordering.

test_admin_auth.py patches ``src.database.engine`` at module-load time to mock
the DB layer for auth-handler tests.  Because ``main.py`` does
``from src.database import engine`` (capturing the value *by reference* at
import time), if ``src.main`` is first imported *inside* that
``with patch(...)`` block, main.py's local ``engine`` name is permanently
stuck on the MagicMock — even after the context-manager exits and
``src.database.engine`` is restored.

That stuck mock causes the FastAPI lifespan startup handler
(``async with engine.begin()``) to fail with ``TypeError`` / ``AsyncMock``
errors when a *later* test module (e.g. ``test_streaming.py``) creates its own
``TestClient(app)``.

This conftest imports ``src.main`` **before** any test module is collected,
guaranteeing that main.py captures the real engine.  test_admin_auth.py's
subsequent ``patch('src.database.engine')`` only affects the ``src.database``
namespace; main.py's already-bound ``engine`` remains the real object, and
every test module's TestClient gets a working startup path.

No production code is touched — only test orchestration.
"""
import sys
from pathlib import Path

# Same sys.path bootstrap every test file does individually.
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Pre-import the application so src.main captures the real engine before
# test_admin_auth.py (or any other test module) patches src.database.engine
# at module level.
from src.main import app  # noqa: F401  — import side-effect is the point