# Section 13 — Top 15 Questions to Practice First + Rapid-Fire Revision

---

## Top 15 Most Important Questions

These are the questions most likely to be asked in any interview where this project appears on your resume. Master these before anything else.

---

**1. Tell me about your Meeting-to-Action Agent project.**
Practice a 90-second answer covering: problem, solution, stack, what you built, what's impressive. See `00_project_summary_and_index.md` for the exact script.

---

**2. How is this different from just asking ChatGPT?**
Key points: persistence (SQLite), structured outputs (Pydantic JSON schema), automation (tools), RAG (your own documents). It's a pipeline, not a conversation.

---

**3. Walk me through the end-to-end flow when a user uploads a transcript.**
Trace: Streamlit → POST /meetings/upload → Pydantic validation → SQLite insert → UUID returned → POST /summarise → fetch transcript → agent prompt → Groq LLM → regex extract JSON → Pydantic validate → SQLite save → return to UI.

---

**4. What is RAG and how did you implement it?**
RAG = retrieve relevant chunks from your own documents first, then give to LLM as context. Your implementation: ChromaDB + ONNX embeddings → cosine similarity top-4 → inject into prompt → Groq generates grounded answer with confidence + sources.

---

**5. Why ChromaDB instead of FAISS?**
FAISS + sentence-transformers = 700MB PyTorch. ChromaDB = ONNX embeddings built-in, installs in seconds, persistent by default. For local dev/portfolio = ChromaDB wins.

---

**6. How do you handle invalid JSON from the LLM?**
Three layers: (1) regex strip markdown fences, (2) json.loads() in try/except, (3) Pydantic validation. Each layer catches what the previous missed. Failures return 422 with raw LLM output in logs.

---

**7. What are your guardrails for tool calling?**
Single `dispatch_tool()` entry point. Allowlist registry — unknown tool names rejected with 400 before execution. Input validation — action_items must be list of dicts with 'task' field. Pure functions — no real external I/O in MVP.

---

**8. Why FastAPI over Flask?**
Native async (LLM calls are async I/O), automatic Pydantic validation on request/response, auto-generated `/docs`. Flask needs extensions for all of this.

---

**9. Why SQLite and when would you replace it?**
SQLite: zero setup, no server, works fine for single-process writes. Replace with PostgreSQL when: multiple concurrent workers, complex relational queries, or production deployment with proper migrations.

---

**10. How do you test an AI system that produces non-deterministic output?**
Mock the LLM with `AsyncMock` returning fixed `SummaryResult`. Test the plumbing: route → service → database → response model. Evaluate real LLM quality separately with a labelled test set.

---

**11. What are the failure modes in your RAG pipeline?**
Semantic mismatch, stale documents, chunk boundary splits, retrieval noise at high k. Mitigations: overlapping chunks, upsert by doc_id, confidence thresholds, reranking.

---

**12. How would you scale this for 10,000 users per day?**
PostgreSQL, background job queue (Celery/Redis), ChromaDB → Pinecone, multiple Gunicorn workers, rate limiting, authentication, caching repeated transcripts by hash.

---

**13. What was the hardest technical problem you solved?**
Two good answers: (1) Python 3.14 + pydantic-core binary wheel issue → pinned pydantic>=2.11. (2) Robust LLM JSON parsing — regex + json.loads + Pydantic layering.

---

**14. What would you improve if you had more time?**
Background job processing, evaluation harness with ground-truth labels, normalised DB schema (action_items table), authentication, Zoom/Teams webhook integration.

---

**15. How do you prevent hallucination in extraction?**
Prompt instruction: "only extract explicitly stated items." Sentinel values: use "TBD" / "Unassigned" instead of guessing. RAG grounding: "answer ONLY from context." Confidence field: low confidence → human review. Verify-before-commit pattern for future improvement.

---

---

## Rapid-Fire Questions (One-Line Q&A for Quick Revision)

