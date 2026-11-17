"""
PulseOps AI - Streamlit Transparent 6-Panel Inspector UI (Phase 6)
Visually demonstrates the entire agentic pipeline:
1. Original User Question
2. Planner's Generated Sub-Questions (Query Decomposition)
3. Dual-Layer Memory (Recalled Facts & Gatekeeper Output)
4. MCP Tools Called (Hops, Tool Names & Arguments)
5. Raw Evidence Retrieved (Live Notion PRD & Jira Payloads)
6. Final Cited Answer (Clickable Grounded Links)
"""

import os
import sys
import time
import requests
import streamlit as st

# Ensure repository root is on path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.config import config
from src.agent.graph import run_agent_workflow
from src.database.memory import get_all_user_memories

# -----------------------------------------------------------------------------
# 1. Streamlit Page Configuration & Styling
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="PulseOps AI - Enterprise Agentic Inspector",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Enterprise CSS Styling
st.markdown("""
<style>
    /* Global Styles */
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #6366f1, #3b82f6, #06b6d4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        color: #94a3b8;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
    .badge-bar {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        margin-bottom: 20px;
    }
    .tech-badge {
        background-color: #1e293b;
        color: #e2e8f0;
        padding: 5px 12px;
        border-radius: 9999px;
        font-size: 0.82rem;
        font-weight: 600;
        border: 1px solid #334155;
    }
    .tech-badge.green { border-color: #10b981; color: #34d399; }
    .tech-badge.blue { border-color: #3b82f6; color: #60a5fa; }
    .tech-badge.purple { border-color: #8b5cf6; color: #c084fc; }
    .tech-badge.amber { border-color: #f59e0b; color: #fbbf24; }
    .tech-badge.rose { border-color: #f43f5e; color: #fb7185; }

    /* Panel Card Styling */
    .panel-box {
        background-color: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 16px;
    }
    .panel-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #f8fafc;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .card-item {
        background-color: #1e293b;
        border-radius: 8px;
        padding: 10px 14px;
        margin-bottom: 8px;
        border-left: 4px solid #6366f1;
        font-size: 0.92rem;
    }
    .card-item.jira { border-left-color: #3b82f6; }
    .card-item.notion { border-left-color: #10b981; }
    .card-item.blocker { border-left-color: #f43f5e; }
    .card-item.memory { border-left-color: #f59e0b; }
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 2. Sidebar Controls & Metadata
# -----------------------------------------------------------------------------
st.sidebar.markdown("### ⚡ PulseOps AI Controls")

user_id = st.sidebar.text_input("User ID (Long-Term Memory)", value="priyanshu_lead")
thread_id = st.sidebar.text_input("Thread ID (Short-Term Session)", value="session_001")

st.sidebar.markdown("---")
st.sidebar.markdown("#### 🎯 Quick Demo Prompts")

sample_prompts = [
    "Summarize what changed in Project Phoenix this quarter and identify major risks",
    "Project Phoenix is our #1 critical priority for Q4 launch",
    "Who is working on Kafka deployment and what is the blocker with AWS RDS?",
    "What is the engineering spec for PostgreSQL ledger partitioning in Notion?"
]

if "query_text_area" not in st.session_state:
    st.session_state["query_text_area"] = sample_prompts[0]

def set_prompt(text: str):
    st.session_state["query_text_area"] = text

for idx, prompt_text in enumerate(sample_prompts):
    st.sidebar.button(
        f"📌 {prompt_text[:35]}...",
        key=f"sample_{idx}",
        on_click=set_prompt,
        args=(prompt_text,)
    )

st.sidebar.markdown("---")
st.sidebar.markdown("#### 🧠 Neon DB Vector Memory")
if st.sidebar.button("Inspect User Memories"):
    memories = get_all_user_memories(user_id)
    if memories:
        st.sidebar.success(f"Found {len(memories)} persistent memories:")
        for m in memories:
            st.sidebar.info(f"**[{m.get('category', 'fact').upper()}]** {m.get('fact_text')}")
    else:
        st.sidebar.warning("No durable memories found yet for this user.")

st.sidebar.markdown("---")
st.sidebar.markdown("#### ⚙️ Execution Mode")
api_mode = st.sidebar.radio("Route Execution Via:", ["Direct LangGraph Engine", "FastAPI Backend (Port 8000)"], index=0)
api_url = st.sidebar.text_input("FastAPI Base URL", value="http://127.0.0.1:8000")


# -----------------------------------------------------------------------------
# 3. Main Header & Badges
# -----------------------------------------------------------------------------
st.markdown('<div class="main-header">⚡ PulseOps AI: Autonomous Enterprise Agent</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Multi-Hop Agentic RAG bridging Notion Strategic PRDs with Live Jira Execution via MCP & LangGraph</div>', unsafe_allow_html=True)

# Live Connection Status Badges
jira_key = config.JIRA_PROJECT_KEY or "PAI"
st.markdown(f"""
<div class="badge-bar">
    <span class="tech-badge green">🐘 Neon PostgreSQL + pgvector</span>
    <span class="tech-badge blue">🔷 Jira Cloud [{jira_key}]</span>
    <span class="tech-badge purple">📑 Notion Architecture PRD</span>
    <span class="tech-badge amber">⚡ Groq LPU (GPT-OSS-120B)</span>
    <span class="tech-badge rose">🔍 LangSmith Traced (pulseops-ai)</span>
    <span class="tech-badge">🔌 Model Context Protocol (MCP)</span>
</div>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 4. User Input & Workflow Invocation
# -----------------------------------------------------------------------------
query_input = st.text_area(
    "Enter your operational question or instruction:",
    key="query_text_area",
    height=80,
    placeholder="e.g. Summarize what changed in Project Phoenix this quarter and identify major risks"
)

col_run, col_clear = st.columns([1, 5])
run_clicked = col_run.button("🚀 Run Agent", type="primary")

effective_query = st.session_state.get("query_text_area", "").strip()

if run_clicked:
    if not effective_query:
        st.warning("⚠️ Please enter a question or select a demo prompt from the sidebar first!")
    else:
        start_time = time.time()
        
        with st.spinner("🤖 Multi-hop agent reasoning across Notion PRD, Jira Cloud & Vector Memory..."):
            agent_result = None
            error_msg = None
            
            # 1. Try FastAPI Backend if selected
            if "FastAPI" in api_mode:
                try:
                    res = requests.post(
                        f"{api_url}/api/query",
                        json={"question": effective_query, "user_id": user_id, "thread_id": thread_id},
                        timeout=60
                    )
                    if res.status_code == 200:
                        agent_result = res.json()
                    else:
                        st.warning(f"FastAPI returned code {res.status_code}. Falling back to Direct LangGraph Engine.")
                        agent_result = run_agent_workflow(query=effective_query, user_id=user_id, thread_id=thread_id)
                except Exception as e:
                    st.warning(f"Could not connect to FastAPI ({e}). Falling back to Direct LangGraph Engine.")
                    agent_result = run_agent_workflow(query=effective_query, user_id=user_id, thread_id=thread_id)
            else:
                # Direct LangGraph Workflow
                try:
                    agent_result = run_agent_workflow(query=effective_query, user_id=user_id, thread_id=thread_id)
                except Exception as e:
                    error_msg = str(e)

            elapsed = round(time.time() - start_time, 2)

        if error_msg:
            st.error(f"Execution Error: {error_msg}")
        elif agent_result:
            st.session_state["last_result"] = agent_result
            st.session_state["elapsed"] = elapsed
            st.rerun()


# -----------------------------------------------------------------------------
# 5. The 6 Transparent Inspector Panels
# -----------------------------------------------------------------------------
if "last_result" in st.session_state:
    res = st.session_state["last_result"]
    elapsed_time = st.session_state.get("elapsed", 0.0)

    st.success(f"✅ Multi-hop reasoning completed in **{elapsed_time}s** with **{res.get('current_hop', 1)} Hops**!")
    st.markdown("---")
    st.markdown("## 🔍 Transparent 6-Panel Inspector")

    # Row 1: Panels 1, 2, 3
    col1, col2, col3 = st.columns(3)

    # PANEL 1: Original User Question
    with col1:
        st.markdown("""
        <div class="panel-box">
            <div class="panel-title">📌 Panel 1: Original User Query</div>
        </div>
        """, unsafe_allow_html=True)
        st.info(f"**Query:** {res.get('user_query', '')}")
        st.caption(f"👤 **User ID:** `{res.get('user_id', user_id)}` | 🧵 **Thread ID:** `{res.get('thread_id', thread_id)}`")
        st.caption(f"⏱️ **Latency:** {elapsed_time}s | 🔄 **Total Hops:** {res.get('current_hop', 1)}")

    # PANEL 2: Planner Sub-Questions (Query Decomposition)
    with col2:
        st.markdown("""
        <div class="panel-box">
            <div class="panel-title">🧠 Panel 2: Planner's Decomposition</div>
        </div>
        """, unsafe_allow_html=True)
        sub_qs = res.get("sub_questions", [])
        if sub_qs:
            for i, sq in enumerate(sub_qs, 1):
                st.markdown(f"""
                <div class="card-item">
                    <strong>Hop Target {i}:</strong><br/>{sq}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.write("No decomposition generated.")

    # PANEL 3: Dual-Layer Memory
    with col3:
        st.markdown("""
        <div class="panel-box">
            <div class="panel-title">💾 Panel 3: Dual-Layer Memory</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Long-Term Recalled Facts
        recalled = res.get("recalled_memories", [])
        if recalled:
            st.markdown("**Recalled Long-Term Facts (Vector Search):**")
            for m in recalled:
                score = round(m.get("similarity_score", 1.0) * 100, 1)
                st.markdown(f"""
                <div class="card-item memory">
                    <strong>[{m.get('category', 'fact').upper()}]</strong> {m.get('fact_text')}<br/>
                    <small>Similarity: {score}%</small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.caption("ℹ️ No past user facts matched this query.")

        # Gatekeeper Durable Facts Saved
        saved_facts = res.get("durable_facts_saved", [])
        if saved_facts:
            st.markdown("**Gatekeeper Saved Durable Facts:**")
            for sf in saved_facts:
                st.success(f"💾 Stored: {sf.get('fact')} ({sf.get('category')})")
        else:
            st.caption("🛡️ Memory Gatekeeper: Query was transient, no new durable fact saved.")

    # Row 2: Panels 4, 5, 6
    col4, col5, col6 = st.columns(3)

    # PANEL 4: MCP Tools Called
    with col4:
        st.markdown("""
        <div class="panel-box">
            <div class="panel-title">🔌 Panel 4: MCP Tools Called</div>
        </div>
        """, unsafe_allow_html=True)
        tools = res.get("tools_called", [])
        if tools:
            for t in tools:
                server_class = "notion" if "notion" in t.get("mcp_server", "") else "jira"
                st.markdown(f"""
                <div class="card-item {server_class}">
                    <strong>[Hop {t.get('hop')}] {t.get('tool_name')}</strong><br/>
                    <small>Server: <code>{t.get('mcp_server')}</code></small><br/>
                    <code>{t.get('arguments')}</code><br/>
                    <small style="color:#94a3b8;">{t.get('description', '')}</small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.caption("No MCP tool calls recorded.")

    # PANEL 5: Raw Evidence Retrieved
    with col5:
        st.markdown("""
        <div class="panel-box">
            <div class="panel-title">📦 Panel 5: Raw Retrieved Evidence</div>
        </div>
        """, unsafe_allow_html=True)
        evidence_list = res.get("evidence", [])
        if evidence_list:
            for idx, ev in enumerate(evidence_list):
                with st.expander(f"Hop {ev.get('hop', 1)}: {ev.get('source')} - {ev.get('title', '')[:30]}"):
                    st.caption(f"Source URL: {ev.get('url', 'N/A')}")
                    st.code(ev.get("content", "")[:600] + ("..." if len(ev.get("content", "")) > 600 else ""), language="markdown")
        else:
            st.caption("No evidence collected.")

    # PANEL 6: Grounded Citation Synthesizer
    with col6:
        st.markdown("""
        <div class="panel-box">
            <div class="panel-title">✅ Panel 6: Final Cited Synthesis</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(res.get("final_answer", "No answer generated."))
        
        citations = res.get("citations", [])
        if citations:
            st.markdown("---")
            st.markdown("**🔗 Verified Citations:**")
            for c in citations:
                st.markdown(f"- [{c.get('title')}]({c.get('url')})")
