"""
Jira MCP Server (Model Context Protocol)
Exposes standalone tools for AI agents to query Jira issues/blockers
and autonomously create or update Jira issues.
"""

import requests
from requests.auth import HTTPBasicAuth
from mcp.server.mcpserver import MCPServer
from src.config import config

# Initialize Standalone MCP Server
mcp = MCPServer("pulseops-jira-server")

JIRA_AUTH = HTTPBasicAuth(config.JIRA_USER_EMAIL, config.JIRA_API_TOKEN)
JIRA_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}


# ============================================================================
# Helper Functions: ADF Conversion & Status Transitions
# ============================================================================

def _text_to_adf(text: str) -> dict:
    """
    Convert raw text/markdown into Jira Cloud's Atlassian Document Format (ADF).
    Jira Cloud v3 REST API requires description in ADF structure.
    """
    if not text:
        return {
            "type": "doc",
            "version": 1,
            "content": []
        }

    paragraphs = []
    for line in text.split("\n"):
        line_clean = line.strip()
        if not line_clean:
            continue
        paragraphs.append({
            "type": "paragraph",
            "content": [
                {
                    "type": "text",
                    "text": line_clean
                }
            ]
        })

    if not paragraphs:
        paragraphs = [{
            "type": "paragraph",
            "content": [{"type": "text", "text": text}]
        }]

    return {
        "type": "doc",
        "version": 1,
        "content": paragraphs
    }


def _transition_issue_status(issue_key: str, target_status: str) -> tuple[bool, str]:
    """
    Find matching workflow transition ID for a given status name and transition the issue.
    """
    jira_url = config.JIRA_INSTANCE_URL
    url = f"{jira_url}/rest/api/3/issue/{issue_key}/transitions"

    try:
        res = requests.get(url, auth=JIRA_AUTH, headers=JIRA_HEADERS, timeout=10)
        if res.status_code != 200:
            return False, f"Could not fetch transitions for {issue_key}: {res.text}"

        transitions = res.json().get("transitions", [])
        matched_transition_id = None
        available_status_names = []

        target_clean = target_status.strip().lower()
        for t in transitions:
            t_name = t.get("name", "")
            to_name = t.get("to", {}).get("name", "")
            available_status_names.append(to_name or t_name)
            if target_clean in [t_name.lower(), to_name.lower()]:
                matched_transition_id = t.get("id")
                break

        if not matched_transition_id:
            return False, f"Status '{target_status}' is not a valid transition. Available transitions: {available_status_names}"

        post_payload = {"transition": {"id": matched_transition_id}}
        trans_res = requests.post(url, auth=JIRA_AUTH, headers=JIRA_HEADERS, json=post_payload, timeout=10)
        if trans_res.status_code in [204, 200]:
            return True, f"Successfully transitioned {issue_key} to '{target_status}'."
        else:
            return False, f"Transition failed ({trans_res.status_code}): {trans_res.text}"
    except Exception as e:
        return False, f"Exception during transition: {str(e)}"


# ============================================================================
# Standalone MCP Tools
# ============================================================================

@mcp.tool()
def get_jira_issues(status: str = "", priority: str = "", assignee: str = "", jql_query: str = "") -> str:
    """
    Query Jira Cloud issues using filters or custom JQL.
    Fetches open bugs, blockers, overdue tasks, or sprint issues in the project.

    Args:
        status: Filter by status name (e.g., 'To Do', 'In Progress', 'Done', 'Blocked').
        priority: Filter by priority (e.g., 'High', 'Highest', 'Medium', 'Low').
        assignee: Filter by assignee email or username (e.g., 'currentUser()' or specific user).
        jql_query: Optional raw JQL override. If empty, auto-constructs query from parameters.
    """
    if not config.JIRA_INSTANCE_URL or not config.JIRA_API_TOKEN or not config.JIRA_USER_EMAIL:
        return "Error: Jira credentials (JIRA_INSTANCE_URL, JIRA_USER_EMAIL, JIRA_API_TOKEN) are missing in .env."

    jira_url = config.JIRA_INSTANCE_URL
    project_key = config.JIRA_PROJECT_KEY or "KAN"

    # Build JQL query
    if jql_query.strip():
        final_jql = jql_query.strip()
    else:
        conditions = [f"project = {project_key}"]
        if status.strip():
            conditions.append(f'status = "{status.strip()}"')
        if priority.strip():
            conditions.append(f'priority = "{priority.strip()}"')
        if assignee.strip():
            if assignee.strip().lower() in ["currentuser()", "currentuser"]:
                conditions.append("assignee = currentUser()")
            else:
                conditions.append(f'assignee = "{assignee.strip()}"')

        conditions.append("ORDER BY created DESC")
        final_jql = " AND ".join(conditions[:-1]) + " " + conditions[-1]

    url = f"{jira_url}/rest/api/3/search/jql"
    params = {
        "jql": final_jql,
        "fields": "summary,status,priority,assignee,created,updated,description",
        "maxResults": 20
    }

    try:
        response = requests.get(url, auth=JIRA_AUTH, headers=JIRA_HEADERS, params=params, timeout=12)
        if response.status_code != 200:
            return f"Error from Jira API ({response.status_code}): {response.text}"

        data = response.json()
        issues = data.get("issues", [])

        if not issues:
            return f"No Jira issues found matching JQL: `{final_jql}` in project [{project_key}]."

        output = [f"### Found {len(issues)} Jira Issue(s) for query: `{final_jql}`\n"]
        for issue in issues:
            key = issue.get("key")
            fields = issue.get("fields", {})
            summary = fields.get("summary", "No summary")
            status_name = fields.get("status", {}).get("name", "Unknown")
            priority_name = fields.get("priority", {}).get("name", "None") if fields.get("priority") else "None"

            assignee_obj = fields.get("assignee")
            assignee_name = assignee_obj.get("displayName", "Unassigned") if assignee_obj else "Unassigned"

            created = fields.get("created", "")[:10]
            updated = fields.get("updated", "")[:10]

            output.append(
                f"- **[{key}] {summary}**\n"
                f"  - **Status**: {status_name} | **Priority**: {priority_name} | **Assignee**: {assignee_name}\n"
                f"  - **Created**: {created} | **Updated**: {updated}\n"
            )

        return "\n".join(output)
    except Exception as e:
        return f"Exception querying Jira issues: {str(e)}"


