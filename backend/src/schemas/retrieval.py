from pydantic import BaseModel
from typing import Optional

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
