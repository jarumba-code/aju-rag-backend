import asyncio
from src.database import engine
from sqlalchemy import text

async def main():
    print("Starting database schema migration...")
    async with engine.begin() as conn:
        # 1. Create documents table if it doesn't exist
        print("Creating 'documents' table if not exists...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS documents (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                title VARCHAR,
                filename VARCHAR,
                file_hash VARCHAR UNIQUE NOT NULL,
                department VARCHAR,
                doc_type VARCHAR,
                source_name VARCHAR,
                chunk_count INTEGER DEFAULT 0 NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
            );
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_documents_id ON documents(id);"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_documents_file_hash ON documents(file_hash);"))
        print("  'documents' table created/verified.")

        # 2. Add document_id column to document_chunks table if not exists
        print("Adding 'document_id' column to 'document_chunks' if not exists...")
        await conn.execute(text("""
            ALTER TABLE document_chunks
            ADD COLUMN IF NOT EXISTS document_id UUID REFERENCES documents(id) ON DELETE CASCADE;
        """))
        print("  'document_id' column added.")

        # 3. Double check if foreign key constraint is correct
        print("Verifying schema of document_chunks...")
        result = await conn.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'document_chunks' AND column_name = 'document_id';
        """))
        row = result.fetchone()
        if row:
            print(f"  Success: Column '{row[0]}' exists with type '{row[1]}'.")
        else:
            print("  Warning: Column 'document_id' could not be found.")

if __name__ == "__main__":
    asyncio.run(main())
