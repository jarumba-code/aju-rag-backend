from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.db import UserQuery

# High-quality AJU-specific default questions to fallback to if database is empty
DEFAULT_QUESTIONS = [
    "What are the admission requirements for Arthur Jarvis University?",
    "What faculties and departments are available at AJU?",
    "Where is Arthur Jarvis University located?",
    "How do I apply for accommodation on campus?",
    "What are the school fees for undergraduate programmes?",
]


async def get_suggested_questions(session: AsyncSession, limit: int = 5) -> list[str]:
    """
    Returns popular/featured queries from the database.
    Falls back to high-quality AJU-specific defaults if the DB is empty.
    """
    try:
        # Fetch top popular queries ordered by ask_count desc, featured first
        stmt = (
            select(UserQuery.query_text)
            .order_by(UserQuery.is_featured.desc(), UserQuery.ask_count.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        questions = [row[0] for row in result.all()]

        if not questions:
            return DEFAULT_QUESTIONS[:limit]

        # Pad with defaults if we have fewer than limit
        if len(questions) < limit:
            for q in DEFAULT_QUESTIONS:
                if q not in questions:
                    questions.append(q)
                if len(questions) == limit:
                    break

        return questions
    except Exception:
        return DEFAULT_QUESTIONS[:limit]


async def record_user_query(session: AsyncSession, query_text: str):
    """
    Upserts a user query: creates a new record or increments ask_count.
    """
    query_text = query_text.strip()
    if not query_text:
        return

    try:
        stmt = select(UserQuery).where(UserQuery.query_text == query_text)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.ask_count += 1
        else:
            new_query = UserQuery(query_text=query_text, ask_count=1)
            session.add(new_query)

        await session.commit()
    except Exception:
        await session.rollback()
