# Requirements — Meeting-to-Action Agent

## Overview

This document defines the full requirement set for the Meeting-to-Action Agent. Requirements are scoped by phase and include acceptance criteria (UAT) for each.

---

## Phase 1 — Foundation & Summarisation

### REQ-001: Project Structure
**Priority:** Must-have  
**Description:** FastAPI project with clean module separation — `routes/`, `services/`, `agents/`, `tools/`, `schemas/`, `config/`, `prompts/`, `tests/`  
**Acceptance:** All modules importable; no circular imports; app starts with `uvicorn`

### REQ-002: Configuration & Logging
**Priority:** Must-have  
**Description:** All secrets loaded from `.env` via `python-dotenv`. Structured JSON logging via Python `logging` module  
**Acceptance:** App fails fast with clear error if required env vars missing; logs show timestamp, level, and message

### REQ-003: Meeting Upload Endpoint
**Priority:** Must-have  
**Description:** `POST /meetings/upload` accepts raw text transcript (JSON body or `.txt` file upload)  
**Acceptance:** Returns 200 with meeting ID and stored transcript; validates non-empty input

### REQ-004: Meeting Summarisation
**Priority:** Must-have  
**Description:** `POST /meetings/{id}/summarise` calls Groq LLM and returns structured JSON summary  
**Acceptance:** Response contains `summary`, `key_topics`, `decisions`, `participants` keys; valid JSON always returned

### REQ-005: Streamlit Frontend (Basic)
**Priority:** Must-have  
**Description:** Simple Streamlit UI for uploading transcripts and displaying structured summaries  
**Acceptance:** User can paste or upload text, click "Analyse", and see formatted summary output

---

## Phase 2 — Extraction Agents

### REQ-006: Action Item Extraction
**Priority:** Must-have  
**Description:** Agent extracts action items from meeting text, each with `task`, `owner`, `deadline`, `priority`  
**Acceptance:** Returns JSON array; handles meetings with no action items gracefully

### REQ-007: Requirement Extraction
**Priority:** Must-have  
**Description:** Agent identifies project requirements mentioned in meeting discussions  
**Acceptance:** Returns structured list with `requirement`, `category`, `priority`

### REQ-008: Risk Identification
**Priority:** Should-have  
**Description:** Agent identifies risks, blockers, and open questions from meeting text  
**Acceptance:** Returns list with `risk`, `severity`, `mitigation_suggestion`

### REQ-009: Structured Note Report
**Priority:** Must-have  
**Description:** `GET /meetings/{id}/report` returns full structured meeting report as Markdown + JSON  
**Acceptance:** Report includes summary, action items, requirements, risks, and decisions

---

## Phase 3 — RAG Pipeline

### REQ-010: Document Ingestion
**Priority:** Must-have  
**Description:** `POST /documents/ingest` accepts PDF, TXT, or Markdown files and indexes them into FAISS  
**Acceptance:** Documents chunked, embedded via HuggingFace, stored in FAISS; returns document ID

### REQ-011: Question Answering
**Priority:** Must-have  
**Description:** `POST /documents/ask` takes a question and returns an answer grounded in ingested documents  
**Acceptance:** Answer includes `answer`, `sources` (document name + excerpt), and `confidence`

### REQ-012: Source Attribution
**Priority:** Must-have  
**Description:** Every RAG answer must cite the source document and relevant excerpt  
**Acceptance:** `sources` field always populated when answer is drawn from documents

---

## Phase 4 — Tool-Using Workflows

### REQ-013: Email Draft Generation
**Priority:** Should-have  
**Description:** Tool generates email draft from meeting action items  
**Acceptance:** Returns formatted email body as string; no actual sending (safe mock)

### REQ-014: CSV/Sheets Export
**Priority:** Should-have  
**Description:** Tool exports action items as CSV file  
**Acceptance:** Returns downloadable CSV with correct headers and rows

### REQ-015: Calendar Event Suggestion
**Priority:** Nice-to-have  
**Description:** Tool generates calendar event JSON (compatible with Google Calendar API format) from deadlines  
**Acceptance:** Returns structured event dict with `title`, `date`, `attendees`, `description`

### REQ-016: Tool Calling Guardrails
**Priority:** Must-have  
**Description:** All tool calls validated before execution; dangerous operations blocked  
**Acceptance:** Invalid tool calls return structured error; no unguarded external I/O

---

## Phase 5 — Quality & Portfolio

### REQ-017: Test Suite
**Priority:** Must-have  
**Description:** pytest tests for all endpoints, agents, and tools  
**Acceptance:** `pytest` passes with ≥80% coverage on core modules

### REQ-018: Error Handling
**Priority:** Must-have  
**Description:** All endpoints return structured JSON errors; no raw Python tracebacks exposed  
**Acceptance:** 4xx/5xx responses always include `error`, `message`, `request_id`

### REQ-019: Interview Q&A Document
**Priority:** Must-have  
**Description:** Markdown document with realistic interviewer questions and detailed answers about all architectural decisions  
**Acceptance:** Covers LLM choice, RAG design, agent architecture, tool safety, API design, testing strategy

### REQ-020: README & Architecture Diagram
**Priority:** Must-have  
**Description:** Professional README with project overview, setup instructions, architecture diagram (Mermaid), and usage examples  
**Acceptance:** Someone unfamiliar with the project can set it up and run it from the README alone

---

## Definition of Done (per Phase)

- [ ] All Must-have requirements for the phase implemented and passing
- [ ] All endpoints return valid structured JSON
- [ ] Unit tests written and passing
- [ ] No hardcoded secrets
- [ ] Code reviewed for clean separation of concerns
- [ ] Committed to git with descriptive message
