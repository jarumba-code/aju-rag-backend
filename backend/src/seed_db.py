import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import engine, Base, AsyncSessionLocal
from src.models import Department, Category, SystemSetting, VisibilityLevel

async def init_and_seed_db():
    print("🔄 Creating updated database tables in Supabase...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables created successfully.")

    async with AsyncSessionLocal() as session:
        async with session.begin():
            # 1. Seed Core Departments
            departments = [
                "Information Technology Centre",
                "Admissions",
                "Registry",
                "Bursary",
                "Library",
                "General Administration"
            ]
            for dept_name in departments:
                existing = await session.execute(
                    Base.metadata.tables["departments"].select().where(
                        Base.metadata.tables["departments"].c.name == dept_name
                    )
                )
                if not existing.scalar_one_or_none():
                    session.add(Department(name=dept_name))

            # 2. Seed Core Categories
            categories = [
                ("Course Registration", "Guides and troubleshooting for course enrollment"),
                ("Exam Clearance", "Clearance steps, requirements, and fee verification"),
                ("Admissions & Tuition", "Prospective student inquiries and fee schedules"),
                ("Hostel & Accommodation", "Campus lodging rules and allocation"),
                ("Portal Support", "Password resets, payment updates, and technical bugs")
            ]
            for cat_name, desc in categories:
                existing = await session.execute(
                    Base.metadata.tables["categories"].select().where(
                        Base.metadata.tables["categories"].c.name == cat_name
                    )
                )
                if not existing.scalar_one_or_none():
                    session.add(Category(name=cat_name, description=desc))

            # 3. Seed Default System Settings
            default_settings = {
                "confidence_threshold": "0.42",
                "max_retrieved_chunks": "5",
                "redis_cache_ttl_student_sec": "3600",   # 1 hour
                "redis_cache_ttl_public_sec": "86400"   # 24 hours
            }
            for key, val in default_settings.items():
                existing = await session.execute(
                    Base.metadata.tables["system_settings"].select().where(
                        Base.metadata.tables["system_settings"].c.key == key
                    )
                )
                if not existing.scalar_one_or_none():
                    session.add(SystemSetting(key=key, value=val))

        await session.commit()
    print("🌱 Default departments, categories, and system settings seeded!")

if __name__ == "__main__":
    asyncio.run(init_and_seed_db())