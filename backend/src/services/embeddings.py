import logging
import os
from typing import List, Optional
from dotenv import load_dotenv
from openai import AsyncOpenAI

from src.services.cache import get_cached_embeddings, set_cached_embeddings

load_dotenv(override=True)
logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "openai/text-embedding-3-small")
EMBEDDING_BATCH_SIZE = 64  # OpenRouter / OpenAI supports up to ~2048 inputs

_embedding_client: Optional[AsyncOpenAI] = None


def get_embedding_client() -> AsyncOpenAI:
    """Lazily build the provider client so importing the app never requires a key."""
    global _embedding_client
    if _embedding_client is None:
        _embedding_client = AsyncOpenAI(
            base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            api_key=OPENROUTER_API_KEY or "not-configured",
            default_headers={
                "HTTP-Referer": "https://arthurjarvisuniversity.edu.ng",
                "X-Title": "AJU Knowledge Management Platform",
            },
        )
    return _embedding_client

async def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generate 1536-dim embeddings for a list of texts via OpenRouter.

    Vectors already present in the Redis embedding cache are reused; only the
    remaining texts are sent to the provider, in batches of EMBEDDING_BATCH_SIZE.

    Returns a list of embedding vectors (one per input text, order preserved).
    """
    if not texts:
        return []

    results: List[List[float]] = [[] for _ in texts]

    cached = await get_cached_embeddings(EMBEDDING_MODEL, texts)
    for index, vector in cached.items():
        results[index] = vector

    pending = [index for index in range(len(texts)) if not results[index]]
    if cached:
        logger.info(
            "Embedding cache: %d/%d hits, %d to generate",
            len(cached),
            len(texts),
            len(pending),
        )

    for batch_start in range(0, len(pending), EMBEDDING_BATCH_SIZE):
        batch_indices = pending[batch_start : batch_start + EMBEDDING_BATCH_SIZE]
        batch = [texts[index] for index in batch_indices]
        try:
            response = await get_embedding_client().embeddings.create(
                model=EMBEDDING_MODEL,
                input=batch,
            )
            # Sort by index to guarantee order matches input
            sorted_data = sorted(response.data, key=lambda d: d.index)
            for index, item in zip(batch_indices, sorted_data):
                results[index] = item.embedding
            await set_cached_embeddings(
                EMBEDDING_MODEL,
                [(texts[index], results[index]) for index in batch_indices],
            )
        except Exception as e:
            logger.error(
                f"Embedding batch failed (items {batch_start}-"
                f"{batch_start + len(batch)}): {e}"
            )
            # Leave empty vectors so indices stay aligned

    return results
