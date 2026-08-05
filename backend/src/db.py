import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import text, ForeignKey, DateTime, String, Text, Integer, Boolean
from pgvector.sqlalchemy import Vector
from src.config import settings


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


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(255), default="general")
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)


class UserQuery(Base):
    __tablename__ = "user_queries"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    query_text: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    ask_count: Mapped[int] = mapped_column(Integer, default=1)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)


async def init_db():
    """Initializes the database: enables vector extension and creates all tables."""
    async with engine.begin() as conn:
        # Enable pgvector extension (requires Supabase extensions.trusted_extensions)
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        # Create tables if they don't exist
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    """FastAPI dependency that provides a database session."""
    async with async_session() as session:
        yield session
