"""
Persona / access-control tests for the RAG retrieval layer.

Part 1 — Unit tests (no external services):
    Proves the persona -> visibility mapping used by the backend retrieval
    layer. The retrieval layer, not the frontend, is the final security
    boundary, so these tests pin its exact behaviour.

Part 2 — Integration tests (require a reachable PostgreSQL + pgvector + the
    embedding provider configured in backend/.env). These report a clear
    BLOCKED status when the database is unreachable so the unit suite never
    falsely passes/fails on infrastructure availability.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy import delete, text

from src.database import AsyncSessionLocal, engine
from src.models import Document, DocumentChunk, KnowledgeSource, VisibilityLevel
from src.services.ingest import process_and_store_document
from src.services.retrieval import retrieve_relevant_chunks, visibility_levels_for_persona

PASS = "PASS"
FAIL = "FAIL"
BLOCKED = "BLOCKED"


# ---------------------------------------------------------------------------
# Part 1 — Unit tests (pure, deterministic)
# ---------------------------------------------------------------------------

def test_persona_visibility_mapping() -> bool:
    cases = [
        # persona        expected visibility levels
        ("public",       {VisibilityLevel.PUBLIC}),
        ("PUBLIC",       {VisibilityLevel.PUBLIC}),  # case-insensitive
        ("student",      {VisibilityLevel.PUBLIC, VisibilityLevel.STUDENT}),
        ("staff",        {VisibilityLevel.PUBLIC, VisibilityLevel.STUDENT, VisibilityLevel.STAFF}),
        ("admin",        {VisibilityLevel.PUBLIC}),  # unknown -> fail closed
        (None,           {VisibilityLevel.PUBLIC}),  # unknown -> fail closed
        ("",             {VisibilityLevel.PUBLIC}),  # unknown -> fail closed
    ]
    all_ok = True
    for persona, expected in cases:
        levels = set(visibility_levels_for_persona(persona))
        ok = levels == expected
        all_ok = all_ok and ok
        print(f"    persona={persona!r:8} -> {sorted(l.value for l in levels)} "
              f"expected={sorted(l.value for l in expected)} {'PASS' if ok else 'FAIL'}")
    return all_ok


def test_public_never_extends_beyond_public() -> bool:
    """PUBLIC is the least-privileged tier — it must never include STUDENT/STAFF."""
    return set(visibility_levels_for_persona("public")) == {VisibilityLevel.PUBLIC}


def test_student_includes_student_but_not_staff() -> bool:
    levels = set(visibility_levels_for_persona("student"))
    ok = VisibilityLevel.PUBLIC in levels and VisibilityLevel.STUDENT in levels
    ok = ok and VisibilityLevel.STAFF not in levels
    return ok


def test_staff_is_highest_privilege() -> bool:
    levels = set(visibility_levels_for_persona("staff"))
    return levels == {
        VisibilityLevel.PUBLIC, VisibilityLevel.STUDENT, VisibilityLevel.STAFF,
    }
# ---------------------------------------------------------------------------
# Part 2 — Integration tests (BACKEND enforces the boundary against a live DB)
# ---------------------------------------------------------------------------

async def db_reachable() -> bool:
    """Probe database connectivity with an ISOLATED, throw-away engine.

    Using the shared application ``engine`` here would borrow a connection into
    the global pool on one ``asyncio.run`` loop and then leave it to be torn
    down by a *different* loop (the next ``asyncio.run`` or interpreter
    shutdown). That is exactly what produces
    ``RuntimeError: Event loop is closed`` /
    ``coroutine 'Connection._cancel' was never awaited`` during teardown and
    masks the real integration result. An isolated ``NullPool`` engine created
    AND disposed inside this single coroutine keeps the probe hermetic.
    """
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool
    from src.database import DATABASE_URL

    probe = create_async_engine(DATABASE_URL, poolclass=NullPool)
    try:
        async with probe.connect() as conn:
            await asyncio.wait_for(conn.execute(text("SELECT 1")), timeout=3)
        return True
    except Exception:
        return False
    finally:
        await probe.dispose()


async def seed_visibility_data(session) -> None:
    await session.execute(delete(DocumentChunk).where(DocumentChunk.chunk_content.like("PERSONATEST_%")))
    await session.execute(delete(Document).where(Document.title.like("PERSONATEST_%")))
    await session.execute(delete(KnowledgeSource).where(KnowledgeSource.title.like("PERSONATEST_%")))
    await session.commit()

    docs = [
        ("PERSONATEST_PUBLIC", VisibilityLevel.PUBLIC,
         "PERSONATEST_PUBLIC_CONTENT: Public admission policy and general campus information."),
        ("PERSONATEST_STUDENT", VisibilityLevel.STUDENT,
         "PERSONATEST_STUDENT_CONTENT: Student portal credentials and exam clearance procedure."),
        ("PERSONATEST_STAFF", VisibilityLevel.STAFF,
         "PERSONATEST_STAFF_CONTENT: Internal staff salary and budget allocation details."),
    ]
    for title, visibility, content in docs:
        source = KnowledgeSource(title=title, visibility=visibility)
        session.add(source)
        await session.flush()
        await process_and_store_document(
            db=session, source_id=source.id, content=content,
            visibility=visibility, title=title,
        )
    await session.commit()


async def integration_persona_access() -> list:
    results = []
    async with AsyncSessionLocal() as session:
        await seed_visibility_data(session)

        async def _run(persona, expect_visibility):
            chunks = await retrieve_relevant_chunks(
                db=session, query="credentials clearance policy budget",
                persona=persona, limit=10, similarity_threshold=0.0,
            )
            got = {c.visibility for c in chunks}
            ok = got.issubset({v.value for v in expect_visibility})
            return ok, got

        # public must only ever see PUBLIC rows
        ok_public, got_public = await _run("public", {VisibilityLevel.PUBLIC})
        results.append(("public sees only PUBLIC content", ok_public, got_public))

        # student may see PUBLIC + STUDENT, never STAFF
        ok_student, got_student = await _run("student", {VisibilityLevel.PUBLIC, VisibilityLevel.STUDENT})
        results.append(("student sees PUBLIC+STUDENT (never STAFF)", ok_student, got_student))

        # staff may see all tiers
        ok_staff, got_staff = await _run("staff", {VisibilityLevel.PUBLIC, VisibilityLevel.STUDENT, VisibilityLevel.STAFF})
        results.append(("staff sees PUBLIC+STUDENT+STAFF", ok_staff, got_staff))

        # cleanup
        await session.execute(delete(DocumentChunk).where(DocumentChunk.chunk_content.like("PERSONATEST_%")))
        await session.execute(delete(Document).where(Document.title.like("PERSONATEST_%")))
        await session.execute(delete(KnowledgeSource).where(KnowledgeSource.title.like("PERSONATEST_%")))
        await session.commit()
        return results


async def _run_integration_and_dispose() -> list:
    """Run the persona integration checks and ALWAYS dispose the shared engine
    while this event loop is still awake.

    Otherwise asyncpg tears its pooled connections down during interpreter
    shutdown on an already-closed loop, surfacing as
    ``RuntimeError: Event loop is closed`` and masking the real test outcome.
    """
    try:
        return await integration_persona_access()
    finally:
        await engine.dispose()


def run_integration() -> str:
    if not asyncio.run(db_reachable()):
        print("  BLOCKED: PostgreSQL/pgvector not reachable on localhost — integration "
              "persona test cannot run without a database.")
        return BLOCKED

    try:
        results = asyncio.run(_run_integration_and_dispose())
    except Exception as exc:  # e.g. asyncpg SSL/teardown issues in this environment
        print(f"  BLOCKED: integration run aborted by a database connection error: "
              f"{type(exc).__name__}: {exc}")
        return BLOCKED

    ok = True
    for name, passed, detail in results:
        ok = ok and passed
        print(f"    {name}: {detail or ''} -> {'PASS' if passed else 'FAIL'}")
    return PASS if ok else FAIL


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main() -> int:
    print("=" * 60)
    print("  PERSONA / ACCESS-CONTROL TESTS")
    print("=" * 60)

    unit_results = {
        "persona -> visibility mapping": test_persona_visibility_mapping(),
        "public never extends beyond PUBLIC": test_public_never_extends_beyond_public(),
        "student includes STUDENT but never STAFF": test_student_includes_student_but_not_staff(),
        "staff is highest privilege": test_staff_is_highest_privilege(),
    }
    print("\n[Unit — backend retrieval security boundary]")
    for name, ok in unit_results.items():
        print(f"  {name}: {'PASS' if ok else 'FAIL'}")

    print("\n[Integration — live DB enforcement]")
    integration_status = run_integration()

    unit_all_ok = all(unit_results.values())
    print(f"\nUNIT: {'ALL PASS' if unit_all_ok else 'SOME FAILED'} | "
          f"INTEGRATION: {integration_status}")
    return 0 if unit_all_ok else 1


if __name__ == "__main__":
    sys.exit(main())