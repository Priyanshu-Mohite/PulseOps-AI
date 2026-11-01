"""
Test script to verify the Custom Jira MCP tools:
1. get_jira_issues
2. create_or_update_jira_issue
"""
import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.mcp_servers.jira_server import get_jira_issues, create_or_update_jira_issue

print("=" * 70)
print("[1/3] Testing 'get_jira_issues' tool (Fetching current tickets in KAN)...")
issues_res = get_jira_issues()
print(issues_res)

print("\n" + "=" * 70)
print("[2/3] Testing 'create_or_update_jira_issue' (Creating new Task autonomously)...")
new_ticket = create_or_update_jira_issue(
    summary="[PulseOps AI] Kafka Ingestion Pipeline Setup",
    description="Milestone 1 from Notion roadmap. Set up Apache Kafka cluster with topic transactions.raw and 12 partitions.",
    issue_type="Task"
)
print(new_ticket)

print("\n" + "=" * 70)
print("[3/3] Testing 'create_or_update_jira_issue' (Updating status to 'In Progress')...")
# Extract key if created or use test issue
if "SUCCESS: Created new Jira issue [" in new_ticket:
    created_key = new_ticket.split("[")[1].split("]")[0]
    update_res = create_or_update_jira_issue(
        issue_key=created_key,
        status="In Progress",
        description="Updated by PulseOps AI Agent: Pipeline setup in progress."
    )
    print(update_res)
else:
    print("Could not parse created key, skipping transition test.")

print("\n" + "=" * 70)
print("[Verification] Fetching tickets with status='In Progress'...")
filtered_res = get_jira_issues(status="In Progress")
print(filtered_res)
