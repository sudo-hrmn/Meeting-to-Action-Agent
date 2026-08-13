# Real Issues Faced While Building Meeting-to-Action Agent

> A log of every real bug, error, and design problem encountered during development — with root cause and exact fix. Useful for interviews when asked "what went wrong?" or "what was hardest?"

---

## Issue 1 — Python 3.14 + pydantic-core Binary Wheel Incompatibility

**When:** Phase 1 — initial `pip install -r requirements.txt`

**Error:**
```
ERROR: Could not find a version that satisfies the requirement pydantic-core==2.23.4
(from pydantic==2.9.2)
No matching distribution found for pydantic-core==2.23.4
```

**Root Cause:**
`pydantic-core` is a Rust-compiled C extension. Pre-built binary wheels only exist for specific Python versions. Python 3.14 was too new — no wheel was published for it yet. `pip` tried to compile from source, which failed because the Rust toolchain build process couldn't resolve the exact version.

**Fix:**
Pinned pydantic to `>=2.11` which had pre-built wheels for Python 3.14:
```
pydantic>=2.11
pydantic-settings>=2.5
```

**Interview Answer:**
> "I hit a binary wheel compatibility issue with pydantic-core on Python 3.14. The package is Rust-compiled and pre-built wheels didn't exist for that version yet. I diagnosed it from the pip error log, identified that newer pydantic versions had wheels available, and pinned to pydantic>=2.11 which resolved it."

---

## Issue 2 — LangChain Import Path Reorganisation

**When:** Phase 1-2 — importing LangChain components

**Error:**
```
ImportError: cannot import name 'ChatGroq' from 'langchain'
ModuleNotFoundError: No module named 'langchain.text_splitter'
```

**Root Cause:**
LangChain split its monolithic package into sub-packages in newer versions. Classes moved:
- `langchain.chat_models.ChatGroq` → `langchain_groq.ChatGroq`
- `langchain.text_splitter` → `langchain_text_splitters`
- `langchain.vectorstores` → `langchain_community.vectorstores`

**Fix:**
Used the correct scoped imports:
```python
from langchain_groq import ChatGroq
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.messages import HumanMessage
```
Added `langchain-groq` and `langchain-community` to `requirements.txt`.

**Interview Answer:**
> "LangChain reorganised its package structure in newer versions — classes moved from `langchain` into sub-packages like `langchain_groq` and `langchain_text_splitters`. I fixed this by updating all imports to the correct scoped package names and adding the required sub-packages to requirements.txt."

---

## Issue 3 — ChromaDB ONNX Model Download Timeout on First Request

**When:** Phase 5 testing — first PDF upload via the Streamlit UI

**Error:**
```
Upload failed: timed out
```

**Root Cause:**
`DefaultEmbeddingFunction()` in ChromaDB downloads its ONNX embedding model (~90MB, `all-MiniLM-L6-v2`) **lazily — on the very first `collection.upsert()` call**, not at server startup. On a slow connection this download takes longer than the Streamlit frontend's hardcoded `timeout=60.0` on the `httpx.Client`, triggering the timeout error.

The download repeated every time the server restarted (due to `--reload`) because the model was downloaded into a temp cache that reset.

**Fix — Two changes:**

1. **`app/main.py`** — pre-warm ChromaDB at startup so the ONNX model downloads once before any request:
```python
from app.agents.rag_agent import _get_collection
# inside lifespan, after init_db():
_get_collection()   # downloads ONNX model at boot, not mid-request
```

2. **`frontend/app.py`** line 248 — increased upload timeout:
```python
# Before:
with httpx.Client(timeout=60.0) as client:
# After:
with httpx.Client(timeout=300.0) as client:
```

**What didn't work (attempted first):**
Tried replacing `DefaultEmbeddingFunction` with `HuggingFaceInferenceAPIEmbeddings` (API-based, no download needed). This failed because the machine had no internet access to `api-inference.huggingface.co` — DNS resolution failed. Had to revert and use the pre-warm approach instead.

**Interview Answer:**
> "The first PDF upload always timed out because ChromaDB downloads its ONNX model lazily on the first request — not at startup. I fixed this by calling `_get_collection()` inside the FastAPI lifespan context manager so the model downloads at boot, before any request comes in. I also tried switching to the HuggingFace Inference API for embeddings but the machine had no DNS access to that host, so I reverted."

---

## Issue 4 — HuggingFace Inference API DNS Failure

