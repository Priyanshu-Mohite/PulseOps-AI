"""
Notion to Neon PostgreSQL Sync Service & Vector Search Engine.
Implements:
1. Delta Sync: Hits POST /v1/search (sorted by last_edited_time desc), filters pages edited after last_sync.
2. Fast Markdown Ingestion: Hits GET /v1/pages/{page_id}/markdown for single-request clean markdown.
3. Semantic Chunking: Splits markdown by sections/paragraphs (~500 chars).
4. Atomic Neon DB Update: Deletes old chunks for modified pages and inserts new embeddings.
5. Vector Search: Performs fast cosine similarity queries over document_chunks.
"""

import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import requests
import psycopg2
from psycopg2.extras import RealDictCursor

from src.config import config
from src.database.models import get_db_connection, init_db
from src.database.embeddings import generate_embeddings, generate_single_embedding

NOTION_HEADERS = {
    "Authorization": f"Bearer {config.NOTION_API_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}


# ============================================================================
# Markdown Chunking Helper
# ============================================================================

def chunk_markdown(text: str, chunk_size: int = 500, overlap: int = 80) -> List[str]:
    """
    Split markdown text into logical chunks, preserving paragraphs and section boundaries.
    """
    if not text or not text.strip():
        return []

    # Clean empty-block tags from Notion markdown
    cleaned = re.sub(r'<empty-block\s*/>', '', text).strip()

    # Split by major headings or double newlines
    paragraphs = [p.strip() for p in cleaned.split("\n\n") if p.strip()]

    chunks = []
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 <= chunk_size:
            current_chunk = f"{current_chunk}\n\n{para}" if current_chunk else para
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            # Handle exceptionally large paragraphs
            if len(para) > chunk_size:
                words = para.split()
                temp_chunk = ""
                for w in words:
                    if len(temp_chunk) + len(w) + 1 <= chunk_size:
                        temp_chunk = f"{temp_chunk} {w}" if temp_chunk else w
                    else:
                        chunks.append(temp_chunk.strip())
                        temp_chunk = w
                current_chunk = temp_chunk
            else:
                current_chunk = para

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


# ============================================================================
# Notion Sync Core Logic
# ============================================================================

def get_last_sync_timestamp(conn) -> Optional[datetime]:
    """Retrieve last_global_sync timestamp from sync_metadata table."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT last_global_sync FROM sync_metadata WHERE id = 1;")
        row = cur.fetchone()
        return row["last_global_sync"] if row else None


def update_sync_metadata(conn, sync_time: datetime, total_pages: int):
    """Upsert last_global_sync timestamp in sync_metadata table."""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO sync_metadata (id, last_global_sync, total_pages_synced)
            VALUES (1, %s, %s)
            ON CONFLICT (id) DO UPDATE 
            SET last_global_sync = EXCLUDED.last_global_sync,
                total_pages_synced = EXCLUDED.total_pages_synced;
        """, (sync_time, total_pages))
    conn.commit()


def fetch_notion_markdown(page_id: str) -> str:
    """Fetch clean markdown directly from Notion's GET /v1/pages/{page_id}/markdown endpoint."""
    url = f"https://api.notion.com/v1/pages/{page_id}/markdown"
    res = requests.get(url, headers=NOTION_HEADERS, timeout=12)
    if res.status_code == 200:
        return res.json().get("markdown", "")
    return ""


