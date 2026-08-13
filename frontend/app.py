"""
Streamlit frontend — Meeting-to-Action Agent (All Phases).

Tabs:
  1. Upload & Analyse   — transcript upload + AI summary display
  2. Knowledge Base     — document ingest + Q&A (RAG)
  3. Workflow Tools     — email draft, CSV export, calendar events
  4. Meeting History    — all meetings list view
"""
import json
import streamlit as st
import httpx

API_BASE = "http://localhost:8000"

st.set_page_config(
    page_title="Meeting-to-Action Agent",
    page_icon="🤝",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .main-header {
        font-size: 2.4rem; font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .sub-header { color: #6b7280; font-size: 1rem; margin-top: -0.5rem; }
    .section-card {
        background: #f8fafc; border: 1px solid #e2e8f0;
        border-radius: 10px; padding: 1.2rem; margin: 0.5rem 0;
    }
    .confidence-high { color: #059669; font-weight: 600; }
    .confidence-medium { color: #d97706; font-weight: 600; }
    .confidence-low { color: #dc2626; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ─── Header ────────────────────────────────────────────────────────────────────
st.markdown('<p class="main-header">🤝 Meeting-to-Action Agent</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">AI-powered meeting intelligence — summaries, action items, knowledge base, and workflow automation</p>', unsafe_allow_html=True)

# ─── API Helpers ───────────────────────────────────────────────────────────────
def api_call(method: str, endpoint: str, **kwargs) -> tuple[dict | list | None, int]:
    try:
        with httpx.Client(timeout=120.0) as client:
            fn = getattr(client, method)
            resp = fn(f"{API_BASE}{endpoint}", **kwargs)
            resp.raise_for_status()
            return resp.json(), resp.status_code
    except httpx.ConnectError:
        st.error("❌ Backend offline — run: `uvicorn app.main:app --reload`")
        return None, 0
    except httpx.HTTPStatusError as e:
        detail = e.response.json().get("detail", {}) if e.response.content else {}
        msg = detail.get("message", str(e)) if isinstance(detail, dict) else str(detail)
        st.error(f"❌ API {e.response.status_code}: {msg}")
        return None, e.response.status_code
    except Exception as e:
        st.error(f"❌ Error: {e}")
        return None, 0

def check_health() -> bool:
    try:
        with httpx.Client(timeout=3.0) as c:
            return c.get(f"{API_BASE}/health").status_code == 200
    except Exception:
        return False

# ─── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ System")
    is_up = check_health()
    st.success("✅ API Online") if is_up else st.error("❌ API Offline")
    if not is_up:
        st.code("uvicorn app.main:app --reload", language="bash")
    st.markdown("---")
    st.markdown("### 🔗 Quick Links")
    st.markdown(f"[📖 Swagger Docs]({API_BASE}/docs)  \n[❤️ Health]({API_BASE}/health)")
    st.markdown("---")
    st.markdown("### 🏗️ Stack")
    st.markdown("🧠 Groq · Llama 3.1  \n⚡ FastAPI  \n🗄️ ChromaDB  \n🗃️ SQLite  \n📦 LangChain")

# ─── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📤 Upload & Analyse",
    "🔍 Knowledge Base (RAG)",
    "⚙️ Workflow Tools",
    "📋 Meeting History",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Upload & Analyse
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("### 📝 Upload Meeting Transcript")

    EXAMPLE = """Alice (PM): Good morning. Let's start the Q3 planning. We need to finalize the payment integration roadmap.

Bob (Engineering Lead): From our side, the auth module is done. Payment integration is the priority — I'll own it and aim to ship by September 15th. We also need to hire two backend engineers by end of August. Alice, can you post the job descriptions?

Alice: Yes, I'll post them by tomorrow. Carol, where are we on designs?

Carol (Designer): Payment flow designs are 80% done, I'll finish by Friday. Risk though — if we don't get the Stripe API specs by Tuesday, we might slip the September deadline.

Bob: I'll follow up with Stripe today. Alice, can you also send an escalation email?

Alice: Absolutely, I'll do that this afternoon. Decided: we're going with Stripe as our payment provider — let's document that. Also, Bob, we need monitoring dashboards live before go-live. That's a must-have.

Bob: Agreed. Let's wrap up. Main actions: I own payment integration by Sep 15, Carol finishes designs by Friday, Alice posts job ads tomorrow and sends Stripe escalation today."""

    col1, col2 = st.columns([4, 1.5])
    with col2:
        if st.button("🎲 Generate Example", use_container_width=True, help="Generate a new AI meeting transcript on every click"):
            with st.spinner("🧠 LLM generating transcript..."):
                data, status = api_call("post", "/meetings/generate-sample", json={})
                if data and "transcript" in data:
                    st.session_state["example_transcript"] = data.get("transcript", "")
                    st.session_state["example_title"] = data.get("title", "")
                else:
                    st.session_state["example_transcript"] = EXAMPLE
                    st.session_state["example_title"] = "Q3 Planning Sync"

    transcript_val = st.session_state.get("example_transcript", "")
    title_val = st.session_state.get("example_title", "")

    transcript = st.text_area(
        "Paste transcript:",
        value=transcript_val,
        height=280,
        placeholder="Alice: Let's discuss the timeline...\nBob: We need to ship by Friday...",
    )
    title = st.text_input("Meeting title (optional):", value=title_val, placeholder="Q3 Planning — 2026-08-06")

    c1, c2, c3 = st.columns([3, 1, 1])
    with c1:
        go = st.button("🚀 Analyse Meeting", type="primary", use_container_width=True,
                       disabled=len(transcript.strip()) < 50)
    c2.metric("Chars", len(transcript))
    c3.metric("Words", len(transcript.split()))

    if go:
        with st.spinner("📤 Uploading..."):
            data, status = api_call("post", "/meetings/upload",
                                    json={"transcript": transcript, "title": title or None})
        if data:
            mid = data["id"]
            st.success(f"✅ Uploaded | ID: `{mid}`")
            st.session_state["last_meeting_id"] = mid

            with st.spinner("🧠 AI analysing (10–20 sec)..."):
                result, _ = api_call("post", f"/meetings/{mid}/summarise", json={})

            if result and result.get("summary"):
                s = result["summary"]
                st.session_state["last_summary"] = s
                st.markdown("---")
                st.markdown("## 📊 Analysis Results")
                st.info(s.get("summary", ""))

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("🎯 Topics", len(s.get("key_topics", [])))
                m2.metric("✅ Decisions", len(s.get("decisions", [])))
                m3.metric("📋 Actions", len(s.get("action_items", [])))
                m4.metric("⚠️ Risks", len(s.get("risks", [])))

                r1, r2, r3, r4, r5 = st.tabs(["🎯 Topics", "📋 Actions", "📦 Requirements", "⚠️ Risks", "🔍 JSON"])

                with r1:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Key Topics**")
                        for t in s.get("key_topics", []): st.markdown(f"• {t}")
                    with col2:
                        st.markdown("**Decisions Made**")
                        for d in s.get("decisions", []): st.markdown(f"• {d}")
                    if s.get("participants"):
                        st.markdown("**Participants:** " + " · ".join(f"`{p}`" for p in s["participants"]))

                with r2:
                    items = s.get("action_items", [])
                    if items:
                        for i, item in enumerate(items, 1):
                            icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(item.get("priority", ""), "⚪")
                            with st.expander(f"{icon} {i}. {item.get('task', '')}"):
                                a, b, c = st.columns(3)
                                a.markdown(f"**Owner:** {item.get('owner', 'Unassigned')}")
                                b.markdown(f"**Deadline:** {item.get('deadline', 'TBD')}")
                                c.markdown(f"**Priority:** `{item.get('priority', '')}`")
                    else:
                        st.info("No action items identified.")

                with r3:
                    reqs = s.get("requirements", [])
                    if reqs:
                        for r in reqs:
                            badge = {"must-have": "🔴", "should-have": "🟡", "nice-to-have": "🟢"}.get(r.get("priority", ""), "⚪")
                            st.markdown(f"{badge} **{r.get('requirement', '')}**")
                            st.caption(f"Category: {r.get('category', '')} · Priority: {r.get('priority', '')}")
                    else:
                        st.info("No requirements extracted.")

                with r4:
                    risks = s.get("risks", [])
                    if risks:
                        for rk in risks:
                            sev = rk.get("severity", "low")
                            icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(sev, "⚪")
                            with st.expander(f"{icon} {rk.get('risk', '')}"):
                                st.markdown(f"**Mitigation:** {rk.get('mitigation_suggestion', 'N/A')}")
                    else:
                        st.info("No risks identified.")

                with r5:
                    st.json(result)
                    st.download_button("⬇️ Download JSON",
                                       data=json.dumps(result, indent=2),
                                       file_name=f"meeting_{mid[:8]}.json",
                                       mime="application/json")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Knowledge Base (RAG)
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### 🔍 Knowledge Base — Document Q&A")
    st.markdown("Ingest documents, then ask questions. The AI answers using **only** your documents.")

    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.markdown("#### 📥 Ingest a Document")
        ingest_method = st.radio("Input method:", ["Paste text", "Upload file"], horizontal=True)

        if ingest_method == "Paste text":
            doc_content = st.text_area("Document content:", height=200,
                                       placeholder="Paste any document — meeting notes, PRD, design spec, policy...")
            doc_name = st.text_input("Document name:", placeholder="product_spec.txt")

            if st.button("📥 Ingest Document", type="primary", use_container_width=True,
                         disabled=len(doc_content.strip()) < 20):
                with st.spinner("Chunking + embedding..."):
                    result, _ = api_call("post", "/documents/ingest",
                                         json={"content": doc_content, "filename": doc_name or "document.txt"})
                if result:
                    st.success(f"✅ Ingested `{result['filename']}` — {result['chunks_created']} chunks stored")

        else:
            uploaded = st.file_uploader("Upload file:", type=["txt", "md", "pdf"])
            if uploaded and st.button("📥 Upload & Ingest", type="primary", use_container_width=True):
                with st.spinner("Uploading and embedding..."):
                    files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type)}
                    try:
                        with httpx.Client(timeout=300.0) as client:
                            resp = client.post(f"{API_BASE}/documents/ingest/file", files=files)
                            resp.raise_for_status()
                            result = resp.json()
                        st.success(f"✅ Ingested `{result['filename']}` — {result['chunks_created']} chunks")
                    except Exception as e:
                        st.error(f"❌ Upload failed: {e}")

    with col2:
        st.markdown("#### 💬 Ask a Question")
        question = st.text_input("Your question:", placeholder="What are the action items from the Q3 meeting?")

        if st.button("🔍 Ask", type="primary", use_container_width=True,
                     disabled=len(question.strip()) < 5):
            with st.spinner("Searching knowledge base + generating answer..."):
                result, _ = api_call("post", "/documents/ask", json={"question": question})

            if result:
                confidence = result.get("confidence", "low")
                conf_class = f"confidence-{confidence}"
                st.markdown(f"**Confidence:** <span class='{conf_class}'>{confidence.upper()}</span>",
                            unsafe_allow_html=True)
                st.markdown("#### Answer")
                st.success(result.get("answer", "No answer generated."))

                if result.get("reasoning"):
                    with st.expander("🧠 Reasoning"):
                        st.markdown(result["reasoning"])

                sources = result.get("sources", [])
                if sources:
                    with st.expander(f"📚 Sources ({len(sources)} chunks retrieved)"):
                        for src in sources:
                            st.markdown(f"**{src.get('source', 'Unknown')}** "
                                        f"(score: {src.get('relevance_score', 0):.3f})")
                            st.caption(src.get("excerpt", "")[:200] + "...")
                            st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Workflow Tools
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### ⚙️ Workflow Automation Tools")
    st.markdown("Run post-meeting automation on a summarised meeting's action items.")

    mid_input = st.text_input(
        "Meeting ID:",
        value=st.session_state.get("last_meeting_id", ""),
        placeholder="Paste meeting ID from Tab 1 or History",
    )

    tool_choice = st.selectbox("Select tool:", [
        "email_draft — Generate follow-up email",
        "csv_export — Export action items to CSV",
        "calendar_event — Generate calendar event JSON",
    ])
    tool_name = tool_choice.split(" —")[0]

    if st.button("▶️ Run Tool", type="primary", disabled=not mid_input.strip()):
        with st.spinner(f"Running {tool_name}..."):
            result, status = api_call(
                "post",
                f"/tools/meetings/{mid_input.strip()}/automate",
                json={"tool_name": tool_name},
            )

        if result and result.get("status") == "success":
            st.success(f"✅ `{tool_name}` completed — {result.get('metadata', {}).get('action_item_count', '?')} items processed")

            if tool_name == "email_draft":
                st.markdown("#### 📧 Email Draft")
                st.text_area("", value=result["output"], height=400)
                st.download_button("⬇️ Download .txt",
                                   data=result["output"],
                                   file_name="meeting_followup_email.txt")

            elif tool_name == "csv_export":
                st.markdown("#### 📊 CSV Export")
                st.text_area("", value=result["output"], height=200)
                st.download_button("⬇️ Download CSV",
                                   data=result["output"],
                                   file_name="action_items.csv",
                                   mime="text/csv")

            elif tool_name == "calendar_event":
                st.markdown("#### 📅 Calendar Events")
                events = result.get("output", [])
                if events:
                    for ev in events:
                        with st.expander(ev.get("summary", "Event")):
                            st.json(ev)
                else:
                    st.info("No events with specific deadlines found.")
                st.download_button("⬇️ Download JSON",
                                   data=json.dumps(result["output"], indent=2),
                                   file_name="calendar_events.json",
                                   mime="application/json")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Meeting History
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("### 📋 Meeting History")
    col1, col2 = st.columns([5, 1])
    with col2:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

    meetings, _ = api_call("get", "/meetings/")

    if meetings is None:
        st.warning("Could not load meetings.")
    elif len(meetings) == 0:
        st.info("No meetings yet. Upload one in 'Upload & Analyse'.")
    else:
        st.markdown(f"**{len(meetings)} meeting(s)**")
        for m in meetings:
            icon = "✅" if m.get("status") == "summarised" else "📤"
            title_display = m.get("title") or f"Meeting {m['id'][:8]}..."
            created = m.get("created_at", "")[:19].replace("T", " ")
            with st.expander(f"{icon} **{title_display}** — {created}"):
                c1, c2 = st.columns(2)
                c1.markdown(f"**ID:** `{m['id']}`")
                c2.markdown(f"**Status:** `{m.get('status')}`")

                cols = st.columns(3)
                if cols[0].button("📖 Full Details", key=f"det_{m['id']}"):
                    detail, _ = api_call("get", f"/meetings/{m['id']}")
                    if detail:
                        st.text_area("Transcript", value=detail.get("transcript", "")[:500], height=120, disabled=True)
                        if detail.get("summary"):
                            st.json(detail["summary"])

                if cols[1].button("📄 Get Report", key=f"rep_{m['id']}"):
                    report, _ = api_call("get", f"/meetings/{m['id']}/report")
                    if report and report.get("markdown"):
                        st.markdown(report["markdown"])

                if cols[2].button("📋 Use in Tools", key=f"tool_{m['id']}"):
                    st.session_state["last_meeting_id"] = m["id"]
                    st.success(f"Meeting ID copied to Tools tab!")
