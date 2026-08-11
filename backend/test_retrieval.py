import asyncio
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from src.database import AsyncSessionLocal, engine
from src.models import KnowledgeSource, Document, DocumentChunk, VisibilityLevel
from src.services.retrieval import retrieve_relevant_chunks
from src.services.ingest import process_and_store_document

# Note: In a real test suite you would mock the embedding client, 
# but we will rely on OpenRouter since this is an integration test against the real database.

async def setup_test_data(db: AsyncSession):
    # Clear old test data
    await db.execute(delete(DocumentChunk).where(DocumentChunk.chunk_content.like("TEST_%")))
    await db.execute(delete(Document).where(Document.title.like("TEST_%")))
    await db.execute(delete(KnowledgeSource).where(KnowledgeSource.title.like("TEST_%")))
    await db.commit()

    # Create dummy source and ingest it
    ks1 = KnowledgeSource(title="TEST_PUBLIC_DOC", visibility=VisibilityLevel.PUBLIC)
    ks2 = KnowledgeSource(title="TEST_STUDENT_DOC", visibility=VisibilityLevel.STUDENT)
    ks3 = KnowledgeSource(title="TEST_STAFF_DOC", visibility=VisibilityLevel.STAFF)
    
    db.add_all([ks1, ks2, ks3])
    await db.commit()

    # We use very specific semantic content so it's easy to retrieve.
    content1 = "TEST_CONTENT_A: The quick brown fox jumps over the lazy dog in the public park."
    content2 = "TEST_CONTENT_B: The students are studying advanced calculus in the library."
    content3 = "TEST_CONTENT_C: The university budget for the new year has been approved by the board of directors."

    await process_and_store_document(db, ks1.id, content1, VisibilityLevel.PUBLIC, title="TEST_PUBLIC_DOC")
    await process_and_store_document(db, ks2.id, content2, VisibilityLevel.STUDENT, title="TEST_STUDENT_DOC")
    await process_and_store_document(db, ks3.id, content3, VisibilityLevel.STAFF, title="TEST_STAFF_DOC")
    await db.commit()

async def run_tests():
    async with AsyncSessionLocal() as db:
        print("Setting up test data...")
        await setup_test_data(db)

        print("\n--- TEST 1: Semantic Query (No Exact Match) ---")
        # "financial plan" -> semantic match to "budget"
        results = await retrieve_relevant_chunks(db, query="financial plan", persona="staff", limit=2, similarity_threshold=0.25)
        assert len(results) > 0
        assert "TEST_CONTENT_C" in results[0].chunk_content
        print("PASS")

        print("\n--- TEST 2: Visibility Filtering (Public) ---")
        # Should not see student or staff docs
        results = await retrieve_relevant_chunks(db, query="calculus and budget", persona="public", limit=5, similarity_threshold=0.10)
        for r in results:
            assert r.visibility == VisibilityLevel.PUBLIC.value
        print("PASS")

        print("\n--- TEST 3: Visibility Filtering (Student) ---")
        # Should see public and student, but not staff
        results = await retrieve_relevant_chunks(db, query="budget", persona="student", limit=5, similarity_threshold=0.10)
        for r in results:
            assert r.visibility in [VisibilityLevel.PUBLIC.value, VisibilityLevel.STUDENT.value]
        print("PASS")

        print("\n--- TEST 4: Threshold Reject (Irrelevant Query) ---")
        # This string should have low cosine similarity to our docs
        results = await retrieve_relevant_chunks(db, query="extraterrestrial alien invasion on mars", persona="staff", similarity_threshold=0.85)
        assert len(results) == 0
        print("PASS")
        
        print("\n--- TEST 5: Empty Result Graceful Handling ---")
        # Test default handling when empty
        results = await retrieve_relevant_chunks(db, query="xyzqwe asdf", persona="public", similarity_threshold=0.99)
        assert type(results) is list
        assert len(results) == 0
        print("PASS")

        print("\nAll tests passed successfully.")

if __name__ == "__main__":
    async def _entry() -> None:
        try:
            await run_tests()
        finally:
            await engine.dispose()

    asyncio.run(_entry())
