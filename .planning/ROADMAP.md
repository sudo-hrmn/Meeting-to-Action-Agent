# Roadmap — Meeting-to-Action Agent

## Milestone 1 — Foundation + Extraction (M1)

### Phase 1: Foundation & Summarisation

**Goal:** Working FastAPI backend with project structure, config, logging, meeting upload, and LLM-powered summarisation.

- [ ] 1.1 — Project structure scaffold (folders, `__init__.py`, `main.py`, `requirements.txt`)
- [ ] 1.2 — Configuration & environment loading (`config.py`, `.env` validation, logging setup)
- [ ] 1.3 — Meeting upload endpoint (`POST /meetings/upload`, Pydantic schema, SQLite storage)
- [ ] 1.4 — Summarisation agent (`POST /meetings/{id}/summarise`, Groq LLM, structured JSON output)
- [ ] 1.5 — Streamlit frontend (transcript upload UI, summary display)

### Phase 2: Extraction Agents

**Goal:** Three specialized extraction agents that turn meeting text into structured data.

- [ ] 2.1 — Action item extraction agent (task, owner, deadline, priority)
- [ ] 2.2 — Requirement extraction agent (requirement, category, priority)
- [ ] 2.3 — Risk identification agent (risk, severity, mitigation)
- [ ] 2.4 — Meeting report endpoint (`GET /meetings/{id}/report`, full Markdown + JSON)
- [ ] 2.5 — Streamlit frontend update (show action items, requirements, risks tabs)

---

## Milestone 2 — RAG + Tool Workflows (M2)

### Phase 3: RAG Pipeline

**Goal:** Document ingestion and retrieval-augmented question answering with source attribution.

- [ ] 3.1 — Document ingestion pipeline (FAISS + HuggingFace embeddings, chunking)
- [ ] 3.2 — Document upload endpoint (`POST /documents/ingest`)
- [ ] 3.3 — Question answering endpoint (`POST /documents/ask`, grounded answers + sources)
- [ ] 3.4 — Streamlit RAG UI (document upload, Q&A interface)

### Phase 4: Tool-Using Workflows

**Goal:** Safe, validated tool-calling agents for post-meeting automation.

- [ ] 4.1 — Tool registry and guardrail framework
- [ ] 4.2 — Email draft generation tool
- [ ] 4.3 — CSV export tool for action items
- [ ] 4.4 — Calendar event suggestion tool
- [ ] 4.5 — Tool-calling endpoint (`POST /meetings/{id}/automate`)

### Phase 6: 1 Foundation & Summarisation

**Goal:** [To be planned]
**Requirements**: TBD
**Depends on:** Phase 5
**Plans:** 0 plans

Plans:

- [ ] TBD (run /gsd-plan-phase 6 to break down)

---

## Milestone 3 — Polish + Portfolio (M3)

### Phase 5: Quality & Portfolio Hardening

**Goal:** Test suite, error handling, documentation, and interview prep.

- [ ] 5.1 — pytest test suite (unit + integration, ≥80% coverage)
- [ ] 5.2 — Global error handling middleware (structured JSON errors)
- [ ] 5.3 — Interview Q&A document (20+ questions with detailed answers)
- [ ] 5.4 — README with architecture diagram (Mermaid), setup guide, usage examples
- [ ] 5.5 — API documentation review (FastAPI auto-docs polish)