@mcp.tool()
def create_or_update_jira_issue(
    summary: str = "",
    description: str = "",
    status: str = "",
    issue_key: str = "",
    issue_type: str = "Task"
) -> str:
    """
    Create a new Jira Bug/Task/Story, OR update an existing ticket (change status or description).
    Provides bidirectional Agentic Action for autonomous workflows.

    Args:
        summary: Title/Summary for new issue (Required if creating new issue).
        description: Description text (converted to ADF automatically).
        status: Target status to move issue into (e.g. 'In Progress', 'Done', 'To Do').
        issue_key: If provided (e.g. 'KAN-2'), updates existing issue. If empty, creates a new issue.
        issue_type: Type of issue ('Task', 'Bug', 'Story', 'Epic'). Defaults to 'Task'.
    """
    if not config.JIRA_INSTANCE_URL or not config.JIRA_API_TOKEN or not config.JIRA_USER_EMAIL:
        return "Error: Jira credentials are missing in .env."

    jira_url = config.JIRA_INSTANCE_URL
    project_key = config.JIRA_PROJECT_KEY or "KAN"

    try:
        # Case 1: Update Existing Issue
        if issue_key.strip():
            key = issue_key.strip().upper()
            update_messages = []

            # 1. Update fields (description/summary) if provided
            fields_to_update = {}
            if summary.strip():
                fields_to_update["summary"] = summary.strip()
            if description.strip():
                fields_to_update["description"] = _text_to_adf(description.strip())

            if fields_to_update:
                update_url = f"{jira_url}/rest/api/3/issue/{key}"
                put_res = requests.put(
                    update_url,
                    auth=JIRA_AUTH,
                    headers=JIRA_HEADERS,
                    json={"fields": fields_to_update},
                    timeout=10
                )
                if put_res.status_code in [204, 200]:
                    update_messages.append(f"Updated fields for {key}.")
                else:
                    return f"Error updating fields on {key} ({put_res.status_code}): {put_res.text}"

            # 2. Transition status if provided
            if status.strip():
                ok, msg = _transition_issue_status(key, status.strip())
                update_messages.append(msg)
                if not ok:
                    return f"Status transition issue: {msg}"

            if not update_messages:
                return f"No changes provided for existing issue {key}."

            return f"SUCCESS: {key} updated!\n- " + "\n- ".join(update_messages)

        # Case 2: Create a Brand New Issue
        else:
            if not summary.strip():
                return "Error: 'summary' is required to create a new Jira issue."

            create_url = f"{jira_url}/rest/api/3/issue"
            payload = {
                "fields": {
                    "project": {"key": project_key},
                    "summary": summary.strip(),
                    "description": _text_to_adf(description.strip()),
                    "issuetype": {"name": issue_type.capitalize()}
                }
            }

            res = requests.post(create_url, auth=JIRA_AUTH, headers=JIRA_HEADERS, json=payload, timeout=12)
            if res.status_code in [201, 200]:
                data = res.json()
                new_key = data.get("key")
                issue_id = data.get("id")
                new_url = f"{jira_url}/browse/{new_key}"

                status_msg = ""
                # If target status is provided and different from default (e.g. 'In Progress')
                if status.strip() and status.strip().lower() != "to do":
                    ok, msg = _transition_issue_status(new_key, status.strip())
                    status_msg = f"\n- Status transition: {msg}"

                return (
                    f"SUCCESS: Created new Jira issue [{new_key}] ({issue_type}) in project [{project_key}]!\n"
                    f"- **Issue Key**: {new_key}\n"
                    f"- **Issue ID**: {issue_id}\n"
                    f"- **Link**: {new_url}"
                    f"{status_msg}"
                )
            else:
                return f"Error creating Jira issue ({res.status_code}): {res.text}"

    except Exception as e:
        return f"Exception in create_or_update_jira_issue: {str(e)}"


# ============================================================================
# Server Runner
# ============================================================================
if __name__ == "__main__":
    # Runs the standalone Jira MCP Server via standard I/O (JSON-RPC)
    mcp.run()
