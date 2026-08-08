import asyncio
import os
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import AsyncSessionLocal
from src.services.retrieval import retrieve_relevant_chunks

async def run():
    async with AsyncSessionLocal() as db:
        results = await retrieve_relevant_chunks(db, query='financial plan', persona='staff', limit=5, similarity_threshold=0.0)
        for r in results:
            print(f'Score: {r.similarity_score} | Content: {r.chunk_content[:50]}...')

asyncio.run(run())
