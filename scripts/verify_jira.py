import os
import sys
from pathlib import Path
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

# Ensure .env is loaded from project root
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

jira_url = os.getenv("JIRA_INSTANCE_URL", "").rstrip("/")
user_email = os.getenv("JIRA_USER_EMAIL")
api_token = os.getenv("JIRA_API_TOKEN")
project_key = os.getenv("JIRA_PROJECT_KEY", "KAN")

if not jira_url or not user_email or not api_token:
    print("[ERROR] Missing Jira credentials in .env file.")
    sys.exit(1)

auth = HTTPBasicAuth(user_email, api_token)
headers = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

print(f"[1/2] Connecting to Jira Cloud: {jira_url} ...")
url = f"{jira_url}/rest/api/3/search/jql"
params = {
    "jql": f"project = {project_key} ORDER BY created DESC",
    "fields": "summary,status,created,updated"
}

try:
    response = requests.get(url, headers=headers, auth=auth, params=params)
    if response.status_code == 200:
        data = response.json()
        issues = data.get("issues", [])
        print(f"      SUCCESS: Connected to Jira! Found {len(issues)} ticket(s) in project [{project_key}].\n")
        
        print("[2/2] Live Tickets fetched:")
        for issue in issues:
            key = issue.get("key")
            fields = issue.get("fields", {})
            summary = fields.get("summary")
            status = fields.get("status", {}).get("name")
            print(f"      - [{key}] ({status}) : {summary}")
            
        print("\n All good! Jira Cloud live workspace is 100% connected to PulseOps AI!")
    elif response.status_code == 401:
        print("[ERROR 401] Authentication failed. Check JIRA_USER_EMAIL and JIRA_API_TOKEN.")
    else:
        print(f"[ERROR {response.status_code}] {response.text}")
except Exception as e:
    print(f"[ERROR] Request failed: {e}")
