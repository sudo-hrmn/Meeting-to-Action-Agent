"""
Streamlit frontend — Meeting-to-Action Agent (Executive Dark-Glass UI).

Features:
  - Dynamic Top-Header Backend Liveness Badge & Custom Theme
  - Comprehensive Session-State Persistence (RAG, Automation, History, & Extraction)
  - Seamless Widget Key Binding (Fixes button click drops & widget state collisions)
  - Tab 1: 📤 Upload & Analyse   — AI summary, KPI metrics, grid cards, structured extractions
  - Tab 2: 🔍 Knowledge Base (RAG)— Document ingestion + interactive Q&A with confidence gauge
  - Tab 3: ⚙️ Workflow Tools     — Email draft, CSV export, calendar event generation
  - Tab 4: 📋 Meeting Repository    — Live meeting repository with quick action triggers
"""
import os
import json
import streamlit as st
import httpx

API_BASE = os.getenv("API_BASE", "http://localhost:8000")

st.set_page_config(
    page_title="Meeting-to-Action Agent",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

EXAMPLE_DEFAULT = """Alice (PM): Good morning team. Let's align on our Q3 payment gateway migration and compliance roadmap.

Bob (Lead Architect): The authentication refactor is complete. Payment integration is our primary focus — I will take ownership of the Stripe migration and target completion by September 15th. However, we must hire two backend engineers by late August. Alice, can you publish those job descriptions?

Alice: Yes, I will post the backend listings by tomorrow afternoon. Carol, what is the status of the UX flows?

Carol (Lead Designer): Payment screen mockups are 80% complete; final Figma components will be published by Friday EOD. Key risk: if vendor specs for Stripe are delayed past Tuesday, the September deadline will slip.

Bob: I'll handle vendor follow-up today. Alice, please draft an official escalation notice.

Alice: Will do this afternoon. Decision confirmed: Stripe is selected as our payment vendor. Also, Bob, we require real-time latency dashboards active prior to launch.

Bob: Agreed. Key action items: I'm owning payment migration for Sep 15, Carol finishes designs Friday, Alice posts job ads tomorrow and sends escalation today."""

# ─── Session State Initialization ─────────────────────────────────────────────
if "input_transcript" not in st.session_state:
    st.session_state["input_transcript"] = ""
if "input_title" not in st.session_state:
    st.session_state["input_title"] = ""
if "last_summary_data" not in st.session_state:
    st.session_state["last_summary_data"] = None
if "last_meeting_id" not in st.session_state:
    st.session_state["last_meeting_id"] = ""
if "automation_mid" not in st.session_state:
    st.session_state["automation_mid"] = ""
if "rag_doc_content" not in st.session_state:
    st.session_state["rag_doc_content"] = ""
if "rag_doc_name" not in st.session_state:
    st.session_state["rag_doc_name"] = ""
if "rag_question" not in st.session_state:
    st.session_state["rag_question"] = ""
if "rag_ingest_msg" not in st.session_state:
    st.session_state["rag_ingest_msg"] = None
if "rag_qa_result" not in st.session_state:
    st.session_state["rag_qa_result"] = None
if "active_tool_result" not in st.session_state:
    st.session_state["active_tool_result"] = None

API_KEY = os.getenv("API_KEY", "")

# ─── API Client Helpers ────────────────────────────────────────────────────────
def api_call(method: str, endpoint: str, **kwargs) -> tuple[dict | list | None, int]:
    """Execute HTTP API request against FastAPI backend."""
    try:
        headers = kwargs.pop("headers", {})
        if API_KEY and "X-API-Key" not in headers:
            headers["X-API-Key"] = API_KEY
        with httpx.Client(timeout=120.0) as client:
            fn = getattr(client, method)
            resp = fn(f"{API_BASE}{endpoint}", headers=headers, **kwargs)
            resp.raise_for_status()
            return resp.json(), resp.status_code
    except httpx.ConnectError:
        st.error("❌ Backend Offline — Please start server via `uvicorn app.main:app --reload`")
        return None, 0
    except httpx.HTTPStatusError as e:
        detail = e.response.json().get("detail", {}) if e.response.content else {}
        msg = detail.get("message", str(e)) if isinstance(detail, dict) else str(detail)
        st.error(f"❌ API Error {e.response.status_code}: {msg}")
        return None, e.response.status_code
    except Exception as e:
        st.error(f"❌ System Exception: {e}")
        return None, 0


@st.cache_data(ttl=5)
def check_health() -> bool:
    """Check API server health status with 5s cache to avoid UI lag."""
    try:
        with httpx.Client(timeout=2.0) as c:
            return c.get(f"{API_BASE}/health").status_code == 200
    except Exception:
        return False


# ─── Custom CSS Design System ──────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
    
    /* Root Design Tokens — Pure Obsidian (#000000) & Platinum Sand (#A8A492) Theme */
    :root {
        --bg-main: #000000;
        --card-bg: rgba(20, 19, 17, 0.75);
        --card-border: rgba(168, 164, 146, 0.3);
        --accent-sand: #A8A492;
        --accent-sand-light: #C8C4B2;
        --accent-champagne: #E2DEC8;
        --accent-gold: #d4af37;
        --text-primary: #f8fafc;
        --text-secondary: #a1a1aa;
    }

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    h1, h2, h3, .main-title {
        font-family: 'Outfit', sans-serif !important;
    }

    /* Main App Streamlit Background Overrides */
    .stApp {
        background: radial-gradient(circle at 50% 0%, #1f1e1a 0%, #0a0a09 60%, #000000 100%) !important;
    }

    /* Modern App Header */
    .hero-header {
        background: linear-gradient(135deg, rgba(168, 164, 146, 0.25) 0%, rgba(30, 28, 24, 0.6) 50%, rgba(0, 0, 0, 0.85) 100%);
        border: 1px solid rgba(200, 196, 178, 0.35);
        border-radius: 20px;
        padding: 1.8rem 2.2rem;
        margin-bottom: 1.6rem;
        backdrop-filter: blur(16px);
        box-shadow: 0 12px 40px -10px rgba(168, 164, 146, 0.25);
        position: relative;
        overflow: hidden;
    }
    
    .hero-header::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0; height: 3px;
        background: linear-gradient(90deg, #A8A492 0%, #C8C4B2 33%, #E2DEC8 66%, #ffffff 100%);
    }

    .main-title {
        font-size: 2.35rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        background: linear-gradient(135deg, #ffffff 0%, #E2DEC8 45%, #A8A492 85%, #ffffff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }

    .sub-title {
        color: #d4d4d8;
        font-size: 1.02rem;
        margin-top: 0.4rem;
        font-weight: 400;
        letter-spacing: 0.01em;
    }

    /* Glass Cards */
    .glass-card {
        background: rgba(20, 19, 17, 0.7);
        border: 1px solid rgba(168, 164, 146, 0.25);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1.2rem;
        backdrop-filter: blur(14px);
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.45);
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .glass-card:hover {
        border-color: rgba(226, 222, 200, 0.6);
        box-shadow: 0 12px 35px -5px rgba(168, 164, 146, 0.35);
        transform: translateY(-2px);
    }

    /* Metric Cards */
    .kpi-card {
        background: linear-gradient(145deg, rgba(168, 164, 146, 0.2) 0%, rgba(15, 14, 12, 0.85) 100%);
        border: 1px solid rgba(200, 196, 178, 0.3);
        border-radius: 14px;
        padding: 1.2rem 1.3rem;
        text-align: center;
        backdrop-filter: blur(10px);
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.4);
        transition: transform 0.2s ease;
    }

    .kpi-card:hover {
        transform: translateY(-2px);
        border-color: rgba(226, 222, 200, 0.6);
    }

    .kpi-title {
        color: #a1a1aa;
        font-size: 0.82rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    .kpi-value {
        font-size: 2rem;
        font-weight: 900;
        margin-top: 0.35rem;
        font-family: 'Outfit', sans-serif;
        background: linear-gradient(135deg, #ffffff 0%, #E2DEC8 50%, #A8A492 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    /* Custom Badges */
    .badge {
        display: inline-flex;
        align-items: center;
        padding: 0.3rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 800;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.35);
    }

    .badge-critical { background: rgba(244, 63, 94, 0.2); color: #fb7185; border: 1px solid rgba(244, 63, 94, 0.4); }
    .badge-high { background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); }
    .badge-medium { background: rgba(168, 164, 146, 0.25); color: #E2DEC8; border: 1px solid rgba(200, 196, 178, 0.45); }
    .badge-low { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4); }

    /* Custom Status Pill */
    .status-online {
        display: inline-flex;
        align-items: center;
        gap: 0.55rem;
        padding: 0.45rem 1.05rem;
        background: linear-gradient(135deg, rgba(168, 164, 146, 0.3) 0%, rgba(20, 19, 17, 0.6) 100%);
        border: 1px solid rgba(226, 222, 200, 0.45);
        border-radius: 9999px;
        color: #E2DEC8;
        font-weight: 700;
        font-size: 0.85rem;
        box-shadow: 0 0 16px rgba(168, 164, 146, 0.3);
    }

    .status-offline {
        display: inline-flex;
        align-items: center;
        gap: 0.55rem;
        padding: 0.45rem 1.05rem;
        background: rgba(244, 63, 94, 0.18);
        border: 1px solid rgba(244, 63, 94, 0.45);
        border-radius: 9999px;
        color: #fb7185;
        font-weight: 700;
        font-size: 0.85rem;
    }

    .pulse-dot {
        width: 9px; height: 9px;
        border-radius: 50%;
        background-color: currentColor;
        box-shadow: 0 0 10px currentColor;
    }

    /* Streamlit Tab Styling Overrides */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.6rem;
        background: rgba(15, 14, 12, 0.8);
        padding: 0.4rem;
        border-radius: 14px;
        border: 1px solid rgba(168, 164, 146, 0.25);
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 10px;
        padding: 0.55rem 1.1rem;
        font-weight: 600;
        color: #a1a1aa;
        transition: all 0.2s ease;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, rgba(168, 164, 146, 0.45) 0%, rgba(30, 28, 24, 0.8) 100%) !important;
        color: #E2DEC8 !important;
        border: 1px solid rgba(226, 222, 200, 0.5) !important;
    }

    /* Primary Button Overrides */
    .stButton>button[kind="primary"] {
        background: linear-gradient(135deg, #A8A492 0%, #807c6d 50%, #59564a 100%) !important;
        border: 1px solid rgba(226, 222, 200, 0.5) !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border-radius: 10px !important;
        box-shadow: 0 4px 20px rgba(168, 164, 146, 0.35) !important;
        transition: all 0.25s ease !important;
    }

    .stButton>button[kind="primary"]:hover {
        box-shadow: 0 6px 28px rgba(200, 196, 178, 0.55) !important;
        transform: translateY(-1px) !important;
    }

    /* Section Divider */
    .divider {
        height: 1px;
        background: linear-gradient(90deg, transparent 0%, rgba(200, 196, 178, 0.3) 50%, transparent 100%);
        margin: 1.6rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Check health for top header & sidebar
is_up = check_health()
status_badge_html = (
    '<span class="status-online"><span class="pulse-dot"></span> SYSTEM ONLINE</span>'
    if is_up
    else '<span class="status-offline"><span class="pulse-dot"></span> BACKEND OFFLINE</span>'
)

# ─── Top Navigation Header ─────────────────────────────────────────────────────
st.markdown(f"""
<div class="hero-header">
    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
        <div>
            <h1 class="main-title">⚡ Meeting-to-Action Agent</h1>
            <p class="sub-title">Production-grade AI meeting intelligence · Automated summaries, action items, RAG Q&A, and workflow execution</p>
        </div>
        <div>
            {status_badge_html}
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ─── Sidebar Controls ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ System Status")
    if is_up:
        st.markdown('<div class="status-online"><span class="pulse-dot"></span> Backend API Connected</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-offline"><span class="pulse-dot"></span> Backend API Offline</div>', unsafe_allow_html=True)
        st.code("uvicorn app.main:app --reload", language="bash")

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    st.markdown("### 🔗 Developer Telemetry")
    st.markdown(f"**API Base:** `{API_BASE}`")
    st.markdown(f"[📖 Swagger Docs]({API_BASE}/docs)  \n[❤️ Health Endpoint]({API_BASE}/health)")

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    st.markdown("### 🛠️ Agentic Tech Stack")
    st.markdown("""
    - **LLM Engine:** `groq/compound-mini`
    - **Observability:** LangSmith Tracing
    - **RAG Storage:** ChromaDB Vector Store
    - **Database:** SQLite + Async SQL
    - **Framework:** FastAPI + LangChain
    """)


# ─── Application Tabs ──────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📤 Upload & Analyse",
    "🔍 Knowledge Base (RAG)",
    "⚙️ Workflow Automation",
    "📋 Meeting Repository",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Upload & Analyse
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("### 📝 Submit Meeting Transcript")
    st.caption("Paste any raw meeting transcript or click 'Generate Example' to synthesize a real-time unscripted scenario.")

    col1, col2 = st.columns([3.5, 1.5])
    with col2:
        if st.button("🎲 Generate Synthetic Sample", use_container_width=True, help="Trigger AI agent to generate dynamic transcript"):
            with st.spinner("🧠 Synthesizing unscripted dialogue..."):
                data, status = api_call("post", "/meetings/generate-sample", json={})
                if data and "transcript" in data:
                    st.session_state["input_transcript"] = data.get("transcript", "")
                    st.session_state["input_title"] = data.get("title", "")
                    st.toast("✨ Dynamic sample transcript generated!", icon="🎉")
                    st.rerun()
                else:
                    st.session_state["input_transcript"] = EXAMPLE_DEFAULT
                    st.session_state["input_title"] = "Q3 Architecture & Compliance Sync"
                    st.rerun()

    transcript = st.text_area(
        "Meeting Transcript:",
        key="input_transcript",
        height=260,
        placeholder="Paste transcript here...",
    )
    title = st.text_input("Meeting Title (Optional):", key="input_title", placeholder="e.g., Sprint Planning & Roadmap Sync")

    m_col1, m_col2, m_col3 = st.columns([3, 1, 1])
    with m_col1:
        go = st.button("🚀 Process & Extract Intelligence", type="primary", use_container_width=True, disabled=len(transcript.strip()) < 40)
    m_col2.metric("Total Characters", f"{len(transcript):,}")
    m_col3.metric("Word Count", f"{len(transcript.split()):,}")

    if go:
        with st.spinner("📤 Ingesting meeting transcript..."):
            data, status = api_call("post", "/meetings/upload", json={"transcript": transcript, "title": title or None})

        if data:
            mid = data["id"]
            st.session_state["last_meeting_id"] = mid
            st.session_state["automation_mid"] = mid

            with st.spinner("🧠 Executing Agentic Analysis Pipeline (10–15s)..."):
                result, _ = api_call("post", f"/meetings/{mid}/summarise", json={})

            if result and result.get("summary"):
                st.session_state["last_summary_data"] = result
                st.success(f"✅ Ingested & Analysed Successfully | Session ID: `{mid}`")

    # Render Summary Results (persisted in session state)
    if st.session_state.get("last_summary_data"):
        result = st.session_state["last_summary_data"]
        mid = st.session_state.get("last_meeting_id", "")
        s = result.get("summary") or {}

        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        st.markdown("## 📊 Executive Summary & Intelligence Matrix")

        # Executive Summary Box
        st.markdown(f"""
        <div class="glass-card" style="border-left: 4px solid var(--accent-purple);">
            <h4 style="margin:0 0 0.5rem 0; color:#c084fc;">Executive Summary</h4>
            <p style="margin:0; font-size:1.05rem; line-height:1.6; color:#f1f5f9;">{s.get("summary", "")}</p>
        </div>
        """, unsafe_allow_html=True)

        # Metrics Dashboard
        topics = s.get("key_topics") or []
        decisions = s.get("decisions") or []
        actions = s.get("action_items") or []
        risks = s.get("risks") or []

        k1, k2, k3, k4 = st.columns(4)
        k1.markdown(f'<div class="kpi-card"><div class="kpi-title">Key Topics</div><div class="kpi-value">{len(topics)}</div></div>', unsafe_allow_html=True)
        k2.markdown(f'<div class="kpi-card"><div class="kpi-title">Decisions</div><div class="kpi-value">{len(decisions)}</div></div>', unsafe_allow_html=True)
        k3.markdown(f'<div class="kpi-card"><div class="kpi-title">Action Items</div><div class="kpi-value">{len(actions)}</div></div>', unsafe_allow_html=True)
        k4.markdown(f'<div class="kpi-card"><div class="kpi-title">Identified Risks</div><div class="kpi-value">{len(risks)}</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        r1, r2, r3, r4, r5 = st.tabs(["🎯 Key Topics & Decisions", "📋 Action Items", "📦 Requirements", "⚠️ Risks & Mitigations", "🔍 Raw JSON"])

        with r1:
            c_left, c_right = st.columns(2)
            with c_left:
                st.markdown("#### 📌 Key Discussion Topics")
                for t in topics:
                    st.markdown(f"• **{t}**")
            with c_right:
                st.markdown("#### ⚡ Decisions Finalized")
                for d in decisions:
                    st.markdown(f"• {d}")

            participants = s.get("participants") or []
            if participants:
                st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
                st.markdown("**Active Participants:** " + " · ".join(f"`{p}`" for p in participants))

        with r2:
            if actions:
                for i, item in enumerate(actions, 1):
                    priority = (item.get("priority") or "medium").lower()
                    badge_cls = f"badge-{priority}" if priority in ["critical", "high", "medium", "low"] else "badge-medium"
                    
                    st.markdown(f"""
                    <div class="glass-card">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.6rem;">
                            <span style="font-weight:700; font-size:1.05rem; color:#f8fafc;">#{i} {item.get('task', '')}</span>
                            <span class="badge {badge_cls}">{priority}</span>
                        </div>
                        <div style="display:flex; gap:2rem; font-size:0.9rem; color:#94a3b8;">
                            <div>👤 <strong>Owner:</strong> <span style="color:#e2e8f0;">{item.get('owner', 'Unassigned')}</span></div>
                            <div>📅 <strong>Deadline:</strong> <span style="color:#e2e8f0;">{item.get('deadline', 'TBD')}</span></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No explicit action items identified.")

        with r3:
            reqs = s.get("requirements") or []
            if reqs:
                for r in reqs:
                    st.markdown(f"""
                    <div class="glass-card" style="padding:1rem 1.2rem;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span style="font-weight:600; color:#f8fafc;">{r.get('requirement', '')}</span>
                            <span class="badge badge-medium">{r.get('priority', '')}</span>
                        </div>
                        <div style="font-size:0.85rem; color:#94a3b8; margin-top:0.4rem;">Category: {r.get('category', 'General')}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No requirements extracted.")

        with r4:
            if risks:
                for rk in risks:
                    sev = (rk.get("severity") or "medium").lower()
                    st.markdown(f"""
                    <div class="glass-card" style="border-left: 4px solid var(--accent-rose);">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
                            <span style="font-weight:700; color:#f8fafc; font-size:1rem;">⚠️ {rk.get('risk', '')}</span>
                            <span class="badge badge-critical">Severity: {sev}</span>
                        </div>
                        <div style="font-size:0.92rem; color:#cbd5e1;"><strong>Mitigation Strategy:</strong> {rk.get('mitigation_suggestion', 'N/A')}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No critical risks flagged.")

        with r5:
            st.json(result)
            st.download_button(
                "⬇️ Download Structured Output (JSON)",
                data=json.dumps(result, indent=2),
                file_name=f"meeting_analysis_{mid[:8]}.json",
                mime="application/json",
                use_container_width=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Knowledge Base (RAG)
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### 🔍 Semantic Knowledge Base & RAG Engine")
    st.caption("Ingest enterprise documents or meeting notes into ChromaDB, then query with vector retrieval.")

    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        with st.container(border=True):
            st.markdown("#### 📥 Document Ingestion")
            ingest_method = st.radio("Ingestion Source:", ["Paste Raw Text", "Upload File (TXT, MD, PDF)"], horizontal=True)

            if ingest_method == "Paste Raw Text":
                doc_content = st.text_area("Document Content:", key="rag_doc_content", height=200, placeholder="Paste policy, PRD, or technical specification...")
                doc_name = st.text_input("Document Reference Name:", key="rag_doc_name", placeholder="q3_architecture_spec.txt")

                if st.button("📥 Index Document", type="primary", use_container_width=True):
                    if len(doc_content.strip()) < 20:
                        st.warning("⚠️ Please enter document text of at least 20 characters before indexing.")
                    else:
                        with st.spinner("Chunking text & embedding vector representation..."):
                            res, _ = api_call("post", "/documents/ingest", json={"content": doc_content, "filename": doc_name or "document.txt"})
                        if res:
                            st.session_state["rag_last_ingested_file"] = res['filename']
                            st.session_state["rag_ingest_msg"] = f"✅ Ingested `{res['filename']}` — {res['chunks_created']} vector chunks indexed"
                            st.rerun()
            else:
                uploaded = st.file_uploader("Choose file:", type=["txt", "md", "pdf"])
                if uploaded and st.button("📥 Process & Embed File", type="primary", use_container_width=True):
                    with st.spinner("Embedding vector representation..."):
                        files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type or "application/octet-stream")}
                        try:
                            with httpx.Client(timeout=300.0) as client:
                                resp = client.post(f"{API_BASE}/documents/ingest/file", files=files)
                                resp.raise_for_status()
                                res = resp.json()
                            st.session_state["rag_last_ingested_file"] = res['filename']
                            st.session_state["rag_ingest_msg"] = f"✅ Indexed `{res['filename']}` — {res['chunks_created']} chunks stored"
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Document ingestion failed: {e}")

            if st.session_state.get("rag_ingest_msg"):
                st.success(st.session_state["rag_ingest_msg"])

    with col2:
        with st.container(border=True):
            st.markdown("#### 💬 Semantic Q&A Query")
            
            # Fetch list of ingested document sources for targeted search scope
            sources_res, _ = api_call("get", "/documents/sources")
            stored_sources = sources_res.get("sources", []) if (sources_res and isinstance(sources_res, dict)) else []
            target_options = ["All Documents in Knowledge Base"] + stored_sources

            default_source_idx = 0
            if st.session_state.get("rag_last_ingested_file") in stored_sources:
                default_source_idx = target_options.index(st.session_state["rag_last_ingested_file"])

            selected_target_doc = st.selectbox(
                "🎯 Search Scope (Target Document):",
                options=target_options,
                index=default_source_idx,
                key="rag_target_doc_filter",
                help="Select a specific document to restrict retrieval strictly to that file, or search across all indexed documents."
            )

            question = st.text_input("Ask a Question across Knowledge Base:", key="rag_question", placeholder="What is our timeline for the Stripe integration?")

            if st.button("🔍 Search & Synthesize Answer", type="primary", use_container_width=True):
                if len(question.strip()) < 3:
                    st.warning("⚠️ Please enter a question of at least 3 characters.")
                else:
                    with st.spinner("Executing vector search & generating grounded response..."):
                        payload = {"question": question}
                        if selected_target_doc and selected_target_doc != "All Documents in Knowledge Base":
                            payload["filename"] = selected_target_doc
                        res, _ = api_call("post", "/documents/ask", json=payload)
                    if res:
                        st.session_state["rag_qa_result"] = res

            if st.session_state.get("rag_qa_result"):
                result = st.session_state["rag_qa_result"]
                confidence = (result.get("confidence") or "low").lower()
                badge_cls = "badge-low" if confidence == "high" else "badge-high"
                
                st.markdown(f"""
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
                    <span style="font-weight:700; color:#f8fafc; font-size:1.1rem;">AI Answer</span>
                    <span class="badge {badge_cls}">Confidence: {confidence.upper()}</span>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"""
                <div style="background:rgba(16, 185, 129, 0.08); border:1px solid rgba(16, 185, 129, 0.2); border-radius:10px; padding:1.2rem; margin-bottom:1rem; color:#f1f5f9; line-height:1.6;">
                    {result.get('answer', 'No answer generated.')}
                </div>
                """, unsafe_allow_html=True)

                if result.get("reasoning"):
                    with st.expander("🧠 Agentic Reasoning Steps"):
                        st.markdown(result["reasoning"])

                sources = result.get("sources") or []
                if sources:
                    with st.expander(f"📚 Retrieved Context Sources ({len(sources)} Chunks)"):
                        for src in sources:
                            st.markdown(f"**{src.get('source', 'Unknown')}** *(Relevance Score: {src.get('relevance_score', 0):.3f})*")
                            st.caption(src.get("excerpt", "")[:250] + "...")
                            st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Workflow Tools
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### ⚙️ Automated Workflow Dispatcher")
    st.caption("Trigger automated actions (email generation, CSV export, calendar events) directly from meeting extractions.")

    mid_input = st.text_input(
        "Active Meeting ID:",
        key="automation_mid",
        placeholder="Paste meeting ID here...",
    )

    if mid_input.strip():
        st.session_state["last_meeting_id"] = mid_input.strip()

    col_tool1, col_tool2 = st.columns([3, 1])
    with col_tool1:
        tool_choice = st.selectbox("Select Action Tool:", [
            "email_draft — Draft Follow-up Email to Team",
            "csv_export — Export Action Items to Structured CSV",
            "calendar_event — Generate iCal/Google Calendar Event Payloads",
        ])
        tool_name = tool_choice.split(" —")[0]

    with col_tool2:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        run_tool = st.button("▶️ Execute Tool", type="primary", use_container_width=True)

    if run_tool:
        target_mid = st.session_state.get("automation_mid", "").strip()
        if not target_mid:
            st.warning("⚠️ Please enter or select a valid Meeting ID first.")
        else:
            with st.spinner(f"Executing workflow tool `{tool_name}`..."):
                result, status = api_call("post", f"/tools/meetings/{target_mid}/automate", json={"tool_name": tool_name})

            if result and result.get("status") == "success":
                st.session_state["active_tool_result"] = {"tool": tool_name, "data": result}
                st.toast(f"✅ `{tool_name}` executed successfully!", icon="🚀")
            else:
                st.session_state["active_tool_result"] = None

    if st.session_state.get("active_tool_result"):
        tool_data = st.session_state["active_tool_result"]
        t_name = tool_data["tool"]
        result = tool_data["data"]

        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        if t_name == "email_draft":
            st.markdown("#### 📧 Generated Follow-Up Email")
            st.text_area("Email Output", value=result.get("output", ""), height=340, label_visibility="collapsed")
            st.download_button("⬇️ Download Email Draft (.txt)", data=result.get("output", ""), file_name="meeting_email_draft.txt", use_container_width=True)

        elif t_name == "csv_export":
            st.markdown("#### 📊 Exported CSV Dataset")
            st.text_area("CSV Output", value=result.get("output", ""), height=220, label_visibility="collapsed")
            st.download_button("⬇️ Download Action Items (.csv)", data=result.get("output", ""), file_name="action_items.csv", mime="text/csv", use_container_width=True)

        elif t_name == "calendar_event":
            st.markdown("#### 📅 Calendar Events Generated")
            events = result.get("output") or []
            if events:
                for ev in events:
                    with st.expander(f"📌 {ev.get('summary', 'Scheduled Task')}"):
                        st.json(ev)
            else:
                st.info("No actionable items with explicit dates were found for calendar export.")
            
            st.download_button("⬇️ Download Calendar Payloads (JSON)", data=json.dumps(events, indent=2), file_name="calendar_events.json", mime="application/json", use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Meeting Repository
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("### 📋 Historic Meetings Repository")
    st.caption("Browse all archived meeting sessions, inspect summaries, and generate formatted reports.")

    col_h1, col_h2 = st.columns([4, 1])
    with col_h2:
        if st.button("🔄 Refresh List", use_container_width=True):
            st.rerun()

    meetings, _ = api_call("get", "/meetings/")

    if meetings is None:
        st.warning("Could not retrieve meeting history.")
    elif len(meetings) == 0:
        st.info("No meeting records found. Process a meeting transcript in Tab 1.")
    else:
        st.markdown(f"**Total Archived Sessions:** `{len(meetings)}`")
        for m in meetings:
            status_icon = "✅" if m.get("status") == "summarised" else "📤"
            title_display = m.get("title") or f"Session {m['id'][:8]}"
            created = m.get("created_at", "")[:19].replace("T", " ")
            
            with st.expander(f"{status_icon} **{title_display}** — `{created}`"):
                st.markdown(f"**Session ID:** `{m['id']}` | **Status:** `{m.get('status')}`")
                st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

                btn_col1, btn_col2, btn_col3 = st.columns(3)
                
                show_det_key = f"show_detail_{m['id']}"
                show_rep_key = f"show_report_{m['id']}"

                if btn_col1.button("📖 Inspect Details", key=f"det_btn_{m['id']}", use_container_width=True):
                    st.session_state[show_det_key] = not st.session_state.get(show_det_key, False)
                    st.session_state[show_rep_key] = False

                if btn_col2.button("📄 Generate Report", key=f"rep_btn_{m['id']}", use_container_width=True):
                    st.session_state[show_rep_key] = not st.session_state.get(show_rep_key, False)
                    st.session_state[show_det_key] = False

                if btn_col3.button("⚙️ Load into Automation", key=f"tool_btn_{m['id']}", use_container_width=True):
                    st.session_state["last_meeting_id"] = m["id"]
                    st.session_state["automation_mid"] = m["id"]
                    st.session_state["active_tool_result"] = None
                    st.toast(f"Session `{m['id'][:8]}` loaded into Automation tab!", icon="📌")

                if st.session_state.get(show_det_key):
                    cache_key = f"detail_cache_{m['id']}"
                    if cache_key not in st.session_state:
                        with st.spinner("Fetching session details..."):
                            detail, _ = api_call("get", f"/meetings/{m['id']}")
                            if detail:
                                st.session_state[cache_key] = detail
                    
                    detail = st.session_state.get(cache_key)
                    if detail:
                        st.text_area("Transcript Preview", value=detail.get("transcript", ""), height=180, disabled=True)
                        if detail.get("summary"):
                            st.json(detail["summary"])

                if st.session_state.get(show_rep_key):
                    cache_key = f"report_cache_{m['id']}"
                    if cache_key not in st.session_state:
                        with st.spinner("Generating executive report..."):
                            report, _ = api_call("get", f"/meetings/{m['id']}/report")
                            if report:
                                st.session_state[cache_key] = report
                    
                    report = st.session_state.get(cache_key)
                    if report and report.get("markdown"):
                        st.markdown(report["markdown"])
