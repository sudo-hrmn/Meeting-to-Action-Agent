# Meeting-to-Action Agent — Interview Preparation Guide

## How to Use This Guide
Each file covers one interview topic area. Study in order or jump to the section relevant to your interview type.

| File | Topic | Interview Type |
|---|---|---|
| 01_project_overview.md | What the project is, why it exists | Any interview |
| 02_architecture.md | System design, API design, data flow | Backend / System Design |
| 03_agent_design.md | Agents, prompts, structured outputs, guardrails | AI/LLM / Agentic AI |
| 04_rag.md | RAG pipeline, chunking, retrieval, vector DBs | AI/LLM / RAG |
| 05_tool_calling.md | Tool calling, guardrails, safety | Agentic AI |
| 06_backend_fastapi.md | FastAPI, endpoints, validation, async | Backend |
| 07_database.md | SQLite, schema design, storage decisions | Backend / DB |
| 08_evaluation_testing.md | Testing agents, RAG quality, hallucination | QA / AI |
| 09_deployment.md | Production readiness, config, logging, scaling | DevOps / Senior |
| 10_tradeoffs.md | Why X over Y — design decision defence | Any senior interview |
| 11_debugging.md | Failure modes, edge cases, recovery | Senior / Reliability |
| 12_resume_defense.md | Personal contribution, learnings, improvements | HR / Final round |
| 13_top15_rapidfire.md | Top 15 questions + rapid-fire revision | Last-minute prep |
| issues_that_faced.md | **Real bugs hit during development** — root causes + fixes | Any interview |

---

## Project Summary (Memorise This — Say It in Every Interview)

> "I built Meeting-to-Action Agent — an AI system that takes raw meeting transcripts and converts them into structured, actionable intelligence. You paste a transcript, and the system extracts action items with owners and deadlines, decisions made, requirements, and risks — all as structured JSON. It also has a RAG knowledge base where you can ingest internal documents and ask questions against them. Finally, it automates post-meeting workflows: it can generate a follow-up email draft, export action items to CSV, or generate calendar event JSON. The backend is FastAPI, the AI layer uses Groq's Llama 3.1 via LangChain with **LangSmith full-stack tracing**, storage is SQLite, the vector store is ChromaDB, and the frontend is Streamlit. I have 37 automated tests covering all phases and a **Graphify AST knowledge graph** for codebase dependency analysis."

### One-sentence version (for quick intro):
> "It's an observability-enabled AI pipeline that turns messy meeting transcripts into structured action items, risks, requirements, and automated follow-ups — with a RAG layer for asking questions against internal documents and LangSmith telemetry."

### What makes it non-trivial (say this when asked "why is this impressive"):
- **LangSmith Tracing & Observability**: Real-time tracing of LLM prompts, token consumption, latency, and Pydantic self-healing retries.
- **Dynamic Conversational Sample Generator**: LLM-driven raw dialogue generator with randomized speaker names (`NAMES_POOL`) and domains.
- **Graphify AST Knowledge Graph**: 326-node dependency graph mapping component relationships across routes, vector DB, and agents.
- **Structured JSON Output with Retry Logic**: Validated Pydantic models with single-pass self-healing retry on parse failures.
- **RAG Pipeline with Grounding**: Dense vector retrieval (`all-MiniLM-L6-v2`) with source attribution and `HIGH/MEDIUM/LOW` confidence scoring.
- **Tool Guardrail Registry**: Centralized dispatcher validating tool schemas before execution.
- **37 Automated Tests**: Full suite covering upload validation, mock LLM chains, tool guardrails, and RAG chunking utilities.
