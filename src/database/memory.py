"""
PulseOps AI - Dual-Layer Memory Architecture (Phase 3)
Implements:
1. Short-Term Memory: Thread-level PostgreSQL Checkpointer via LangGraph PostgresSaver.
2. Long-Term Memory: User-level persistent facts stored in Neon DB with 384-dim vector embeddings.
3. Memory Gatekeeper: Inspects user messages to distinguish durable facts from transient queries,
   preventing context bloat.
"""

import re
from typing import Dict, List, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from langgraph.checkpoint.postgres import PostgresSaver

from src.config import config
from src.database.models import get_db_connection
from src.database.embeddings import generate_single_embedding


# ============================================================================
# 1. Database Schema for Long-Term Memory
# ============================================================================

def init_memory_db():
    """
    Ensures the user_long_term_memories table and vector index exist in Neon DB.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Table for persistent user-level facts
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_long_term_memories (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(128) NOT NULL,
                fact_text TEXT NOT NULL,
                category VARCHAR(64) DEFAULT 'fact',
                embedding vector(384),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Vector cosine similarity index
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_memories_embedding 
            ON user_long_term_memories USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 10);
        """)

        # Fast lookup by user_id
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_memories_user_id 
            ON user_long_term_memories (user_id);
        """)

        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


# ============================================================================
# 2. Short-Term Memory (PostgreSQL Checkpointer)
# ============================================================================

def get_short_term_checkpointer():
    """
    Returns a LangGraph PostgresSaver context manager connected to Neon DB.
    Usage:
        with get_short_term_checkpointer() as checkpointer:
            # pass checkpointer to graph.compile(checkpointer=checkpointer)
    """
    return PostgresSaver.from_conn_string(config.DATABASE_URL)


# ============================================================================
# 3. Long-Term Memory Operations
# ============================================================================

def save_long_term_memory(user_id: str, fact_text: str, category: str = "fact") -> Dict[str, Any]:
    """
    Persists a durable fact into Neon PostgreSQL with a 384-dimensional vector embedding.
    """
    if not user_id or not fact_text:
        return {"status": "error", "message": "user_id and fact_text are required"}

    # Generate 384-dim embedding
    emb = generate_single_embedding(fact_text)
    if not emb:
        return {"status": "error", "message": "Failed to generate embedding for memory fact"}

    init_memory_db()
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Check for near-duplicate memory to avoid redundancy
            cur.execute("""
                SELECT id, fact_text, 1 - (embedding <=> %s::vector) AS similarity
                FROM user_long_term_memories
                WHERE user_id = %s
                ORDER BY embedding <=> %s::vector
                LIMIT 1;
            """, (emb, user_id, emb))
            existing = cur.fetchone()

            # If existing fact is > 95% similar, update timestamp or skip
            if existing and existing["similarity"] >= 0.95:
                return {
                    "status": "skipped",
                    "message": f"Similar fact already remembered: '{existing['fact_text']}'",
                    "memory_id": existing["id"]
                }

            cur.execute("""
                INSERT INTO user_long_term_memories (user_id, fact_text, category, embedding)
                VALUES (%s, %s, %s, %s)
                RETURNING id, created_at;
            """, (user_id, fact_text.strip(), category, emb))
            row = cur.fetchone()
            conn.commit()
            return {
                "status": "saved",
                "memory_id": row["id"],
                "user_id": user_id,
                "fact": fact_text.strip(),
                "category": category,
                "created_at": str(row["created_at"])
            }
    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()


def search_long_term_memory(user_id: str, query: str, top_k: int = 3, threshold: float = 0.55) -> List[Dict[str, Any]]:
    """
    Recalls the most relevant durable facts for a user using cosine distance (<=>).
    """
    if not user_id or not query:
        return []

    query_emb = generate_single_embedding(query)
    if not query_emb:
        return []

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    id,
                    fact_text,
                    category,
                    created_at,
                    1 - (embedding <=> %s::vector) AS similarity_score
                FROM user_long_term_memories
                WHERE user_id = %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s;
            """, (query_emb, user_id, query_emb, top_k))
            rows = cur.fetchall()
            # Filter by relevance threshold
            return [dict(r) for r in rows if r["similarity_score"] >= threshold]
    except Exception as e:
        print(f"[ERROR] search_long_term_memory: {e}")
        return []
    finally:
        conn.close()


# ============================================================================
# 4. Memory Gatekeeper: Evaluates Fact Durability
# ============================================================================

def memory_gatekeeper(user_message: str) -> Dict[str, Any]:
    """
    Inspects user input to decide if it shares a durable, long-term fact
    (role, company priority, critical rule, personal preference)
    or if it is merely a transient question/task.
    
    Returns:
        {
            "is_durable": bool,
            "fact": Optional[str],
            "category": Optional[str] ('role', 'priority', 'rule', 'preference', 'fact')
        }
    """
    if not user_message or not user_message.strip():
        return {"is_durable": False, "fact": None, "category": None}

    text = user_message.strip()

    # Rule 1: Questions are NEVER durable facts (What, Why, Where, How, List, Show, etc.)
    if text.endswith("?") or re.match(r"^(what|why|how|where|when|who|is|are|can|could|show|list|tell|summarize|give)\b", text, re.I):
        return {"is_durable": False, "fact": None, "category": None}

    # Rule 2: Greetings or conversational acknowledgments
    if re.match(r"^(hi|hello|hey|thanks|thank you|ok|okay|cool|got it|bye|good morning)\b", text, re.I):
        return {"is_durable": False, "fact": None, "category": None}

    # Rule 3: Role declaration
    # e.g., "I am the DevOps Lead", "My role is QA Engineer", "I manage the database"
    role_match = re.search(r"(?:i am|i'm|my role is|my job is|i work as)\s+(?:the\s+|a\s+|an\s+)?([a-z0-9_\-\s]+)", text, re.I)
    if role_match:
        role = role_match.group(1).strip()
        # Ensure it's not a verb phrase
        if len(role.split()) <= 6 and not role.lower().startswith(("asking", "looking", "trying", "doing")):
            return {
                "is_durable": True,
                "fact": f"User's role: {role}",
                "category": "role"
            }

    # Rule 4: Priority declaration
    # e.g., "Project Phoenix is our #1 priority this quarter", "Priority #1 is latency"
    if re.search(r"\b(priority|top priority|#1 priority|most important|critical goal)\b", text, re.I):
        return {
            "is_durable": True,
            "fact": text,
            "category": "priority"
        }

    # Rule 5: Strict Operational Rule declaration
    # e.g., "Never deploy to prod without approval", "Always tag the DevOps team for DB changes"
    if re.search(r"\b(never\s+[a-z]+|always\s+[a-z]+|do not\s+[a-z]+|strict rule|policy is)\b", text, re.I):
        return {
            "is_durable": True,
            "fact": text,
            "category": "rule"
        }

    # Rule 6: Explicit memory request
    # e.g., "Remember that...", "Keep in mind that...", "Note that..."
    rem_match = re.search(r"^(?:please\s+)?(?:remember|keep in mind|note that|save to memory)\s+(?:that\s+)?(.+)", text, re.I)
    if rem_match:
        return {
            "is_durable": True,
            "fact": rem_match.group(1).strip(),
            "category": "preference"
        }

    # Default: It is a standard prompt, transient in nature
    return {"is_durable": False, "fact": None, "category": None}
