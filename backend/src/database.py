from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from src.config import settings

BACKEND_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BACKEND_DIR / ".env"

load_dotenv(dotenv_path=ENV_FILE, override=False)


def _mask_database_url(database_url: str) -> str:
    parsed = urlparse(database_url)
    username = parsed.username or ""
    password = parsed.password or ""
    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    database = parsed.path.lstrip("/")
    driver = parsed.scheme
    if username and password:
        return f"{driver}://{username}:********@{host}{port}/{database}"
    if username:
        return f"{driver}://{username}@{host}{port}/{database}"
    return f"{driver}://{host}{port}/{database}"


DATABASE_URL = settings.get_database_url().strip().strip('"').strip("'")
if not DATABASE_URL:
    raise ValueError("🚨 DATABASE_URL environment variable is missing or failed to load. Check backend/.env")

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

print(f".env file loaded from: {ENV_FILE}")
print("Loaded DATABASE_URL:")
print(_mask_database_url(DATABASE_URL))
print(f"Hostname: {urlparse(DATABASE_URL).hostname}")
print(f"Username: {urlparse(DATABASE_URL).username}")
print(f"Database: {urlparse(DATABASE_URL).path.lstrip('/')}")
print(f"Driver: {urlparse(DATABASE_URL).scheme}")

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    connect_args={"statement_cache_size": 0},
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


async def get_db():
    """FastAPI dependency yielding asynchronous database sessions per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()