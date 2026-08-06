"""
seed_data.py — Seeds Arthur Jarvis University knowledge base into Supabase.

Run from the backend directory:
    python -m src.seed_data
"""

import asyncio
import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from src.config import settings
from src.db import Document, DocumentChunk, init_db, async_session

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
logger = logging.getLogger(__name__)
load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

# ─── AJU Knowledge Base ───────────────────────────────────────────────────────

AJU_KNOWLEDGE = [
    {
        "title": "About Arthur Jarvis University",
        "category": "general",
        "content": (
            "Arthur Jarvis University (AJU) is a private university located in Akpabuyo, "
            "Cross River State, Nigeria. It was founded by Arthur Jarvis and is accredited by "
            "the National Universities Commission (NUC) of Nigeria. The university is committed "
            "to providing quality education that is accessible and relevant to the needs of the "
            "society. The university's motto is 'Excellence in Service'."
        ),
    },
    {
        "title": "AJU Location & Contact",
        "category": "general",
        "content": (
            "Arthur Jarvis University is located at Akpabuyo, Cross River State, Nigeria. "
            "The official website is arthurjarvisuniversity.edu.ng. "
            "The university campus is situated approximately 20 km from Calabar, the state capital. "
            "Students can reach the admissions office via the university portal or by visiting "
            "the administrative block on campus."
        ),
    },
    {
        "title": "AJU Faculties and Departments",
        "category": "academics",
        "content": (
            "Arthur Jarvis University offers programmes in the following faculties:\n"
            "1. Faculty of Engineering: Civil Engineering, Electrical/Electronics Engineering, "
            "Mechanical Engineering, Computer Engineering.\n"
            "2. Faculty of Environmental Sciences: Architecture, Estate Management, Urban and "
            "Regional Planning.\n"
            "3. Faculty of Management Sciences: Accounting, Business Administration, "
            "Economics, Banking and Finance.\n"
            "4. Faculty of Computing: Computer Science, Information Technology, "
            "Cyber Security, Software Engineering.\n"
            "5. Faculty of Basic Medical Sciences: Anatomy, Physiology, Biochemistry.\n"
            "6. Faculty of Sciences: Mathematics, Physics, Chemistry, Biology."
        ),
    },
    {
        "title": "AJU Undergraduate Admission Requirements",
        "category": "admissions",
        "content": (
            "To gain admission into Arthur Jarvis University undergraduate programmes, applicants must:\n"
            "1. Possess a minimum of 5 credits in WAEC/NECO/NABTEB O'Level results, including "
            "English Language and Mathematics, obtained at not more than two sittings.\n"
            "2. Have a valid JAMB UTME score. The cut-off mark is typically 160 and above, "
            "though departmental requirements may vary.\n"
            "3. Sit for and pass the Post-UTME screening examination conducted by AJU.\n"
            "4. Satisfy specific departmental subject requirements (e.g., Physics and Chemistry "
            "for Engineering programmes).\n"
            "Direct Entry candidates require a minimum of 2 A-Level passes or an OND/HND with "
            "Upper Credit in a relevant discipline."
        ),
    },
    {
        "title": "AJU School Fees & Payment",
        "category": "finance",
        "content": (
            "Arthur Jarvis University school fees vary by faculty and programme level. "
            "Generally, tuition fees for undergraduate programmes range from ₦350,000 to ₦600,000 "
            "per session depending on the department. "
            "Fees are payable in instalments: the first instalment is due before registration, "
            "and the second instalment is due mid-semester. "
            "Payments are made through the university's online payment portal or designated bank accounts. "
            "Students should visit the Bursary department or check the university website for "
            "the exact fee schedule for their specific programme."
        ),
    },
    {
        "title": "AJU Student Accommodation",
        "category": "accommodation",
        "content": (
            "Arthur Jarvis University provides on-campus accommodation for students. "
            "The university has separate halls of residence for male and female students. "
            "Accommodation is allocated on a first-come, first-served basis during registration. "
            "Students who wish to stay off-campus must notify the Dean of Student Affairs. "
            "To apply for accommodation, students should visit the Student Affairs office with "
            "their admission letter, payment receipt, and a completed accommodation form. "
            "Hostel fees are separate from tuition and are paid directly to the Bursary."
        ),
    },
    {
        "title": "AJU Academic Calendar & Examinations",
        "category": "academics",
        "content": (
            "The academic year at Arthur Jarvis University is divided into two semesters. "
            "The first semester typically runs from October/November to February/March, "
            "and the second semester runs from March/April to July/August. "
            "Semester examinations are held at the end of each semester. "
            "Students are required to maintain a minimum attendance of 75% to be eligible "
            "to sit for examinations. "
            "Results are released through the student portal. "
            "Students with grievances about results may apply for a script review through "
            "the Examinations and Records office."
        ),
    },
    {
        "title": "AJU Student Services & Support",
        "category": "student-services",
        "content": (
            "Arthur Jarvis University offers a range of student support services including:\n"
            "- Health Centre: Provides basic medical care for students on campus.\n"
            "- Counselling Services: Academic and personal counselling is available through "
            "the Dean of Student Affairs office.\n"
            "- Library: The university library is equipped with physical and digital resources. "
            "Students have access to online academic databases.\n"
            "- ICT Centre: Provides internet access and computer facilities for students.\n"
            "- Sports & Recreation: The university has facilities for football, basketball, "
            "and other sports activities.\n"
            "- Student Union Government (SUG): Represents student interests and organizes "
            "cultural and academic events."
        ),
    },
    {
        "title": "AJU Postgraduate Programmes",
        "category": "postgraduate",
        "content": (
            "Arthur Jarvis University offers postgraduate programmes at the Masters and Ph.D. levels "
            "in select departments. "
            "Admission requirements for Masters programmes include a minimum of Second Class Lower "
            "degree (2:2) in a relevant discipline from a recognized university. "
            "Ph.D. candidates must hold a Masters degree with a minimum of Merit in a related field. "
            "Postgraduate students are required to complete coursework and defend a thesis/dissertation. "
            "Interested candidates should contact the School of Postgraduate Studies or visit "
            "the university's official website for current programme offerings."
        ),
    },
    {
        "title": "AJU Registration & Course Registration Process",
        "category": "academics",
        "content": (
            "Students at Arthur Jarvis University must complete course registration at the beginning "
            "of each semester. The registration process involves:\n"
            "1. Clearing all outstanding fees with the Bursary department.\n"
            "2. Logging into the student portal (via arthurjarvisuniversity.edu.ng).\n"
            "3. Selecting courses for the semester in the portal.\n"
            "4. Obtaining adviser approval from your academic adviser.\n"
            "5. Printing and submitting the signed course form to the department.\n"
            "Late registration attracts a penalty fee. Students who fail to register within "
            "the stipulated period will not be allowed to sit for semester examinations."
        ),
    },
]

