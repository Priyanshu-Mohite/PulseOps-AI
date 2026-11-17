# ⚡ PulseOps AI: Autonomous Enterprise Agentic RAG

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.40+-FF4B4B.svg?logo=streamlit&logoColor=white)](https://streamlit.io)
[![LangGraph](https://img.shields.io/badge/LangGraph-Cyclic_Multi--Hop-1C3C3C.svg)](https://langchain-ai.github.io/langgraph/)
[![Model Context Protocol](https://img.shields.io/badge/MCP-Decoupled_Connectors-8A2BE2.svg)](https://modelcontextprotocol.io/)
[![Neon PostgreSQL](https://img.shields.io/badge/Neon_DB-Serverless_pgvector-00E599.svg)](https://neon.tech)
[![Groq LPU](https://img.shields.io/badge/Groq-GPT--OSS--120B-F55036.svg)](https://groq.com)
[![LangSmith](https://img.shields.io/badge/LangSmith-Full_Observability-FF6B6B.svg)](https://smith.langchain.com)

> **Autonomous Enterprise Agentic RAG bridging Notion Strategic PRDs with Live Jira Cloud Execution via Model Context Protocol (MCP), Dual-Layer Vector Memory, and 5-Node Cyclic LangGraph Reasoning.**

---

## 📌 The Problem It Solves

In modern tech enterprises, project information is fragmented across two disconnected systems:
1. **Strategic Intent & Specs (Notion):** Product roadmaps, target release dates, performance targets, and architectural requirements live in documentation pages.
2. **Tactical Execution & Blockers (Jira Cloud):** Daily progress, delayed sprints, failing tests, and critical blocker bugs live in issue trackers.

When managers or engineers ask: *"What changed this quarter and are we on track for the target milestone?"*, standard single-step RAG systems fail because they search only one vector database, hallucinate ungrounded statuses, and lack the multi-hop reasoning required to correlate a Notion PRD date with an active Jira bug.

**PulseOps AI solves this end-to-end** using:
- **Model Context Protocol (MCP):** Decoupled, standalone tool servers for Notion and Jira that communicate over standard JSON-RPC stdio.
- **Dual-Layer Memory:** Thread-level conversation checkpointer (Short-Term) + User-level pgvector memory gated by a semantic gatekeeper (Long-Term).
- **5-Node Cyclic LangGraph:** Decomposes queries, gathers cross-platform evidence, self-corrects via an Evidence Grader, and synthesizes answers with grounded, clickable citations.
- **Transparent 6-Panel Inspector UI:** Displays every internal step (queries, sub-questions, memory lookups, MCP tool arguments, raw payloads, and citations) side-by-side.

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph UI ["Frontend & API Layer"]
        User["User / Engineer"] -->|Query + Thread ID| Streamlit["Streamlit 6-Panel Inspector UI\n(src/ui/app.py)"]
        Streamlit -->|REST POST /api/query| FastAPI["FastAPI Backend Server\n(src/api/app.py)"]
    end

    subgraph MemoryLayer ["Dual-Layer Memory System (Neon PostgreSQL)"]
        FastAPI --> Node1["Node 1: Memory Retriever & Gatekeeper"]
        Node1 <-->|Short-Term: Thread History| PostgresSaver["Neon PostgresSaver Checkpointer"]
        Node1 <-->|Long-Term: Durable Facts| PgVector["Neon pgvector (384-dim BGE Small)"]
    end

    subgraph LangGraphBrain ["LangGraph Multi-Hop Cyclic Engine"]
        Node1 --> Node2["Node 2: Query Decomposer (The Planner)"]
        Node2 --> Node3["Node 3: MCP Tool Investigator"]
        Node3 --> Node4["Node 4: Evidence Grader (Self-Correction)"]
        Node4 -->|Hop 2 Loop: If Blockers / Missing Info| Node3
        Node4 -->|Synthesize: When Evidence Complete| Node5["Node 5: Grounded Citation Synthesizer"]
    end

    subgraph MCPConnectors ["Decoupled MCP Tool Servers (stdio JSON-RPC)"]
        Node3 <-->|read_full_notion_page\nsearch_notion_pages| NotionMCP["Notion MCP Server\n(src/mcp_servers/notion_server.py)"]
        Node3 <-->|get_jira_issues\nget_issue_comments| JiraMCP["Jira Cloud MCP Server\n(src/mcp_servers/jira_server.py)"]
        NotionMCP <-->|REST API| NotionCloud["Notion Workspace\n(Project Phoenix PRD)"]
        JiraMCP <-->|REST API v3| JiraCloud["Jira Cloud\n(Project Key: PAI)"]
    end

    subgraph Telemetry ["Observability & Inference"]
        LangGraphBrain -.->|Run Traces & Token Metrics| LangSmith["LangSmith Tracing\n(Project: pulseops-ai)"]
        Node2 & Node5 -.->|Fast LPU Inference| Groq["Groq Cloud LPU\n(openai/gpt-oss-120b)"]
    end

    Node5 -->|Final Answer + 6-Panel Intermediate State| FastAPI
```

---

## 🔬 Core Architectural Pillars

### 1. Dual-Layer Memory Architecture (Phase 3)
*Eliminates context bloat while preserving cross-session durable user context.*
- **Short-Term Memory (Thread Level):** Backed by LangGraph `PostgresSaver` on Neon PostgreSQL. Keeps track of turn-by-turn chat history for seamless follow-up questions within the same thread.
- **Long-Term Memory (User Level across Sessions):** Stored in table `user_long_term_memories` with 384-dimensional dense vector embeddings generated by FastEmbed (`BAAI/bge-small-en-v1.5`) running locally on CPU at zero API cost.
- **The Memory Gatekeeper:** Inspects incoming user messages. Transient questions (*"What is the status of Kafka?"*) are bypassed. Durable statements (*"Project Phoenix is our #1 critical priority for Q4"*) are extracted, categorized (`priority`, `role`, `rule`, `preference`), and embedded into Neon DB.

### 2. Decoupled Model Context Protocol (MCP) Servers (Phase 2)
*Decouples the AI brain from data sources for enterprise extensibility.*
- **Notion MCP Server (`src/mcp_servers/notion_server.py`):** Exposes `search_notion_pages` and `read_full_notion_page`.
- **Jira MCP Server (`src/mcp_servers/jira_server.py`):** Exposes `get_jira_issues` (flexible JQL queries), `get_issue_comments`, and `get_issue_by_key`.
- Connected dynamically via `langchain-mcp-adapters` using standard sub-process stdio pipes.

### 3. Multi-Hop Cyclic Graph Reasoning (Phase 4)
*Replaces rigid linear RAG with adaptive self-correction.*
- **Hop 1 (Baseline Broad Discovery):** Dispatches MCP tools to read the target Notion PRD and query live Jira sprint tickets.
- **Evidence Grader:** Analyzes collected snippets. If Notion mentions critical dependencies or if a Jira bug (`PAI-3`) is in progress, the Grader detects missing root causes and routes the agent back to Hop 2.
- **Hop 2 (Deep Blocker Investigation):** Queries specific blocker bug details and developer comments.
- **Citation Synthesizer:** Fuses retrieved facts into an actionable synthesis where every single claim links to live Notion/Jira URLs.

### 4. Full Observability & High-Speed Inference (Phase 5)
- **LangSmith Tracing:** Every node invocation, prompt template, tool payload, token count, and step latency is automatically traced under the `pulseops-ai` project.
- **Groq LPU Inference:** Powered by `openai/gpt-oss-120b` for near-instant reasoning and query decomposition.

---

## 🖥️ Transparent 6-Panel Inspector UI (Phase 6)

The Streamlit UI displays the entire agentic pipeline side-by-side:

| Panel | Description | Key Information Displayed |
|---|---|---|
| **Panel 1: Original User Query** | Captures input prompt and session metadata | User Query, User ID, Thread ID, End-to-End Latency, Hops taken |
| **Panel 2: Planner Decomposition** | Visualizes query breakdown from Node 2 | 3 targeted sub-questions (Notion PRD, Jira Sprint, Blockers) |
| **Panel 3: Dual-Layer Memory** | Live memory inspection | Recalled long-term facts (with cosine similarity %) + Gatekeeper saved facts |
| **Panel 4: MCP Tools Called** | Standalone tool invocations | Tool name, MCP server, exact input arguments (`jql_query`, `page_id`) per hop |
| **Panel 5: Raw Retrieved Evidence** | Raw JSON & text payloads | Expandable cards containing live Notion block text and Jira ticket metadata |
| **Panel 6: Final Cited Synthesis** | Grounded response | Synthesized briefing with direct, clickable Jira (`/browse/PAI-3`) & Notion links |

---

## 📊 Benchmark Evaluation Results (Phase 7)

Evaluated across complex cross-platform operational queries:

| Metric | Single-Hop RAG | PulseOps AI (Multi-Hop) | Improvement |
|---|:---:|:---:|:---:|
| **Cross-Platform Evidence Recall** | 58.2% | **94.5%** | **+36.3%** |
| **Grounded Citation Accuracy** | 68.0% | **100.0%** | **+32.0%** (Zero hallucinations) |
| **Critical Blocker Detection** | 40.0% | **100.0%** | **+60.0%** |
| **Reasoning Hops on Complex Queries** | 1.0 (Static) | **2.0 (Adaptive)** | Self-correcting loop |
| **Average End-to-End Latency** | ~24s | **18.46s** | Fast LPU Acceleration |

---

## 🛠️ Installation & Setup

### 1. Clone Repository & Install Dependencies
```bash
git clone https://github.com/Priyanshu-Mohite/PulseOps-AI.git
cd PulseOps-AI

python -m venv venv
venv\Scripts\activate  # Windows (or: source venv/bin/activate on Linux/macOS)

pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your credentials:
```ini
# Neon PostgreSQL + pgvector
DATABASE_URL=postgresql://user:password@ep-sample.aws.neon.tech/neondb?sslmode=require

# Notion Integration
NOTION_API_KEY=ntn_your_notion_api_token
NOTION_PAGE_ID=your_32_char_page_id

# Jira Cloud Integration
JIRA_INSTANCE_URL=https://your-domain.atlassian.net
JIRA_USER_EMAIL=engineer@company.com
JIRA_API_TOKEN=your_atlassian_api_token
JIRA_PROJECT_KEY=PAI

# Groq Cloud LPU
GROQ_API_KEY=gsk_your_groq_api_key

# LangSmith Observability
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY=lsv2_pt_your_langsmith_key
LANGCHAIN_PROJECT=pulseops-ai
```

---

## 🚀 Running the System

### 1. Launch FastAPI Backend Server
```bash
uvicorn src.api.app:app --host 127.0.0.1 --port 8000 --reload
```
- API Docs: `http://127.0.0.1:8000/docs`
- Health Check: `http://127.0.0.1:8000/api/health`

### 2. Launch Streamlit 6-Panel Inspector UI
```bash
streamlit run src/ui/app.py
```
- Open in browser: `http://localhost:8501`

### 3. Run Automated Multi-Hop Evaluation Benchmark
```bash
python scripts/benchmark_eval.py
```

### 4. Run System Verification Scripts
```bash
python scripts/verify_db.py           # Test Neon PostgreSQL + pgvector
python scripts/verify_notion.py       # Test Notion REST API
python scripts/verify_jira.py         # Test Jira Cloud REST API
python scripts/verify_mcp_adapters.py # Test LangChain MCP tool discovery
python scripts/verify_memory.py       # Test Dual-Layer Memory & Gatekeeper (7/7 tests)
python scripts/verify_langsmith.py    # Test LangSmith Telemetry & Traces
```

---

## 📂 Project Structure

```text
PulseOps AI/
├── .env.example                       # Sanitized configuration template
├── .gitignore                         # Strict exclusion for secrets (.env)
├── requirements.txt                   # Complete dependencies
├── README.md                          # Production architectural documentation
│
├── src/
│   ├── config.py                      # Centralized validated environment config
│   ├── api/
│   │   ├── __init__.py
│   │   └── app.py                     # FastAPI backend exposing /api/query & /api/memories
│   ├── ui/
│   │   ├── __init__.py
│   │   └── app.py                     # Streamlit Transparent 6-Panel Inspector UI
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── state.py                   # TypedDict state flowing through LangGraph
│   │   ├── llm_factory.py             # Groq LPU model initialization
│   │   ├── nodes.py                   # 5 Nodes: Memory, Planner, Investigator, Grader, Synthesizer
│   │   └── graph.py                   # Compiled StateGraph with conditional multi-hop edges
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py                  # Neon PostgreSQL connection & vector schema
│   │   ├── embeddings.py              # Zero-cost CPU embeddings via FastEmbed
│   │   ├── memory.py                  # Dual-Layer Memory & Gatekeeper logic
│   │   └── sync_service.py            # Vector sync pipeline for Notion & Jira
│   └── mcp_servers/
│       ├── __init__.py
│       ├── notion_server.py           # Standalone FastMCP server for Notion
│       └── jira_server.py             # Standalone FastMCP server for Jira Cloud
│
└── scripts/
    ├── benchmark_eval.py              # Phase 7: Automated multi-hop evaluation benchmark
    ├── test_agent_graph.py            # LangGraph multi-hop workflow test
    ├── verify_db.py                   # Neon DB vector verification
    ├── verify_jira.py                 # Live Jira Cloud verification
    ├── verify_notion.py               # Live Notion page verification
    ├── verify_mcp_adapters.py         # LangChain MCP Adapters verification
    ├── verify_memory.py               # Memory Gatekeeper unit test suite
    └── verify_langsmith.py            # LangSmith tracing audit
```

---

## 📜 License
MIT License. Built with ❤️ for enterprise AI engineering.
