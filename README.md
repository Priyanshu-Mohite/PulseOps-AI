# PulseOps AI ⚡
> **Autonomous Enterprise Agentic RAG System**  
> Bridges strategic documentation in Notion with live execution status & blockers in Jira Cloud, powered by Model Context Protocol (MCP), PostgreSQL with pgvector, and LangGraph.

---

## 📁 Project Structure

```text
PulseOps AI/
├── .env                       # Local secrets & API keys (Git ignored)
├── .env.example               # Template for environment configuration
├── .gitignore                 # Standard git ignore rules
├── requirements.txt           # Project dependencies
├── README.md                  # Project overview & documentation
│
├── scripts/                   # Verification & utility scripts
│   ├── verify_db.py           # Test Neon PostgreSQL & pgvector extension
│   ├── verify_notion.py       # Test Notion REST API & read live blocks
│   └── verify_jira.py         # Test Jira Cloud REST API & list tickets
│
└── src/                       # Production application source code
    ├── config.py              # Centralized environment settings
    ├── mcp_servers/           # Phase 2: Standalone MCP Servers
    │   ├── notion_server.py   # Notion MCP Server (Tools for pages & search)
    │   └── jira_server.py     # Jira MCP Server (Tools for JQL & blockers)
    ├── database/              # PostgreSQL + pgvector schemas & connections
    └── agent/                 # Phase 3+: LangGraph cyclic agent workflows
```

---

## 🚀 Quick Verification

To verify that your connections to Neon DB, Notion, and Jira are fully healthy:

```bash
# Verify Database & pgvector
python scripts/verify_db.py

# Verify Notion Connection
python scripts/verify_notion.py

# Verify Jira Cloud Connection
python scripts/verify_jira.py
```
