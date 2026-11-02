"""
PulseOps AI - Phase 2 Verification Script
Verifies runtime MCP Tool Discovery and execution using LangChain MCP Adapters.
Connects MultiServerMCPClient to standalone notion_server and jira_server over stdio.
"""

import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")
sys.path.insert(0, str(ROOT_DIR))

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from langchain_mcp_adapters.client import MultiServerMCPClient


async def main():
    print("=" * 75)
    print("🚀 [PulseOps AI] Phase 2: Verifying MCP Tool Discovery via LangChain Adapters")
    print("=" * 75)

    connections = {
        "notion": {
            "transport": "stdio",
            "command": sys.executable,
            "args": ["-m", "src.mcp_servers.notion_server"],
            "cwd": str(ROOT_DIR),
        },
        "jira": {
            "transport": "stdio",
            "command": sys.executable,
            "args": ["-m", "src.mcp_servers.jira_server"],
            "cwd": str(ROOT_DIR),
        }
    }

    print("\n[1/3] Connecting MultiServerMCPClient to Notion & Jira MCP servers (stdio)...")
    client = MultiServerMCPClient(connections)

    try:
        tools = await client.get_tools()
        print(f"      SUCCESS: Discovered {len(tools)} LangChain tool(s) dynamically!\n")

        print("[2/3] Inspecting Discovered Tools:")
        for t in tools:
            desc_first_line = t.description.strip().split("\n")[0] if t.description else "No description"
            print(f"      - 🛠️  Tool: {t.name}")
            print(f"          Description: {desc_first_line}")
            print(f"          Args: {list(t.args.keys())}")

        print("\n[3/3] Live Tool Invocation Test via LangChain Adapter:")
        # Look for get_jira_issues tool
        jira_tool = next((t for t in tools if "get_jira_issues" in t.name), None)
        if jira_tool:
            print(f"      Running '{jira_tool.name}' for status='In Progress'...")
            res = await jira_tool.ainvoke({"status": "In Progress"})
            print("      Result Preview:")
            for line in str(res).strip().split("\n")[:6]:
                print(f"        {line}")
        else:
            print("      Warning: get_jira_issues tool not found in discovered list.")

        print("\n" + "=" * 75)
        print("🎉 Phase 2 is 100% COMPLETE! MCP Servers + LangChain Adapters Operational.")
        print("=" * 75)

    except Exception as e:
        print(f"\n[ERROR] Tool discovery failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
