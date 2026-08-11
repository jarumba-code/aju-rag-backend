"""Suggested-question service for the AJU portal.

Returns a curated set of high-quality AJU-specific prompts, optionally enriched
with the most frequently asked queries already present in the existing analytics
table (``ChatAnalytics``).

This intentionally reuses the models already in the system instead of creating a
duplicate ``UserQuery`` model (the previous ``src.db`` import did not exist).
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import ChatAnalytics

# High-quality AJU-specific default questions to fall back to when the analytics
# store is empty or unavailable.
DEFAULT_QUESTIONS = [
    "What are the admission requirements for Arthur Jarvis University?",
    "What faculties and departments are available at AJU?",
    "Where is Arthur Jarvis University located?",
    "How do I apply for accommodation on campus?",
    "What are the school fees for undergraduate programmes?",
]


async def get_suggested_questions(session: AsyncSession, limit: int = 5) -> list[str]:
    """
    Return popular previously-asked queries (from ``ChatAnalytics``), padded and
    deduplicated with the curated ``DEFAULT_QUESTIONS``.

    If the analytics table is empty or unavailable, only the defaults are used.
    """
    popular: list[str] = []
    try:
        stmt = (
            select(ChatAnalytics.query, func.count(ChatAnalytics.id).label("cnt"))
            .where(ChatAnalytics.query.isnot(None), ChatAnalytics.query != "")
            .group_by(ChatAnalytics.query)
            .order_by(func.count(ChatAnalytics.id).desc(), func.max(ChatAnalytics.created_at).desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        popular = [
            row[0].strip()
            for row in result.all()
            if row and row[0] and row[0].strip()
        ]
    except Exception:
        # Any analytics failure should never break the chat UX.
        popular = []

    questions: list[str] = []
    for question in popular + DEFAULT_QUESTIONS:
        if question not in questions:
            questions.append(question)
        if len(questions) >= limit:
            break
    return questions
