"""Metadata filters are pushed into the SQL, before the top-k cut."""

from datetime import datetime

from sqlalchemy import select

from src.models import DocumentChunk, VisibilityLevel
from src.schemas.retrieval import RetrievalFilters
from src.services.retrieval import _apply_metadata_filters, visibility_levels_for_persona


def _compiled(filters: RetrievalFilters) -> str:
    stmt = _apply_metadata_filters(select(DocumentChunk), filters)
    return str(stmt.compile(compile_kwargs={"literal_binds": True})).lower()


def test_empty_filters_are_detected():
    assert RetrievalFilters().is_empty()
    assert not RetrievalFilters(department="Law").is_empty()
    assert RetrievalFilters(department="Law").fingerprint() == {"department": "Law"}


def test_document_level_filters_join_documents():
    sql = _compiled(RetrievalFilters(department="Law", doc_type="PDF"))
    assert "join documents" in sql
    assert "lower(documents.department) = 'law'" in sql
    assert "lower(documents.doc_type) = 'pdf'" in sql


def test_date_bounds_are_applied():
    sql = _compiled(
        RetrievalFilters(
            created_after=datetime(2026, 1, 1),
            created_before=datetime(2026, 6, 1),
        )
    )
    assert "documents.created_at >=" in sql
    assert "documents.created_at <=" in sql


def test_chunk_level_filters_need_no_join():
    sql = _compiled(RetrievalFilters(department_id=3, source_ids=[1, 2]))
    assert "join documents" not in sql
    assert "document_chunks.department_id = 3" in sql
    assert "document_chunks.source_id in (1, 2)" in sql


def test_persona_visibility_is_not_client_controllable():
    assert "visibility" not in RetrievalFilters.model_fields
    assert visibility_levels_for_persona("public") == [VisibilityLevel.PUBLIC]
    assert visibility_levels_for_persona("hacker") == [VisibilityLevel.PUBLIC]
    assert VisibilityLevel.STAFF in visibility_levels_for_persona("staff")
    assert VisibilityLevel.STAFF not in visibility_levels_for_persona("student")
