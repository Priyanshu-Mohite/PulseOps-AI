"""
Notion MCP Server (Model Context Protocol)
Exposes custom standalone tools for AI agents to deeply read Notion pages (including nested blocks/tables)
and autonomously create or append new documentation.
"""

import requests
from mcp.server.mcpserver import MCPServer
from src.config import config

# Initialize Standalone MCP Server
mcp = MCPServer("pulseops-notion-server")

NOTION_HEADERS = {
    "Authorization": f"Bearer {config.NOTION_API_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}


# ============================================================================
# Helper Functions: Recursive Reading & Markdown Conversion
# ============================================================================

def _fetch_table_rows(table_block_id: str) -> list[str]:
    """Fetch all rows of a Notion table block and convert to Markdown table format."""
    url = f"https://api.notion.com/v1/blocks/{table_block_id}/children"
    try:
        res = requests.get(url, headers=NOTION_HEADERS, timeout=10)
        if res.status_code != 200:
            return ["[Table content could not be retrieved]"]

        rows = res.json().get("results", [])
        if not rows:
            return []

        table_lines = []
        is_first_row = True
        for row in rows:
            cells = row.get("table_row", {}).get("cells", [])
            cell_texts = ["".join([t.get("plain_text", "") for t in cell]).strip() for cell in cells]
            table_lines.append("| " + " | ".join(cell_texts) + " |")

            if is_first_row:
                # Add Markdown separator line after header row
                table_lines.append("| " + " | ".join(["---"] * max(len(cells), 1)) + " |")
                is_first_row = False

        return table_lines
    except Exception as e:
        return [f"[Error reading table: {e}]"]


def _fetch_block_children(block_id: str, depth: int = 0, max_depth: int = 3) -> list[str]:
    """
    Recursively fetch blocks inside a Notion block or page.
    Handles headings, bullets, checkboxes, toggles, callouts, and tables.
    """
    url = f"https://api.notion.com/v1/blocks/{block_id}/children"
    lines = []
    has_more = True
    start_cursor = None
    indent = "  " * depth

    while has_more:
        params = {"page_size": 100}
        if start_cursor:
            params["start_cursor"] = start_cursor

        response = requests.get(url, headers=NOTION_HEADERS, params=params, timeout=12)
        if response.status_code != 200:
            lines.append(f"{indent}[Error fetching blocks: HTTP {response.status_code}]")
            break

        data = response.json()
        blocks = data.get("results", [])

        for block in blocks:
            b_id = block.get("id")
            b_type = block.get("type")
            has_children = block.get("has_children", False)
            content_data = block.get(b_type, {})

            rich_texts = content_data.get("rich_text", [])
            plain_text = "".join([t.get("plain_text", "") for t in rich_texts]).strip()

            if b_type == "heading_1":
                lines.append(f"\n# {plain_text}")
            elif b_type == "heading_2":
                lines.append(f"\n## {plain_text}")
            elif b_type == "heading_3":
                lines.append(f"\n### {plain_text}")
            elif b_type == "bulleted_list_item":
                lines.append(f"{indent}- {plain_text}")
            elif b_type == "numbered_list_item":
                lines.append(f"{indent}1. {plain_text}")
            elif b_type == "to_do":
                checked = content_data.get("checked", False)
                status_box = "[x]" if checked else "[ ]"
                lines.append(f"{indent}{status_box} {plain_text}")
            elif b_type == "toggle":
                lines.append(f"{indent}▶ {plain_text}")
            elif b_type == "callout":
                emoji = content_data.get("icon", {}).get("emoji", "💡")
                lines.append(f"{indent}> {emoji} {plain_text}")
            elif b_type == "quote":
                lines.append(f"{indent}> {plain_text}")
            elif b_type == "code":
                lang = content_data.get("language", "")
                lines.append(f"{indent}```{lang}\n{plain_text}\n{indent}```")
            elif b_type == "divider":
                lines.append(f"{indent}---")
            elif b_type == "table":
                table_lines = _fetch_table_rows(b_id)
                lines.extend(table_lines)
                has_children = False  # Already processed children
            elif plain_text:
                lines.append(f"{indent}{plain_text}")

            # Recursively fetch nested blocks (e.g. toggles or nested sub-bullets)
            if has_children and depth < max_depth:
                child_lines = _fetch_block_children(b_id, depth=depth + 1, max_depth=max_depth)
                lines.extend(child_lines)

        has_more = data.get("has_more", False)
        start_cursor = data.get("next_cursor")

    return lines


def _markdown_to_blocks(content: str) -> list[dict]:
    """Convert raw Markdown text into Notion API block structures."""
    blocks = []
    lines = content.strip().split("\n")

    for raw_line in lines:
        line = raw_line.rstrip()
        if not line:
            continue

        if line.startswith("# "):
            blocks.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {"rich_text": [{"type": "text", "text": {"content": line[2:].strip()[:2000]}}]}
            })
        elif line.startswith("## "):
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": line[3:].strip()[:2000]}}]}
            })
        elif line.startswith("### "):
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {"rich_text": [{"type": "text", "text": {"content": line[4:].strip()[:2000]}}]}
            })
        elif line.startswith("- ") or line.startswith("* "):
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": line[2:].strip()[:2000]}}]}
            })
        elif len(line) > 3 and line[:2].isdigit() and line[2:4] in [". ", ") "]:
            blocks.append({
                "object": "block",
                "type": "numbered_list_item",
                "numbered_list_item": {"rich_text": [{"type": "text", "text": {"content": line[3:].strip()[:2000]}}]}
            })
        elif line.startswith("[x] ") or line.startswith("[X] "):
            blocks.append({
                "object": "block",
                "type": "to_do",
                "to_do": {
                    "rich_text": [{"type": "text", "text": {"content": line[4:].strip()[:2000]}}],
                    "checked": True
                }
            })
        elif line.startswith("[ ] "):
            blocks.append({
                "object": "block",
                "type": "to_do",
                "to_do": {
                    "rich_text": [{"type": "text", "text": {"content": line[4:].strip()[:2000]}}],
                    "checked": False
                }
            })
        elif line.startswith("> "):
            blocks.append({
                "object": "block",
                "type": "callout",
                "callout": {
                    "rich_text": [{"type": "text", "text": {"content": line[2:].strip()[:2000]}}],
                    "icon": {"emoji": "📌"}
                }
            })
        elif line.strip() == "---":
            blocks.append({
                "object": "block",
                "type": "divider",
                "divider": {}
            })
        else:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": line[:2000]}}]}
            })

    return blocks


