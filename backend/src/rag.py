import io
import uuid
import logging
from typing import AsyncGenerator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from openai import AsyncOpenAI
from pgvector.sqlalchemy import Vector
from src.config import settings
from src.db import Document, DocumentChunk

logger = logging.getLogger(__name__)

# Initialize AsyncOpenAI client for OpenRouter
openai_client = AsyncOpenAI(
    api_key=settings.OPENROUTER_API_KEY,
    base_url=settings.OPENROUTER_BASE_URL,
)


def extract_text_from_pdf(file_bytes: bytes) -> list[dict]:
    """
    Extracts text page-by-page from raw PDF bytes.
    Tries PyMuPDF (fitz) first, then falls back to pypdf.
    """
    # 1. Try fitz (PyMuPDF)
    try:
        import fitz
        pages = []
        with fitz.open(stream=file_bytes, filetype="pdf") as doc:
            for page_num, page in enumerate(doc, start=1):
                text = page.get_text().strip()
                if text:
                    pages.append({"page": page_num, "text": text})
        return pages
    except ImportError:
        pass

    # 2. Try pypdf
    try:
        import pypdf
        pages = []
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text()
            if text:
                text = text.strip()
                pages.append({"page": page_num, "text": text})
        return pages
    except ImportError:
        pass

    raise RuntimeError(
        "Neither PyMuPDF (fitz) nor pypdf is installed. Please install one of them."
    )


def chunk_text(text: str, chunk_size: int = 2000, overlap: int = 200) -> list[str]:
    """
    Simple sliding-window character chunker.
    chunk_size=2000 chars (~500 tokens), overlap=200 chars (~50 tokens)
    """
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


async def get_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Generates embeddings from OpenAI for a list of texts.
    """
    if not texts:
        return []
    response = await openai_client.embeddings.create(
        input=texts, model=settings.EMBEDDING_MODEL
    )
    return [item.embedding for item in response.data]


async def ingest_document(file_bytes: bytes, filename: str, session: AsyncSession) -> Document:
    """
    Ingests a document: parses it, chunks the text, embeds chunks, and saves to DB.
    """
    # Create Document entry
    doc = Document(title=filename)
    session.add(doc)
    await session.flush()

    # Extract text by pages
    pages = extract_text_from_pdf(file_bytes)
    
    all_chunks_data = []
    for page in pages:
        page_num = page["page"]
        text_content = page["text"]
        chunks = chunk_text(text_content)
        
        if not chunks:
            continue
            
        embeddings = await get_embeddings(chunks)
        
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            all_chunks_data.append(
                DocumentChunk(
                    document_id=doc.id,
                    content=chunk,
                    embedding=embedding,
                    page_number=page_num,
                )
            )

    if all_chunks_data:
        session.add_all(all_chunks_data)
        
    await session.commit()
    return doc


async def search_similar_chunks(
    query: str, session: AsyncSession, top_k: int = 4
) -> list[dict]:
    """
    Retrieves chunks from pgvector using cosine distance similarity.
    """
    # 1. Embed query
    query_emb_resp = await openai_client.embeddings.create(
        input=[query], model=settings.EMBEDDING_MODEL
    )
    query_embedding = query_emb_resp.data[0].embedding

    # 2. Similarity search using cosine distance (<-> operator)
    stmt = (
        select(
            DocumentChunk.content,
            DocumentChunk.page_number,
            (1 - DocumentChunk.embedding.cosine_distance(query_embedding)).label("score")
        )
        .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
        .limit(top_k)
    )
    
    result = await session.execute(stmt)
    rows = result.all()
    
    return [
        {
            "content": row[0],
            "page_number": row[1],
            "score": float(row[2])
        }
        for row in rows
    ]


async def stream_rag_response(
    query: str, session: AsyncSession
) -> AsyncGenerator[str, None]:
    """
    Generates a streaming RAG answer using search results and GPT completions.
    """
    # Fetch top similar document chunks
    try:
        chunks = await search_similar_chunks(query, session, top_k=4)
    except Exception as e:
        logger.error(f"Search similar chunks error: {e}")
        chunks = []

    # Format context
    context = ""
    if chunks:
        context = "\n\n".join(
            f"[Page {c['page_number']}]: {c['content']}" for c in chunks
        )

    # Construct prompt
    system_prompt = (
        "You are an assistant for Arthur Jarvis University (Arthur Jarvis University, Nigeria). "
        "Answer questions based on the provided context. If the answer is not in the context, "
        "rely on general facts about university regulations or health/support services, but be precise. "
        "Be polite, clear, and student-focused."
    )
    
    user_prompt = f"Context:\n{context}\n\nQuestion: {query}\nAnswer:"
    
    try:
        response = await openai_client.chat.completions.create(
            model=settings.DEFAULT_LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            stream=True,
            temperature=0.3,
        )
        
        async for chunk in response:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content
    except Exception as e:
        yield f"\n[Error generating response: {str(e)}]"