**When:** Between Issue 3 attempts — testing HF API-based embeddings

**Error:**
```
HTTPSConnectionPool(host='api-inference.huggingface.co', port=443):
Max retries exceeded with url: /pipeline/feature-extraction/BAAI/bge-small-en-v1.5
(Caused by NameResolutionError: Failed to resolve 'api-inference.huggingface.co'
[Errno -5] No address associated with hostname)
```

**Root Cause:**
The development machine could not reach `api-inference.huggingface.co` — either no internet access for that host or a DNS/firewall block. `HuggingFaceInferenceAPIEmbeddings` makes an HTTPS call to that endpoint for every embedding operation.

**Fix:**
Reverted to `DefaultEmbeddingFunction` (local ONNX, no internet needed) and used the startup pre-warm approach (Issue 3 fix) instead.

**Interview Answer:**
> "I attempted to use HuggingFace's Inference API for embeddings to avoid local model downloads, but the machine had no DNS access to api-inference.huggingface.co. This taught me to always verify network constraints in your target environment before choosing an API-based dependency."

---

## Issue 5 — Workflow Tools 422: `action_items` Field Required

**When:** Phase 5 testing — running email_draft / csv_export / calendar_event from the Workflow Tools tab

**Error:**
```
API 422: [{'type': 'missing', 'loc': ['body', 'action_items'],
'msg': 'Field required', 'input': {'tool_name': 'email_draft'}}]
```

