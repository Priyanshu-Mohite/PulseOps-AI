"""
Database connection and schema setup for Neon PostgreSQL + pgvector.
Creates:
1. sync_metadata: Tracks the timestamp of the last Notion sync.
2. document_chunks: Stores chunked markdown text and 384-dimensional vector embeddings.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from src.config import config


def get_db_connection():
    """Returns a new psycopg2 connection to Neon PostgreSQL."""
    return psycopg2.connect(config.DATABASE_URL)


def init_db():
    """
    Initializes pgvector extension and creates necessary tables if they don't exist.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 1. Enable pgvector
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

        # 2. Table: sync_metadata
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sync_metadata (
                id INT PRIMARY KEY DEFAULT 1,
                last_global_sync TIMESTAMP WITH TIME ZONE NOT NULL,
                total_pages_synced INT DEFAULT 0,
                CONSTRAINT single_row CHECK (id = 1)
            );
        """)

        # 3. Table: document_chunks
        # fastembed (BAAI/bge-small-en-v1.5) uses 384 dimensions
        cur.execute("""
            CREATE TABLE IF NOT EXISTS document_chunks (
                id SERIAL PRIMARY KEY,
                page_id VARCHAR(64) NOT NULL,
                title TEXT,
                chunk_index INT NOT NULL,
                content TEXT NOT NULL,
                page_last_edited TIMESTAMP WITH TIME ZONE,
                embedding vector(384),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 4. Create an index for vector similarity search (cosine distance)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding 
            ON document_chunks USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 10);
        """)

        # 5. Index for fast page_id lookups during deletion/re-sync
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_document_chunks_page_id 
            ON document_chunks (page_id);
        """)

        conn.commit()
        print("SUCCESS: Database tables (sync_metadata, document_chunks) initialized successfully!")
    except Exception as e:
        conn.rollback()
        print(f"Error initializing database: {e}")
        raise e
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    init_db()
