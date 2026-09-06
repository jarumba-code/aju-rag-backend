import os
import sys
from pathlib import Path

# Tests exercise the pure logic (limiter accounting, cache keys, filter SQL) without
# requiring Redis, Postgres, or an LLM provider.
os.environ.setdefault("CACHE_ENABLED", "false")
os.environ.setdefault("OPENROUTER_API_KEY", "test-key")
os.environ.setdefault("SECRET_KEY", "test-secret")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