**Root Cause:**
The `/tools/meetings/{id}/automate` endpoint reused `ToolRunRequest` as its request body schema. `ToolRunRequest` declared `action_items` with `...` (Pydantic's required marker). But this endpoint fetches action items from the database itself — it never needs them in the request body. The frontend correctly sent only `{"tool_name": "email_draft"}`, but Pydantic rejected it with 422 before the route logic even ran.

**Fix:**
Created a separate slim schema `MeetingAutomateRequest` with only `tool_name` and `meeting_title` (no `action_items`), and used it exclusively on the automate endpoint.

**`app/schemas/tools.py`:**
```python
class MeetingAutomateRequest(BaseModel):
    tool_name: str = Field(...)
    meeting_title: Optional[str] = Field(None)
```

**`app/routes/tools.py`:**
```python
# Before:
async def automate_from_meeting(meeting_id: str, request: ToolRunRequest)
# After:
async def automate_from_meeting(meeting_id: str, request: MeetingAutomateRequest)
```

**Interview Answer:**
> "Two endpoints shared the same Pydantic request schema, but the automate endpoint doesn't need action_items in the body — it fetches them from the database. The fix was to create a separate slim schema for that endpoint. This is a classic schema reuse mistake: one schema should not serve two endpoints with different input requirements."

---

## Issue 6 — Email Draft Showing `[NOT SPECIFIED]` and `[MUST-HAVE]`

**When:** Phase 5 testing — generating email drafts from meetings

**Problem:**
```
1. [NOT SPECIFIED] Post job descriptions
6. [MUST-HAVE] Create monitoring dashboards
```

**Root Cause — Two separate causes:**

1. **`[NOT SPECIFIED]`**: The summarisation LLM returns `priority: "not specified"` (as a string) when it can't infer a priority from the transcript. The old code did `.get("priority", "medium").upper()` — so `"not specified".upper()` → `"NOT SPECIFIED"` went straight into the email.

2. **`[MUST-HAVE]`**: The requirements extraction agent uses `"must-have"` as a priority label. This occasionally leaked into action items. Again, no normalization existed.

**Fix:**
Added a `_normalize_priority()` function inside `tool_email_draft` that maps any incoming value to a clean emoji display:

```python
def _normalize_priority(raw):
    if not raw:
        return "🟡 Medium"
    key = raw.strip().lower()
    if key in ("must-have", "critical", "urgent"):
        return "🔴 High"
    if key in ("should-have", "nice-to-have", "optional", "not specified"):
        return "🟢 Low"
    return {"high": "🔴 High", "medium": "🟡 Medium", "low": "🟢 Low"}.get(key, "🟡 Medium")
```

Also rewrote the email template with proper structure, emoji labels, separator lines, and a professional sign-off.

**Interview Answer:**
> "The email was showing raw LLM output values like [NOT SPECIFIED] because there was no normalization layer between what the LLM returns and what the email template renders. I added a priority normalizer that maps all non-standard values to high/medium/low with emoji indicators, and redesigned the email template to be genuinely professional."

---

## Issue 7 — ChromaDB Collection Incompatibility After Embedding Function Switch

**When:** During Issue 3 fix attempts — switching between DefaultEmbeddingFunction and HF embeddings

**Problem:**
After switching embedding functions and then reverting, the existing `chroma_db/` directory contained embeddings generated by `DefaultEmbeddingFunction`. If a different embedding function had written some data in between, retrieval would silently return wrong results (vectors from different embedding spaces are not comparable).

**Fix:**
Wiped the `chroma_db/` directory when switching embedding functions:
```bash
rm -rf chroma_db/
```
Also added `chroma_db/` to `.gitignore` to prevent accidentally committing vector data.

**Interview Answer:**
> "When you change the embedding model, all existing vectors become incompatible — they're in a different mathematical space. You must re-ingest all documents from scratch. This is a real production concern: any embedding model upgrade requires a full re-indexing of your vector store."

---

## Issue 8: `uv add` failing with "No pyproject.toml found"

**Phase:** Dependency Management & Environment Setup

**Problem:**
Running `uv add -r requirements.txt` failed with:
`error: No pyproject.toml found in current directory or any parent directory`

**Root Cause:**
`uv add` is designed for projects initialized with a `pyproject.toml` workspace file. For projects using standard `requirements.txt`, `uv add` expects project metadata to exist.

**Fix:**
Switched to using `uv pip install`:
```bash
.venv/bin/uv pip install -r requirements.txt
```

---

## Issue 9: Unnatural / Pre-Summarized Sample Meeting Generation

**Phase:** Phase 5 — Frontend & LLM Generation

**Problem:**
Clicking the example button generated transcripts formatted as `Meeting Transcript:`, `Attendees:`, and `Action Items:` lists rather than raw conversational dialogue.

**Root Cause:**
The LLM prompt lacked explicit negative formatting rules, causing Llama 3.1 to generate pre-formatted summaries instead of unscripted spoken dialogue.

**Fix:**
1. Updated prompt in `generate_sample_transcript()` to enforce strict format rules forbidding markdown headers, bullet lists, or summary sections.
2. Injected a random name pool (`NAMES_POOL`) and random business domains (`SAMPLE_DOMAINS`) on every request.
3. Added post-processing line filters to strip markdown headers if returned by the LLM.

---

## Issue 10: Streamlit `ModuleNotFoundError` & Uvicorn Port 8000 Address In Use

**Phase:** Deployment & Execution

**Problem:**
Starting Streamlit failed with `ModuleNotFoundError: No module named 'httpx'`, while restarting backend failed with `[Errno 98] Address already in use`.

**Root Cause:**
- System `streamlit` binary was invoked instead of virtualenv binary `.venv/bin/streamlit`.
- Backend process was already running on port 8000 in the background.

**Fix:**
Verified running backend with `curl http://localhost:8000/health` and launched Streamlit using `.venv/bin/streamlit run frontend/app.py`.

---

## Summary Table

| # | Issue | Phase | Root Cause | Fix |
|---|---|---|---|---|
| 1 | pydantic-core wheel missing | Setup | Python 3.14 too new for pre-built wheels | Pin `pydantic>=2.11` |
| 2 | LangChain import errors | Phase 1 | Package reorganised into sub-packages | Use scoped imports |
| 3 | Upload timeout (ONNX download) | Phase 5 | ChromaDB downloads model on first request | Pre-warm `_get_collection()` at startup |
| 4 | HF Inference API DNS failure | Phase 5 | No DNS access to `api-inference.huggingface.co` | Reverted to local ONNX embeddings |
| 5 | Tools 422 missing `action_items` | Phase 5 | Wrong schema reused for two different endpoints | New `MeetingAutomateRequest` schema |
| 6 | `[NOT SPECIFIED]` in email | Phase 5 | No priority normalization — raw LLM string in template | `_normalize_priority()` function |
| 7 | ChromaDB incompatibility on switch | Phase 5 | Different embedding spaces can't be mixed | Wipe `chroma_db/` and re-ingest |
| 8 | `uv add` missing `pyproject.toml` | Setup | `uv add` requires `pyproject.toml` | Use `uv pip install -r requirements.txt` |
| 9 | Unnatural sample transcripts | Phase 5 | LLM prompt lacked negative formatting rules | Enforced raw dialogue rules & name pool |
| 10 | Port 8000 in use & missing `httpx` | Deploy | System binary used & server already active | Used `.venv/bin/streamlit` & checked port PID |
