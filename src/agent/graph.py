"""
PulseOps AI - LangGraph Multi-Hop Cyclic Agent Workflow (Phase 4)
Assembles the 5-node cyclic graph:
[START] -> [Memory] -> [Planner] -> [Investigator] -> [Grader]
                                          ^               |
                                          |-- (Hop Loop) -| (if missing info)
                                                          |
                                                          v
                                                   [Synthesizer] -> [END]
Compiled with LangGraph PostgreSQL Checkpointer for turn-by-turn state persistence.
"""

from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, START, END

from src.config import config
from src.agent.state import AgentState
from src.database.memory import get_short_term_checkpointer
from src.agent.nodes import (
    memory_node,
    planner_node,
    investigator_node,
    grader_node,
    should_continue,
    synthesizer_node
)


def build_agent_graph():
    """
    Constructs the uncompiled LangGraph StateGraph with all 5 nodes and cyclic edges.
    """
    workflow = StateGraph(AgentState)

    # 1. Add all 5 Nodes
    workflow.add_node("memory", memory_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("investigator", investigator_node)
    workflow.add_node("grader", grader_node)
    workflow.add_node("synthesizer", synthesizer_node)

    # 2. Add Fixed Edges
    workflow.add_edge(START, "memory")
    workflow.add_edge("memory", "planner")
    workflow.add_edge("planner", "investigator")
    workflow.add_edge("investigator", "grader")

    # 3. Add Conditional Edge for Self-Correction (Multi-Hop Loop)
    workflow.add_conditional_edges(
        "grader",
        should_continue,
        {
            "investigate": "investigator",   # Loop back for Hop 2
            "synthesize": "synthesizer"      # Proceed to final answer
        }
    )

    # 4. Final Edge
    workflow.add_edge("synthesizer", END)

    return workflow


def get_compiled_agent(checkpointer=None):
    """
    Returns the compiled LangGraph workflow.
    Optionally attaches the LangGraph Postgres checkpointer.
    """
    workflow = build_agent_graph()
    if checkpointer:
        return workflow.compile(checkpointer=checkpointer)
    return workflow.compile()


def run_agent_workflow(
    query: str,
    user_id: str = "default_user",
    thread_id: str = "session_001"
) -> Dict[str, Any]:
    """
    Executes the multi-hop agent workflow end-to-end.
    Persists thread state in Neon PostgreSQL using PostgresSaver.
    """
    initial_state: AgentState = {
        "user_id": user_id,
        "thread_id": thread_id,
        "user_query": query,
        "recalled_memories": [],
        "durable_facts_saved": [],
        "sub_questions": [],
        "current_hop": 1,
        "max_hops": 3,
        "evidence": [],
        "missing_information": [],
        "citations": [],
        "final_answer": ""
    }

    config_dict = {"configurable": {"thread_id": thread_id}}

    try:
        with get_short_term_checkpointer() as checkpointer:
            checkpointer.setup()
            app = get_compiled_agent(checkpointer=checkpointer)
            final_output = app.invoke(initial_state, config=config_dict)
            return final_output
    except Exception as e:
        print(f"[WARN] Running without persistent checkpointer: {e}")
        app = get_compiled_agent()
        return app.invoke(initial_state)
