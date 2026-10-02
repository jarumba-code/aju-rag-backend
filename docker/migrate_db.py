"""Database initialisation for container startup.

Reuses the project's EXISTING mechanism (no second migration system):
  1. CREATE EXTENSION IF NOT EXISTS vector  (pgvector; models use Vector(1536))
  2. src.seed_db.init_and_seed_db()         (create_all + idempotent seeding)

This is safe to run on every container start: the extension statement and
create_all are IF-NOT-EXISTS, and the seeder checks each row before insert.
It never drops tables and never overwrites existing data.
"""

import asyncio
import sys

sys.path.insert(0, "/app/backend")


async def main() -> None:
    from sqlalchemy import text

    from src.database import engine
    from src.seed_db import init_and_seed_db

    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
    await engine.dispose()

    # Creates tables (same call the FastAPI startup event makes) and seeds
    # departments / categories / system settings only when missing.
    await init_and_seed_db()


if __name__ == "__main__":
    asyncio.run(main())
