import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey, Float, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from .database import Base

# --- ENUMS ---
class VisibilityLevel(str, enum.Enum):
    PUBLIC = "PUBLIC"
    STUDENT = "STUDENT"
    STAFF = "STAFF"

class ContentStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    ARCHIVED = "ARCHIVED"

class ContentType(str, enum.Enum):
    FAQ = "FAQ"
    ARTICLE = "ARTICLE"
    PDF = "PDF"
    NOTICE = "NOTICE"

# --- RELATIONAL TAXONOMY ---
class Department(Base):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)  # e.g., "Information Technology Centre"

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)  # e.g., "Course Registration"
    description = Column(String, nullable=True)

# --- SYSTEM CONFIGURATION ---
class SystemSetting(Base):
    __tablename__ = "system_settings"
    __table_args__ = {"extend_existing": True}

    key = Column(String, primary_key=True, index=True)
    value = Column(String, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

# --- CORE KNOWLEDGE ---
class KnowledgeSource(Base):
    __tablename__ = "knowledge_sources"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    content_type = Column(Enum(ContentType))
    status = Column(Enum(ContentStatus), default=ContentStatus.DRAFT)
    
    # Relationships
    department_id = Column(Integer, ForeignKey("departments.id"))
    category_id = Column(Integer, ForeignKey("categories.id"))
    
    # Target Audience (Can be handled via association table for multiple, but simplified here)
    visibility = Column(Enum(VisibilityLevel), index=True)
    
    # Temporal Controls (Scheduled Publishing & Expiry)
    publish_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    department = relationship("Department")
    category = relationship("Category")
    chunks = relationship("DocumentChunk", back_populates="source", cascade="all, delete-orphan")
    versions = relationship("KnowledgeVersion", back_populates="source")

# --- VERSION HISTORY (The Git Model) ---
class KnowledgeVersion(Base):
    __tablename__ = "knowledge_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("knowledge_sources.id"))
    version_number = Column(Integer)
    content = Column(Text)  # The actual Notion-like rich text or parsed PDF text
    edit_reason = Column(String)
    edited_by = Column(String)  # Admin User ID
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    source = relationship("KnowledgeSource", back_populates="versions")

# --- VECTOR CHUNKS ---
class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey("knowledge_sources.id", ondelete="CASCADE"))
    chunk_content = Column(Text)
    
    # Replicated for High-Speed pgvector pre-filtering
    visibility = Column(Enum(VisibilityLevel), index=True)
    department_id = Column(Integer, index=True)

    # 1536-dim embedding from text-embedding-3-small
    vector_embedding = Column(Vector(1536), nullable=True)

    source = relationship("KnowledgeSource", back_populates="chunks")

# --- ANALYTICS & FEEDBACK LOOPS ---
class UnansweredQuestion(Base):
    __tablename__ = "unanswered_questions"
    id = Column(Integer, primary_key=True)
    normalized_hash = Column(String, index=True)
    sample_query = Column(Text)
    hit_count = Column(Integer, default=1)
    lowest_confidence = Column(Float)
    ai_draft_suggested = Column(Text, nullable=True) # AI Draft Assistant Output
    resolved = Column(Boolean, default=False)

class ChatAnalytics(Base):
    __tablename__ = "chat_analytics"
    id = Column(Integer, primary_key=True)
    query = Column(Text)
    response_time_ms = Column(Integer)
    cache_hit = Column(Boolean)
    similarity_score = Column(Float)
    user_feedback = Column(Integer, nullable=True) # 1 for 👍, -1 for 👎
    created_at = Column(DateTime(timezone=True), server_default=func.now())