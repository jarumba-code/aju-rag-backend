import logging
import os
from typing import List
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv(override=True)
logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "openai/text-embedding-3-small")
EMBEDDING_BATCH_SIZE = 64  # OpenRouter / OpenAI supports up to ~2048 inputs

_embedding_client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    default_headers={
        "HTTP-Referer": "https://arthurjarvisuniversity.edu.ng",
        "X-Title": "AJU Knowledge Management Platform",
    },
)

async def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generate 1536-dim embeddings for a list of texts via OpenRouter.
    Processes in batches of EMBEDDING_BATCH_SIZE to respect API limits.

    Returns a list of embedding vectors (one per input text).
    """
    if not texts:
        return []

    all_embeddings: List[List[float]] = []

    for batch_start in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = texts[batch_start : batch_start + EMBEDDING_BATCH_SIZE]
        try:
            response = await _embedding_client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=batch,
            )
            # Sort by index to guarantee order matches input
            sorted_data = sorted(response.data, key=lambda d: d.index)
            all_embeddings.extend([item.embedding for item in sorted_data])
        except Exception as e:
            logger.error(
                f"Embedding batch failed (items {batch_start}-"
                f"{batch_start + len(batch)}): {e}"
            )
            # Insert empty vectors so indices stay aligned
            all_embeddings.extend([[] for _ in batch])

    return all_embeddings
