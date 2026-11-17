"""
PulseOps AI - Phase 4 Verification Script
Executes the complete 5-Node Multi-Hop Cyclic Graph in LangGraph:
[Memory] -> [Planner] -> [Investigator] <-> [Grader] -> [Synthesizer]
Validates cross-system reasoning between Notion PRD and Jira live execution blockers.
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

from src.agent.graph import run_agent_workflow


def main():
    print("=" * 80)
    print("🚀 [PulseOps AI] Phase 4: Verifying Multi-Hop Agent Brain in LangGraph")
    print("=" * 80)

    user_query = "Analyze the release health of Project Phoenix. Are we on track for the Nov 15 launch?"
    test_user_id = "user_devops_lead_42"
    test_thread_id = "eval_thread_phx_001"

    print(f"\n[Test Query]: '{user_query}'")
    print(f"[User ID]   : '{test_user_id}'")
    print(f"[Thread ID] : '{test_thread_id}'")
    print("-" * 80)

    print("\n[Executing 5-Node Cyclic LangGraph Workflow]...")
    result = run_agent_workflow(
        query=user_query,
        user_id=test_user_id,
        thread_id=test_thread_id
    )

    # 1. Inspect Node 1: Memory
    recalled = result.get("recalled_memories", [])
    print(f"\n[Node 1: Memory] Recalled {len(recalled)} durable fact(s):")
    for m in recalled:
        print(f"  - [{m.get('category')}] {m.get('fact_text')}")

    # 2. Inspect Node 2: Planner (Sub-Questions)
    sub_qs = result.get("sub_questions", [])
    print(f"\n[Node 2: Planner] Decomposed into {len(sub_qs)} sub-questions:")
    for idx, sq in enumerate(sub_qs, 1):
        print(f"  {idx}. {sq}")

    # 3. Inspect Node 3 & 4: Evidence & Multi-Hop
    evidence = result.get("evidence", [])
    total_hops = result.get("current_hop", 1) - 1
    print(f"\n[Node 3 & 4: Multi-Hop Investigator] Completed {total_hops} hop(s), gathered {len(evidence)} evidence piece(s):")
    for ev in evidence:
        print(f"  - [Hop {ev.get('hop')}] [{ev.get('source')}] {ev.get('title')}")

    # 4. Inspect Node 5: Citations
    citations = result.get("citations", [])
    print(f"\n[Node 5: Citations] {len(citations)} verified citation link(s):")
    for c in citations:
        print(f"  - {c.get('title')} -> {c.get('url')}")

    # 5. Inspect Final Synthesized Output
    final_answer = result.get("final_answer", "")
    print("\n" + "=" * 80)
    print("📋 [FINAL SYNTHESIZED AGENT ANSWER]")
    print("=" * 80)
    print(final_answer)
    print("=" * 80)

    # Verification assertions
    assert len(sub_qs) >= 2, "Planner failed to decompose query"
    assert len(evidence) >= 2, "Investigator failed to gather cross-system evidence"
    assert "PAI-3" in final_answer or "BUG-03" in final_answer or "blocker" in final_answer.lower(), "Synthesizer missed critical blocker"

    print("\n🎉 Phase 4 is 100% COMPLETE! Multi-Hop Agent Brain successfully verified.")
    print("=" * 80)


if __name__ == "__main__":
    main()
