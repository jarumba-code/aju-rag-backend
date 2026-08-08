import asyncio
import uuid
from sqlalchemy import select
from src.database import AsyncSessionLocal
from src.models import KnowledgeSource, Document, DocumentChunk, VisibilityLevel, ContentStatus
from src.services.ingest import process_and_store_document
from src.rag import retrieve_relevant_chunks

async def main():
    print("Starting ingestion and retrieval test...")
    async with AsyncSessionLocal() as session:
        # Create a test KnowledgeSource
        source_title = f"Test AJU Policy {uuid.uuid4().hex[:6]}"
        test_source = KnowledgeSource(
            title=source_title,
            visibility=VisibilityLevel.PUBLIC,
            status=ContentStatus.DRAFT
        )
        session.add(test_source)
        await session.flush()
        print(f"Created temporary KnowledgeSource ID: {test_source.id}")

        test_content = "Arthur Jarvis University is a private university in Nigeria. Course registration must be completed by the third week of the semester."

        try:
            # Run ingestion pipeline
            chunks_count = await process_and_store_document(
                db=session,
                source_id=test_source.id,
                content=test_content,
                visibility=VisibilityLevel.PUBLIC,
                title=source_title
            )
            print(f"Ingestion pipeline completed. Created {chunks_count} chunks.")

            # Commit the transaction
            await session.commit()
            print("Transaction committed successfully.")
        except Exception as e:
            await session.rollback()
            print(f"Ingestion pipeline failed: {e}")
            return

    # Eagerly fetch and test retrieval in a new session
    async with AsyncSessionLocal() as session:
        print("\nVerifying database records...")
        # Verify KnowledgeSource
        source_db = (await session.execute(
            select(KnowledgeSource).where(KnowledgeSource.id == test_source.id)
        )).scalar_one_or_none()
        print(f"KnowledgeSource in DB: {source_db.title if source_db else 'NOT FOUND'} (Status: {source_db.status if source_db else 'N/A'})")

        # Verify Document
        doc_db = (await session.execute(
            select(Document).where(Document.title == source_title)
        )).scalar_one_or_none()
        print(f"Document in DB: {doc_db.title if doc_db else 'NOT FOUND'} (Chunks count: {doc_db.chunk_count if doc_db else 'N/A'})")

        # Verify DocumentChunk
        chunks_db = (await session.execute(
            select(DocumentChunk).where(DocumentChunk.source_id == test_source.id)
        )).scalars().all()
        print(f"DocumentChunks count in DB: {len(chunks_db)}")
        for idx, chunk in enumerate(chunks_db, 1):
            print(f"  Chunk {idx}: {chunk.chunk_content[:60]}... (visibility: {chunk.visibility}, dept: {chunk.department_id})")

        # Test RAG retrieval compatibility
        print("\nTesting retrieval compatibility...")
        retrieved_sources = await retrieve_relevant_chunks(
            db=session,
            query="Arthur Jarvis Course registration",
            persona="public",
            limit=3
        )
        print(f"Retrieved {len(retrieved_sources)} relevant sources.")
        found = False
        for src in retrieved_sources:
            print(f"  Source Title: {src.title}")
            for c in src.chunks:
                print(f"    Chunk text: {c.chunk_content}")
                if source_title == src.title:
                    found = True
        
        if found:
            print("\nSUCCESS: Document was successfully ingested, stored, and retrieved via RAG retrieval!")
        else:
            print("\nFAILURE: Ingested document was not retrieved.")

        # Cleanup
        print("\nCleaning up test records...")
        if source_db:
            await session.delete(source_db)
        if doc_db:
            await session.delete(doc_db)
        await session.commit()
        print("Cleanup completed.")

if __name__ == "__main__":
    asyncio.run(main())
