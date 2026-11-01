import os
import sys
from pathlib import Path
import requests
from dotenv import load_dotenv

# Ensure .env is loaded from project root
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

api_key = os.getenv("NOTION_API_KEY")
page_id = os.getenv("NOTION_PAGE_ID")

if not api_key:
    print("[ERROR] NOTION_API_KEY missing in .env file.")
    print("Please set NOTION_API_KEY=ntn_xxxx in your .env file.")
    sys.exit(1)

if not page_id:
    print("[ERROR] NOTION_PAGE_ID missing in .env file.")
    sys.exit(1)

headers = {
    "Authorization": f"Bearer {api_key}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

print("[1/2] Connecting to Notion API...")
url = f"https://api.notion.com/v1/blocks/{page_id}/children"

try:
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        results = data.get("results", [])
        print(f"      SUCCESS: Connected to Notion! Retrieved {len(results)} content blocks from page.")
        
        print("\n[2/2] Sample Content from Page:")
        for block in results[:5]:
            btype = block.get("type")
            text_objs = block.get(btype, {}).get("rich_text", [])
            plain_text = "".join([t.get("plain_text", "") for t in text_objs])
            if plain_text:
                print(f"      - [{btype}] {plain_text[:80]}")
                
        print("\n All good! Notion live workspace is 100% connected to PulseOps AI!")
    elif response.status_code == 404:
        print("[ERROR 404] Page not found or integration not connected.")
    elif response.status_code == 401:
        print("[ERROR 401] Invalid NOTION_API_KEY.")
    else:
        print(f"[ERROR {response.status_code}] {response.text}")
except Exception as e:
    print(f"[ERROR] Request failed: {e}")
