import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Mapped, mapped_column

from src.config import settings
from src.models import Base, Document, DocumentChunk


def generate_uuid() -> str:
    return str(uuid.uuid4())


def _build_engine():
    """
    Build the async engine with Supabase SSL requirements.
    Supabase requires SSL; we pass connect_args so asyncpg uses it.
    """
    db_url = settings.get_database_url()
    return create_async_engine(
        db_url,
        echo=False,
        pool_pre_ping=True,
        connect_args={"ssl": "require"},
    )


engine = _build_engine()
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class UserQuery(Base):
    __tablename__ = "user_queries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    query_text: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    ask_count: Mapped[int] = mapped_column(Integer, default=1)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)


async def init_db():
    """Initializes the database: enables vector extension and creates all tables."""
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    """FastAPI dependency that provides a database session."""
    async with async_session() as session:
        yield session
