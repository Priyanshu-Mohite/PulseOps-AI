"""
Test script to verify the Custom Notion MCP tools:
1. read_full_notion_page
2. create_or_append_notion_page
"""
import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.mcp_servers.notion_server import read_full_notion_page, create_or_append_notion_page

print("[1/2] Testing 'read_full_notion_page' tool on live Notion...")
read_result = read_full_notion_page()
print(read_result)

print("\n" + "="*70 + "\n")

print("[2/2] Testing 'create_or_append_notion_page' (Agentic Action)...")
test_title = "PulseOps AI - Agentic Action Test"
test_content = """# Autonomous Risk & Health Report
Generated autonomously by PulseOps AI Agent.

## Executive Summary
- System Status: Operational
- RAG Vector Sync: Active
- Connected Integrations: Notion, Jira, Neon DB

### Action Items
- [x] Verify Custom Notion MCP Server
- [ ] Connect Jira MCP Server
- [ ] Deploy LangGraph Autonomous Reasoning Loop

> 🚀 PulseOps AI is ready for autonomous execution!
"""

write_result = create_or_append_notion_page(title=test_title, content=test_content)
print(write_result)
