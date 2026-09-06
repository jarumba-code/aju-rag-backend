from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RetrievalResult(BaseModel):
    chunk_id: int
    document_id: str
    source_id: Optional[int]
    chunk_content: str
    similarity_score: float
    source_title: Optional[str]
    department: Optional[str]
    doc_type: Optional[str]
    visibility: str


class RetrievalFilters(BaseModel):
    """
    Structured metadata filters applied *in the database* alongside the vector search,
    so the top-k is chosen from matching documents only rather than being filtered
    after the fact (which would silently return fewer than k results).

    Persona visibility is deliberately NOT part of this model — it is derived
    server-side from the caller's persona and can never be widened by a request.
    """

    department: Optional[str] = Field(default=None, description="Document department (case-insensitive)")
    department_id: Optional[int] = Field(default=None, description="Chunk department id")
    doc_type: Optional[str] = Field(default=None, description="e.g. 'pdf', 'text'")
    document_ids: Optional[List[str]] = Field(default=None, description="Restrict to these document UUIDs")
    source_ids: Optional[List[int]] = Field(default=None, description="Restrict to these knowledge source ids")
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None

    def is_empty(self) -> bool:
        return not any(value is not None for value in self.model_dump().values())

    def fingerprint(self) -> Dict[str, Any]:
        """Cache-key friendly representation (only the set fields)."""
        return {key: value for key, value in self.model_dump(exclude_none=True).items()}
