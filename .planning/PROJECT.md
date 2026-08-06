# Meeting-to-Action Agent

## What This Is

An AI-powered backend system that transforms raw meeting conversations into structured, actionable intelligence. It ingests transcripts or audio summaries, uses LLMs to extract requirements, action items, owners, deadlines, and risks, answers questions via a RAG pipeline over internal knowledge, and can trigger safe automated workflows (email drafts, calendar events, spreadsheet exports).

## Core Value

> Turn any meeting into a structured, searchable, and actionable output — automatically.

This is a **portfolio project** designed to be practical, intelligent, and industry-ready. It demonstrates multi-agent AI orchestration, RAG, structured JSON outputs, tool-using agents, and production-grade FastAPI design.

## Context

- **Stack:** FastAPI · Streamlit · Groq LLMs · FAISS vector store · HuggingFace embeddings · SQLite · LangChain · Pydantic · pytest
- **Free-tier only:** All APIs used are free (Groq, HuggingFace, Tavily, FAISS local)
- **API Keys available in `.env`:** `GROQ_API_KEY`, `TAVILY_API_KEY`, `HUGGINGFACEHUB_API_TOKEN`
- **Python virtual env:** `.venv/` already exists in project root
- **Architecture principles:** Modular · Prompts separate from code · Structured JSON outputs · Guardrails on tool calls · Explainable · Easy to extend

## Requirements

### Validated

(None yet — ship to validate)

### Active

**Phase 1 — Foundation**
- [ ] FastAPI project structure with clean separation (routes, services, agents, tools, schemas, config)
- [ ] Environment variable-based config (no hardcoded secrets)
- [ ] Structured logging
- [ ] Meeting transcript upload endpoint (accept text or file)
- [ ] LLM-powered meeting summarisation returning structured JSON
- [ ] Streamlit frontend for transcript upload and summary display

**Phase 2 — Extraction Agents**
- [ ] Requirement extraction agent — extracts project requirements from meeting text
- [ ] Action item extraction agent — extracts tasks with owner, deadline, priority
- [ ] Structured note generation — produces clean Markdown + JSON report per meeting
- [ ] Risk identification from meeting text

**Phase 3 — RAG Pipeline**
- [ ] Document ingestion pipeline (PDF, TXT, Markdown)
- [ ] FAISS vector store with HuggingFace embeddings
- [ ] Retrieval-augmented question answering over ingested documents
- [ ] Source references returned with every answer

**Phase 4 — Tool-Using Workflows**
- [ ] Email draft generation from action items
- [ ] Google Sheets / CSV export of action items
- [ ] Calendar event suggestion generation
- [ ] Safe tool calling with guardrails and validation

**Phase 5 — Quality & Portfolio**
- [ ] pytest test suite (unit + integration)
- [ ] Error handling and input validation throughout
- [ ] API documentation (auto-generated via FastAPI)
- [ ] Interview Q&A document covering all architectural decisions
- [ ] Final README with architecture diagram and usage guide

### Out of Scope

- Real-time audio transcription (handled externally; text transcripts are the input)
- Production deployment / cloud infrastructure (local dev only for portfolio)
- OAuth / multi-user auth (single-user MVP)
- LangGraph multi-agent orchestration (only if single-agent LangChain becomes insufficient)

## Key Decisions

| Decision | Rationale | Outcome |
|---|---|---|
| FastAPI as backend | Industry-standard, async, auto-docs, Pydantic-native | — Pending |
| Groq for LLMs | Free, fast inference (Llama 3.x models) | — Pending |
| FAISS (local) for vectors | No cloud dependency, free, sufficient for MVP | — Pending |
| HuggingFace embeddings | Free, no API cost, runs locally | — Pending |
| SQLite for storage | Zero-setup, fits portfolio scope | — Pending |
| LangChain for pipelines | Mature ecosystem, prompt separation, chain composition | — Pending |
| Pydantic for schemas | Strong validation, native FastAPI integration | — Pending |
| Separate prompts from code | Maintainability, easy iteration without code changes | — Pending |
| YOLO mode (all phases) | Portfolio build — speed matters, low risk of divergence | — Pending |

## Milestones

- **M1:** Foundation + Summarisation (Phases 1–2)
- **M2:** RAG + Tool Workflows (Phases 3–4)
- **M3:** Polish + Portfolio Hardening (Phase 5)

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition:**
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone:**
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-08-06 after initialization*
