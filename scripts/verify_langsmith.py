"""
PulseOps AI - Phase 5 Verification Script
Verifies LangSmith Observability connection and fetches live traces.
"""

import sys
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

import os
from langsmith import Client


def main():
    print("=" * 80)
    print("🚀 [PulseOps AI] Phase 5: Verifying LangSmith Full Observability")
    print("=" * 80)

    project_name = os.getenv("LANGCHAIN_PROJECT", "pulseops-ai")
    api_key = os.getenv("LANGCHAIN_API_KEY", "")

    if not api_key:
        print("[ERROR] LANGCHAIN_API_KEY is not set.")
        return

    client = Client()
    print(f"\n[1/2] Connecting to LangSmith Project: '{project_name}'...")
    try:
        runs = list(client.list_runs(project_name=project_name, limit=5))
        print(f"      SUCCESS: Connected! Found {len(runs)} live trace(s) in LangSmith dashboard.\n")

        print("[2/2] Inspecting Live Trace Telemetry (X-Ray Vision):")
        for idx, r in enumerate(runs, 1):
            lat = f"{r.latency:.2f}s" if r.latency is not None else "N/A"
            tok = r.total_tokens if r.total_tokens is not None else "N/A"
            print(f"      {idx}. Run Name: {r.name}")
            print(f"         Run ID  : {r.id}")
            print(f"         Status  : {r.status}")
            print(f"         Latency : {lat} | Total Tokens: {tok}")
            if r.url:
                print(f"         Trace URL: {r.url}")

        print("\n" + "=" * 80)
        print("🎉 Phase 5 is 100% COMPLETE! LangSmith Tracing & Observability Verified.")
        print(f"👉 View live traces at: https://smith.langchain.com/ (Project: {project_name})")
        print("=" * 80)

    except Exception as e:
        print(f"[ERROR] Failed to fetch LangSmith runs: {e}")


if __name__ == "__main__":
    main()
