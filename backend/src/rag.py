import os
import logging
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from openai import AsyncOpenAI

# src/rag.py
from src.models import KnowledgeSource, SystemSetting

logger = logging.getLogger(__name__)

# Environment Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "meta-llama/llama-3.3-70b-instruct")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "openai/text-embedding-3-small")

# Initialize OpenAI Async Client routed to OpenRouter
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    default_headers={
        "HTTP-Referer": "https://arthurjarvisuniversity.edu.ng",
        "X-Title": "AJU Knowledge Management Platform",
    }
)


async def get_system_setting(db: AsyncSession, key: str, default: str) -> str:
    """Fetch dynamic system settings from database."""
    result = await db.execute(select(SystemSetting).filter(SystemSetting.key == key))
    setting = result.scalars().first()
    return setting.value if setting else default


async def generate_embedding(text: str) -> List[float]:
    """Generates text embeddings via OpenRouter."""
    try:
        response = await client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error generating embeddings via OpenRouter: {e}")
        return []


async def retrieve_context(
    db: AsyncSession, 
    persona: str = "public", 
    limit: int = 4
) -> List[KnowledgeSource]:
    """Fetches knowledge sources from PostgreSQL based on persona visibility rules."""
    stmt = select(KnowledgeSource).filter(KnowledgeSource.is_active == True)
    
    # Public persona restricted to non-confidential files
    if persona.lower() == "public":
        stmt = stmt.filter(KnowledgeSource.is_confidential == False)
    
    result = await db.execute(stmt.limit(limit))
    return result.scalars().all()


def build_persona_prompt(query: str, context_chunks: List[str], persona: str) -> List[Dict[str, str]]:
    """Constructs OpenAI format chat messages tailored to the active role."""
    context_str = "\n\n".join(context_chunks) if context_chunks else "No relevant context found."

    if persona.lower() == "student":
        system_instruction = (
            "You are the Official Student Assistant for Arthur Jarvis University (AJU). "
            "Use the provided institutional context to answer accurately and clearly. "
            "If the information is not in the context, explicitly inform the user."
        )
    else:
        system_instruction = (
            "You are the Public Information Assistant for Arthur Jarvis University (AJU). "
            "Provide general inquiry information for visitors and prospective students. "
            "Never reveal confidential internal policies, administrative records, or staff data."
        )

    user_content = f"--- VERIFIED CONTEXT ---\n{context_str}\n\n--- QUESTION ---\n{query}"

    return [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": user_content}
    ]


async def answer_query(db: AsyncSession, query: str, persona: str = "public") -> Dict[str, Any]:
    """Main entrypoint: retrieves context, enforces persona access, and queries OpenRouter."""
    # 1. Fetch dynamic confidence threshold
    min_confidence_str = await get_system_setting(db, "min_confidence_score", "0.70")

    # 2. Retrieve sources from Supabase
    sources = await retrieve_context(db, persona=persona)
    context_chunks = [f"[{s.title}]: {s.content}" for s in sources if s.content]

    # 3. Handle fallback state if no context passes constraints
    if not context_chunks:
        return {
            "answer": "I am sorry, but I do not have verified institutional data to answer that query.",
            "sources": [],
            "confidence_met": False
        }

    # 4. Construct prompt and execute OpenRouter Chat Completion
    messages = build_persona_prompt(query, context_chunks, persona)

    try:
        completion = await client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            temperature=0.2
        )
        answer_text = completion.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenRouter LLM completion error: {e}")
        answer_text = "An error occurred while communicating with the inference model."

    return {
        "answer": answer_text,
        "sources": [s.title for s in sources],
        "confidence_met": True
    }