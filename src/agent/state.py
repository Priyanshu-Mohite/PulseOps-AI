"""
PulseOps AI - Agent State Definition (Phase 4)
Defines the unified state schema that flows across all 5 LangGraph nodes.
"""

from typing import TypedDict, List, Dict, Any, Optional, Annotated
import operator


class AgentState(TypedDict):
    """
    State object flowing through the LangGraph Multi-Hop Cyclic Graph.
    """
    # Session & User metadata
    user_id: str
    thread_id: str
    user_query: str

    # Layer 1 & 2 Memory data
    recalled_memories: List[Dict[str, Any]]
    durable_facts_saved: List[Dict[str, Any]]

    # Planner (Node 2)
    sub_questions: List[str]

    # Cyclic Execution tracking (Node 3 & 4)
    current_hop: int
    max_hops: int
    evidence: Annotated[List[Dict[str, Any]], operator.add]
    missing_information: List[str]

    # Synthesizer Output (Node 5)
    citations: List[Dict[str, str]]
    final_answer: str