def run_notion_sync() -> Dict[str, Any]:
    """
    Executes the Delta Sync process:
    1. Reads last sync time from Neon DB.
    2. Calls POST /v1/search (sorted by last_edited_time desc).
    3. Finds pages where last_edited_time > last_sync.
    4. Fetches markdown via GET /v1/pages/{id}/markdown.
    5. Chunks, embeds, and updates Neon DB atomically.
    """
    init_db()  # Ensure tables exist
    conn = get_db_connection()

    try:
        last_sync = get_last_sync_timestamp(conn)

        # 1. Hit Notion Search API
        search_url = "https://api.notion.com/v1/search"
        payload = {
            "filter": {"value": "page", "property": "object"},
            "sort": {"direction": "descending", "timestamp": "last_edited_time"},
            "page_size": 20
        }
        res = requests.post(search_url, headers=NOTION_HEADERS, json=payload, timeout=12)
        if res.status_code != 200:
            return {"status": "error", "message": f"Notion Search failed: {res.text}"}

        all_pages = res.json().get("results", [])
        pages_to_sync = []

        for page in all_pages:
            page_id = page.get("id")
            last_edited_str = page.get("last_edited_time")
            # Parse ISO 8601 timestamp
            page_last_edited = datetime.fromisoformat(last_edited_str.replace("Z", "+00:00"))

            # Extract title
            title = "Untitled"
            props = page.get("properties", {})
            for _, val in props.items():
                if val.get("type") == "title":
                    t_objs = val.get("title", [])
                    if t_objs:
                        title = t_objs[0].get("plain_text", "Untitled")
                    break

            # If never synced, or page was edited after last_sync
            if last_sync is None or page_last_edited > last_sync:
                pages_to_sync.append({
                    "id": page_id,
                    "title": title,
                    "last_edited": page_last_edited
                })

        if not pages_to_sync:
            return {
                "status": "success",
                "message": "Already up to date. No pages edited since last sync.",
                "synced_count": 0,
                "last_sync": last_sync.isoformat() if last_sync else None
            }

        total_chunks_inserted = 0

        # 2. Process modified pages
        for page_info in pages_to_sync:
            pid = page_info["id"]
            title = page_info["title"]
            last_edited = page_info["last_edited"]

            # Fetch full page markdown in 1 single call
            md_content = fetch_notion_markdown(pid)
            if not md_content:
                continue

            # Split into chunks
            chunks = chunk_markdown(md_content, chunk_size=500)
            if not chunks:
                continue

            # Generate embeddings locally on CPU (0-cost)
            embeddings = generate_embeddings(chunks)

            # Atomic database transaction for this page
            with conn.cursor() as cur:
                # Remove stale chunks for this page
                cur.execute("DELETE FROM document_chunks WHERE page_id = %s;", (pid,))

                # Insert new chunks with vector embeddings
                insert_query = """
                    INSERT INTO document_chunks 
                    (page_id, title, chunk_index, content, page_last_edited, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s);
                """
                for idx, (chunk_text, emb) in enumerate(zip(chunks, embeddings)):
                    cur.execute(insert_query, (pid, title, idx, chunk_text, last_edited, emb))

            conn.commit()
            total_chunks_inserted += len(chunks)

        # 3. Update sync metadata timestamp
        current_time = datetime.now(timezone.utc)
        update_sync_metadata(conn, current_time, len(all_pages))

        return {
            "status": "success",
            "message": f"Sync completed successfully. Synced {len(pages_to_sync)} page(s) ({total_chunks_inserted} chunks).",
            "pages_synced": [p["title"] for p in pages_to_sync],
            "total_chunks": total_chunks_inserted,
            "sync_time": current_time.isoformat()
        }

    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": f"Exception during sync: {str(e)}"}
    finally:
        conn.close()


# ============================================================================
# Vector Semantic Search Core Logic
# ============================================================================

def search_similar_chunks(query: str, top_k: int = 4) -> List[Dict[str, Any]]:
    """
    Search document_chunks in Neon PostgreSQL using cosine distance (<=>).
    Returns the top_k most semantically relevant text chunks.
    """
    query_emb = generate_single_embedding(query)
    if not query_emb:
        return []

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # <=> operator calculates cosine distance in pgvector
            search_sql = """
                SELECT 
                    id,
                    page_id,
                    title,
                    chunk_index,
                    content,
                    page_last_edited,
                    1 - (embedding <=> %s::vector) AS similarity_score
                FROM document_chunks
                ORDER BY embedding <=> %s::vector
                LIMIT %s;
            """
            cur.execute(search_sql, (query_emb, query_emb, top_k))
            results = cur.fetchall()
            return [dict(r) for r in results]
    finally:
        conn.close()


if __name__ == "__main__":
    print("[1/2] Running Delta Notion Sync...")
    sync_res = run_notion_sync()
    print(sync_res)

    print("\n[2/2] Running Vector Similarity Search on Neon DB...")
    search_query = "What is the launch date and database migration dependency for Project Phoenix?"
    matches = search_similar_chunks(search_query, top_k=2)
    for m in matches:
        print(f"\n[Score: {m['similarity_score']:.4f}] {m['title']} (Chunk {m['chunk_index']}):")
        print(m['content'])