# ============================================================================
# Standalone MCP Tools
# ============================================================================

@mcp.tool()
def read_full_notion_page(page_id: str = "") -> str:
    """
    Read all blocks of a Notion page deeply, including nested toggles, sub-bullets, and tables.
    Returns clean, structured Markdown text.

    Args:
        page_id: The Notion Page ID (defaults to configured page if empty).
    """
    target_page_id = page_id.strip() if page_id else config.NOTION_PAGE_ID
    if not target_page_id:
        return "Error: No page_id provided and NOTION_PAGE_ID is not configured in .env."

    if not config.NOTION_API_KEY:
        return "Error: NOTION_API_KEY is missing in .env."

    try:
        content_lines = _fetch_block_children(target_page_id, depth=0, max_depth=3)
        if not content_lines:
            return f"Page (ID: {target_page_id}) has no readable blocks or is empty."

        header = f"=== Notion Page Content (ID: {target_page_id}) ===\n"
        return header + "\n".join(content_lines)
    except Exception as e:
        return f"Exception reading Notion page {target_page_id}: {str(e)}"


@mcp.tool()
def create_or_append_notion_page(title: str, content: str, parent_page_id: str = "") -> str:
    """
    Create a new child page under a parent Notion page, OR append Markdown content to an existing page.
    This provides true Agentic Action capability for the AI Agent.

    Args:
        title: Title of the new page. If left empty, content will be appended to parent_page_id.
        content: Markdown formatted content to write (headings, bullets, checklists, paragraphs).
        parent_page_id: Target Notion Page ID (defaults to configured NOTION_PAGE_ID if empty).
    """
    target_parent_id = parent_page_id.strip() if parent_page_id else config.NOTION_PAGE_ID
    if not target_parent_id:
        return "Error: No target parent page ID provided and NOTION_PAGE_ID is not configured in .env."

    if not config.NOTION_API_KEY:
        return "Error: NOTION_API_KEY is missing in .env."

    blocks = _markdown_to_blocks(content)
    if not blocks:
        return "Error: Content is empty, nothing to write."

    try:
        # Case 1: Create a brand new child page
        if title.strip():
            url = "https://api.notion.com/v1/pages"
            payload = {
                "parent": {"page_id": target_parent_id},
                "properties": {
                    "title": {
                        "title": [{"type": "text", "text": {"content": title.strip()}}]
                    }
                },
                # Notion allows up to 100 children blocks on page creation
                "children": blocks[:100]
            }
            res = requests.post(url, headers=NOTION_HEADERS, json=payload, timeout=15)
            if res.status_code in [200, 201]:
                data = res.json()
                page_id = data.get("id")
                page_url = data.get("url", "")
                return f"SUCCESS: Created new Notion page '{title}'!\n- **Page ID**: {page_id}\n- **URL**: {page_url}"
            else:
                return f"Error creating Notion page ({res.status_code}): {res.text}"

        # Case 2: Append blocks to existing page
        else:
            url = f"https://api.notion.com/v1/blocks/{target_parent_id}/children"
            payload = {"children": blocks[:100]}
            res = requests.patch(url, headers=NOTION_HEADERS, json=payload, timeout=15)
            if res.status_code == 200:
                return f"SUCCESS: Appended {len(blocks[:100])} content blocks to Notion page (ID: {target_parent_id})."
            else:
                return f"Error appending to Notion page ({res.status_code}): {res.text}"

    except Exception as e:
        return f"Exception in create_or_append_notion_page: {str(e)}"


# ============================================================================
# Server Runner
# ============================================================================
if __name__ == "__main__":
    # Runs the standalone MCP Server via standard I/O (JSON-RPC)
    mcp.run()