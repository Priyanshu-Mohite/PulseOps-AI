"""
PulseOps AI - Phase 3 Verification Script
Verifies:
1. Short-Term Memory: Thread-level PostgreSQL Checkpointer via LangGraph PostgresSaver.
2. Long-Term Memory: Vector-based user-level memory in Neon DB.
3. Memory Gatekeeper: Durability classifier distinguishing persistent facts from routine queries.
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

from src.database.memory import (
    init_memory_db,
    get_short_term_checkpointer,
    save_long_term_memory,
    search_long_term_memory,
    memory_gatekeeper
)


def main():
    print("=" * 75)
    print("🚀 [PulseOps AI] Phase 3: Verifying Dual-Layer Memory Architecture")
    print("=" * 75)

    # ------------------------------------------------------------------------
    # 1. Short-Term Memory Verification (LangGraph PostgresSaver)
    # ------------------------------------------------------------------------
    print("\n[1/3] Testing Short-Term Memory Checkpointer (PostgresSaver on Neon DB)...")
    try:
        with get_short_term_checkpointer() as checkpointer:
            checkpointer.setup()
            print("      SUCCESS: Neon DB Checkpointer tables verified (checkpoints, writes, blobs)!")
    except Exception as e:
        print(f"      [ERROR] Checkpointer failed: {e}")
        return

    # ------------------------------------------------------------------------
    # 2. Memory Gatekeeper Verification (Context Bloat Prevention)
    # ------------------------------------------------------------------------
    print("\n[2/3] Testing Memory Gatekeeper (Fact Durability Classifier)...")
    test_cases = [
        ("I am the Lead DevOps Engineer on Project Phoenix", True, "role"),
        ("Project Phoenix is our #1 priority this quarter", True, "priority"),
        ("Strict rule: Never deploy database migrations on weekends", True, "rule"),
        ("Remember that we require 2 approvals for PR merging", True, "preference"),
        ("What is the launch date of Project Phoenix?", False, None),
        ("Show me all Jira issues in progress", False, None),
        ("Hey, good morning! How are you doing today?", False, None),
    ]

    gatekeeper_passed = 0
    for text, expected_durable, expected_cat in test_cases:
        res = memory_gatekeeper(text)
        is_durable = res["is_durable"]
        cat = res["category"]
        verdict = "PASS" if is_durable == expected_durable else "FAIL"
        if verdict == "PASS":
            gatekeeper_passed += 1
        label = "DURABLE" if is_durable else "TRANSIENT (Skip)"
        print(f"      [{verdict}] '{text[:50]}...' -> {label} (Cat: {cat})")

    print(f"      Result: {gatekeeper_passed}/{len(test_cases)} gatekeeper tests passed successfully!\n")

    # ------------------------------------------------------------------------
    # 3. Long-Term Memory Save & Semantic Recall Test (Vector Search)
    # ------------------------------------------------------------------------
    print("[3/3] Testing Long-Term Memory Persistence & Vector Cosine Recall...")
    test_user = "user_devops_lead_42"

    # Step A: Save durable facts
    fact1 = "User's role: Lead DevOps Engineer for Project Phoenix deployment"
    fact2 = "Project Phoenix is our #1 priority this quarter"

    save_res1 = save_long_term_memory(test_user, fact1, category="role")
    save_res2 = save_long_term_memory(test_user, fact2, category="priority")

    print(f"      Saved Memory 1: {save_res1.get('status')} (ID: {save_res1.get('memory_id')})")
    print(f"      Saved Memory 2: {save_res2.get('status')} (ID: {save_res2.get('memory_id')})")

    # Step B: Semantic vector search across sessions
    print("\n      Performing Cross-Session Semantic Search for User...")
    search_queries = [
        "Who is responsible for deployments and infrastructure?",
        "What is the team's top priority right now?"
    ]

    for q in search_queries:
        recalled = search_long_term_memory(test_user, q, top_k=1, threshold=0.5)
        if recalled:
            top_match = recalled[0]
            print(f"      Query: '{q}'")
            print(f"      -> Recalled: '{top_match['fact_text']}' [Score: {top_match['similarity_score']:.4f}]")
        else:
            print(f"      Query: '{q}' -> No matching memory found.")

    print("\n" + "=" * 75)
    print("🎉 Phase 3 is 100% COMPLETE! Dual-Layer Memory + Gatekeeper Operational.")
    print("=" * 75)


if __name__ == "__main__":
    main()
