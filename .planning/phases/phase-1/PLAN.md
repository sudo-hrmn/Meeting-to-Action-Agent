# Phase 1 — Foundation & Summarisation

**Goal:** Working FastAPI backend with project structure, config/logging, meeting upload endpoint, LLM-powered summarisation, and a Streamlit UI.

**Requirements covered:** REQ-001, REQ-002, REQ-003, REQ-004, REQ-005

---

## Plan 1.1 — Project Structure Scaffold

**Why:** Every other plan depends on this. Clean separation (routes/services/agents/schemas/config/prompts/tests) means changes are isolated and the codebase stays readable as it grows.

**Tasks:**
- Create `requirements.txt` with all Phase 1 dependencies
- Create package directories with `__init__.py`: `app/`, `app/routes/`, `app/services/`, `app/agents/`, `app/schemas/`, `app/config/`, `app/prompts/`, `tests/`
- Create `app/main.py` — FastAPI app entry point with CORS, router registration, health check
- Create `.gitignore`

**Output:** `python -m uvicorn app.main:app --reload` starts without errors; `/health` returns `{"status": "ok"}`

---

## Plan 1.2 — Configuration & Logging

**Why:** Centralising config prevents secrets from leaking into code. Structured logging makes debugging and monitoring tractable. Fail-fast on missing env vars prevents silent failures.

**Tasks:**
- Create `app/config/settings.py` — Pydantic `BaseSettings` loading from `.env`
- Create `app/config/logging.py` — JSON-style structured logging setup
- Add startup validation — app errors clearly if `GROQ_API_KEY` missing

**Output:** App logs structured JSON; missing API key → clear startup error message

---

## Plan 1.3 — Meeting Upload Endpoint + SQLite Storage

**Why:** We need a persistent store for transcripts. SQLite is zero-config and perfectly sized for this portfolio project.

**Tasks:**
- Create `app/schemas/meeting.py` — Pydantic schemas (`MeetingUploadRequest`, `MeetingResponse`, `MeetingRecord`)
- Create `app/config/database.py` — SQLite connection via `aiosqlite`, table creation on startup
- Create `app/services/meeting_service.py` — CRUD operations for meetings
- Create `app/routes/meetings.py` — `POST /meetings/upload` endpoint
- Add router to `app/main.py`

**Output:** `POST /meetings/upload` with `{"transcript": "..."}` → `{"id": "uuid", "status": "uploaded"}`

---

## Plan 1.4 — Summarisation Agent (Groq LLM)

**Why:** This is the core intelligence of Phase 1. The agent calls Groq (Llama 3), parses structured JSON output, and stores the result. Keeping the prompt in a separate file makes iteration fast.

**Tasks:**
- Create `app/prompts/summarise.txt` — structured prompt template for meeting summarisation
- Create `app/agents/summarise_agent.py` — LangChain `ChatGroq` chain, JSON output parsing
- Create `app/services/summarise_service.py` — orchestrates agent call + result storage
- Add `POST /meetings/{id}/summarise` route to `app/routes/meetings.py`
- Add `GET /meetings/{id}` route (fetch meeting + summary)

**Output:** `POST /meetings/{id}/summarise` → `{"summary": "...", "key_topics": [...], "decisions": [...], "participants": [...]}`

---

## Plan 1.5 — Streamlit Frontend

**Why:** A visual UI makes the project demonstrable in portfolio reviews and interviews. Streamlit is the fastest path from backend to working demo.

**Tasks:**
- Create `frontend/app.py` — Streamlit app with tabs: "Upload & Summarise", "View History"
- Upload tab: text area for transcript, "Analyse Meeting" button, formatted summary display
- History tab: list of past meetings, click to view summary
- Create `frontend/requirements.txt` (streamlit + httpx)

**Output:** `streamlit run frontend/app.py` shows working UI connected to FastAPI backend

---

## Verification

- [ ] `uvicorn app.main:app --reload` starts cleanly
- [ ] `GET /health` → `{"status": "ok"}`
- [ ] `POST /meetings/upload` stores transcript and returns ID
- [ ] `POST /meetings/{id}/summarise` returns valid structured JSON with all required keys
- [ ] Streamlit UI loads and successfully calls the backend
- [ ] No hardcoded secrets anywhere in code
- [ ] `pytest tests/` passes for Phase 1 tests