**Q: What does the project do?**
A: Turns meeting transcripts into structured action items, decisions, risks, requirements, reports, and automated workflows.

**Q: What LLM do you use?**
A: Groq's Llama 3.1-8b-instant via LangChain.

**Q: What is the vector database?**
A: ChromaDB with ONNX embeddings (built-in, no PyTorch).

**Q: What is the relational database?**
A: SQLite via aiosqlite (async).

**Q: How many tests do you have?**
A: 37 across 4 phases.

**Q: What is Pydantic used for?**
A: Request/response validation, config management (BaseSettings), and LLM output schema enforcement.

**Q: What is LangChain used for?**
A: Calling the Groq LLM via ChatGroq and building the RAG retrieval chain.

**Q: What is RAG?**
A: Retrieve relevant document chunks first, then give them to the LLM as context so it answers from your data, not its training.

**Q: What is a guardrail in tool calling?**
A: A validation check that runs before tool execution — e.g., rejecting unknown tool names.

**Q: Why is async important here?**
A: LLM calls take 5-20 seconds; async lets the event loop serve other requests during that wait instead of blocking.

**Q: What does the summarise endpoint return?**
A: A `SummaryResult` JSON with summary, key_topics, decisions, participants, action_items, requirements, and risks.

**Q: How do you handle a missing owner in action items?**
A: The prompt instructs "Unassigned" as the default — never guess an owner.

**Q: What is chunking in RAG?**
A: Splitting a long document into smaller overlapping pieces before embedding — 512 tokens with 64-token overlap.

**Q: What is top-k retrieval?**
A: Returning the k most similar document chunks from the vector store — I use k=4.

**Q: What HTTP status codes do your errors return?**
A: 422 for invalid input or LLM schema errors, 404 for not found, 400 for tool validation errors, 500 for unexpected failures.

**Q: What is lru_cache used for?**
A: Caching `get_settings()` so Pydantic reads the .env file once per process, not on every request.

**Q: What's the endpoint to generate a follow-up email?**
A: `POST /tools/meetings/{id}/automate` with `{"tool_name": "email_draft"}`.

**Q: What does the report endpoint return?**
A: Both a Markdown-formatted report and a JSON data object.

**Q: Why are prompts in .txt files, not in Python?**
A: Separates prompt engineering from code — iterate on prompts without touching the codebase.

**Q: What is `lifespan` in FastAPI?**
A: An async context manager that replaces deprecated `@app.on_event` — runs startup (DB init, key validation) and shutdown logic.

**Q: How do you mock the LLM in tests?**
A: `patch("app.routes.meetings.summarise_meeting", new_callable=AsyncMock, return_value=mock_summary)`.

**Q: What is prompt injection?**
A: When malicious content in user input contains instructions that hijack LLM behaviour — mitigated by tool registry and schema enforcement.

**Q: Why use `upsert` in ChromaDB?**
A: Makes re-ingestion idempotent — the same doc_id replaces old chunks instead of duplicating them.

**Q: What is the `confidence` field in RAG responses?**
A: `high` = context directly answers it, `medium` = inference required, `low` = tangential — used to flag answers for human review.

**Q: Single agent vs multi-agent — what did you use?**
A: Specialist pattern — separate focused agents per task (summary, action items, requirements, risks), each with its own prompt.

**Q: What would you add first in a production version?**
A: Background job queue for summarisation — currently it blocks the HTTP request for 10-20 seconds.

**Q: How is ChromaDB persisted?**
A: Automatically to `./chroma_db/` directory — survives process restarts without any extra serialisation code.

**Q: What Python version does this run on?**
A: Python 3.14 (resolved pydantic-core binary wheel issue by pinning pydantic>=2.11).

**Q: What does CORS middleware do in your app?**
A: Allows the Streamlit frontend (port 8501) to make HTTP requests to the FastAPI backend (port 8000) without browser blocking.

**Q: Why are tool functions pure (no real I/O)?**
A: Safety + testability — pure functions are trivially testable and have no unintended side effects in MVP.
