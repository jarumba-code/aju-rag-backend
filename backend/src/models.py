import enum
import uuid
from datetime import datetime

from typing import Any
from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
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

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# --- CONVERSATION MEMORY ---
class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    persona = Column(String(50), default="public")
    department_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), index=True, nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    sources = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")


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

class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    title = Column(String, nullable=True)
    filename = Column(String, nullable=True)
    file_hash = Column(String, unique=True, nullable=False, index=True)
    department = Column(String, nullable=True)
    doc_type = Column(String, nullable=True)
    source_name = Column(String, nullable=True)
    chunk_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

# --- VECTOR CHUNKS ---
class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey("knowledge_sources.id", ondelete="CASCADE"), nullable=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=True)
    chunk_content = Column(Text)
    
    # Replicated for High-Speed pgvector pre-filtering
    visibility = Column(Enum(VisibilityLevel), index=True)
    department_id = Column(Integer, index=True)
    
    vector_embedding = Column(Vector(1536), nullable=True)
    source = relationship("KnowledgeSource", back_populates="chunks")
    document = relationship("Document", back_populates="chunks")

# --- ANALYTICS & FEEDBACK LOOPS ---
class UnansweredQuery(Base):
    __tablename__ = "unanswered_queries"
    __table_args__ = (
        Index("ix_unanswered_queries_created_at", "created_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    query_text = Column(Text, nullable=False)
    normalized_query = Column(Text, nullable=True)
    reason = Column(String(50), nullable=False)
    confidence_score = Column(Float, nullable=True)
    retrieved_documents = Column(Integer, default=0, nullable=False)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    metadata_json = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved = Column(Boolean, default=False, nullable=False)
    resolution_note = Column(Text, nullable=True)

    conversation = relationship("Conversation")

class ChatAnalytics(Base):
    __tablename__ = "chat_analytics"
    id = Column(Integer, primary_key=True)
    query = Column(Text)
    response_time_ms = Column(Integer)
    cache_hit = Column(Boolean)
    similarity_score = Column(Float)
    user_feedback = Column(Integer, nullable=True) # 1 for 👍, -1 for 👎
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# --- AUDIT LOGGING ---
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    user_role = Column(String(50), nullable=True)  # e.g. "admin", "system"
    action = Column(String(100), nullable=False, index=True)  # e.g. "login", "logout", "password_change", "document_upload", "document_delete"
    resource_type = Column(String(50), nullable=True)  # e.g. "document", "gap", "settings"
    resource_id = Column(String(100), nullable=True)
    details = Column(Text, nullable=True)  # JSON string for extra context
    status = Column(String(20), nullable=False)  # "success", "failure", "warning"
    ip_address = Column(String(45), nullable=True)  # IPv4/IPv6
