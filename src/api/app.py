"""
PulseOps AI - FastAPI Backend API Server (Phase 6)
Wraps the compiled LangGraph Multi-Hop Cyclic Workflow into an enterprise REST API.
Returns the complete transparent intermediate state across all 6 panels.
"""

from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.config import config
from src.agent.graph import run_agent_workflow
from src.database.memory import get_all_user_memories, search_long_term_memory

# 1. Initialize FastAPI Application
app = FastAPI(
    title="PulseOps AI Backend",
    version="1.0.0",
    description="Autonomous Enterprise Agentic RAG bridging Notion Architecture with live Jira Execution via MCP & LangGraph."
)

# 2. Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 3. Pydantic Request & Response Schemas
class QueryRequest(BaseModel):
    question: str = Field(..., description="The user's query or status question")
    user_id: Optional[str] = Field("default_user", description="User identifier for long-term cross-session vector memory")
    thread_id: Optional[str] = Field("session_001", description="Thread identifier for short-term turn-by-turn conversation checkpointer")


class QueryResponse(BaseModel):
    status: str
    user_query: str
    user_id: str
    thread_id: str
    recalled_memories: List[Dict[str, Any]]
    durable_facts_saved: List[Dict[str, Any]]
    sub_questions: List[str]
    tools_called: List[Dict[str, Any]]
    evidence: List[Dict[str, Any]]
    citations: List[Dict[str, str]]
    final_answer: str
    current_hop: int


# 4. API Endpoints
@app.get("/")
def get_root():
    """Returns system status and active configuration."""
    return {
        "project": "PulseOps AI",
        "description": "Autonomous Enterprise Agentic RAG with Dual-Layer Memory & MCP Decoupled Connectors",
        "version": "1.0.0",
        "integrations": {
            "database": "Neon Serverless PostgreSQL (pgvector enabled)",
            "documentation": f"Notion PRD ({config.NOTION_PAGE_ID[:8]}...)",
            "execution": f"Jira Cloud ({config.JIRA_PROJECT_KEY})",
            "inference": "Groq LPU (openai/gpt-oss-120b)",
            "observability": f"LangSmith Tracing ({config.LANGCHAIN_PROJECT})"
        },
        "endpoints": {
            "health": "/api/health",
            "query": "POST /api/query",
            "memories": "GET /api/memories/{user_id}"
        }
    }


@app.get("/api/health")
def get_health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "jira_configured": bool(config.JIRA_INSTANCE_URL and config.JIRA_API_TOKEN),
        "notion_configured": bool(config.NOTION_API_KEY and config.NOTION_PAGE_ID),
        "neon_db_configured": bool(config.DATABASE_URL),
        "groq_configured": bool(config.GROQ_API_KEY),
        "langsmith_configured": bool(config.LANGCHAIN_TRACING_V2)
    }


@app.post("/api/query", response_model=QueryResponse)
def execute_query(req: QueryRequest):
    """
    Executes the multi-hop LangGraph agent workflow:
    1. Node 1: Recalls long-term facts & gates new durable memories
    2. Node 2: Decomposes query into 3 strategic sub-questions
    3. Node 3: Dispatches Notion & Jira MCP tools over stdio
    4. Node 4: Self-corrects & schedules Hop 2 if dependencies/blockers missing
    5. Node 5: Synthesizes final answer with grounded citations
    """
    if not req.question or not req.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question string cannot be empty."
        )

    try:
        result = run_agent_workflow(
            query=req.question.strip(),
            user_id=req.user_id or "default_user",
            thread_id=req.thread_id or "session_001"
        )

        return QueryResponse(
            status="success",
            user_query=result.get("user_query", req.question),
            user_id=result.get("user_id", req.user_id),
            thread_id=result.get("thread_id", req.thread_id),
            recalled_memories=result.get("recalled_memories", []),
            durable_facts_saved=result.get("durable_facts_saved", []),
            sub_questions=result.get("sub_questions", []),
            tools_called=result.get("tools_called", []),
            evidence=result.get("evidence", []),
            citations=result.get("citations", []),
            final_answer=result.get("final_answer", ""),
            current_hop=result.get("current_hop", 1)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent workflow execution error: {str(e)}"
        )


@app.get("/api/memories/{user_id}")
def get_user_memories(user_id: str):
    """Fetches durable long-term memories persisted in Neon DB for a specific user."""
    try:
        memories = get_all_user_memories(user_id=user_id)
        return {
            "status": "success",
            "user_id": user_id,
            "total_memories": len(memories),
            "memories": memories
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error recalling memories: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.app:app", host="127.0.0.1", port=8000, reload=True)