# ─── Embedding & Seeding ──────────────────────────────────────────────────────

client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL"),
)


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts via OpenRouter."""
    response = await client.embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=texts,
    )
    return [item.embedding for item in response.data]


async def seed(session: AsyncSession):
    logger.info(f"Seeding {len(AJU_KNOWLEDGE)} AJU knowledge entries...")

    for entry in AJU_KNOWLEDGE:
        # Create parent Document record
        doc = Document(title=entry["title"], category=entry["category"])
        session.add(doc)
        await session.flush()  # populate doc.id

        # Split content into chunks of ~2000 chars (~500 tokens)
        content = entry["content"]
        chunk_size, overlap = 2000, 200
        chunks = []
        start = 0
        while start < len(content):
            chunks.append(content[start : start + chunk_size])
            start += chunk_size - overlap

        if not chunks:
            continue

        logger.info(f"  [{entry['title']}] — generating {len(chunks)} embedding(s)...")
        embeddings = await embed_texts(chunks)

        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            session.add(
                DocumentChunk(
                    document_id=doc.id,
                    content=chunk,
                    embedding=embedding,
                    page_number=idx + 1,
                )
            )

    await session.commit()
    logger.info("✅ Seeding complete!")


async def main():
    logger.info("Connecting to Supabase and initialising schema...")
    await init_db()
    logger.info("Schema ready. Starting seed...")
    async with async_session() as session:
        await seed(session)


if __name__ == "__main__":
    asyncio.run(main())
