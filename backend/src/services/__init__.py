"""Services module handling document processing and RAG operations."""

from src.services.ingest import process_and_ingest_pdf

__all__ = ["process_and_ingest_pdf"]
