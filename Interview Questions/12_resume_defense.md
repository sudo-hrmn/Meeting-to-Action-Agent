# Section 12 — Resume & Project Defence Questions

---

**Q1. What was your personal contribution to this project?**
**A1.** I designed and built the entire system from scratch. Starting from a `rules.md` spec, I designed the modular FastAPI architecture, wrote all the agents and prompts, implemented the RAG pipeline, built the tool calling system with guardrails, and wrote 37 automated tests across four phases. I made key technical decisions: switching from FAISS+sentence-transformers to ChromaDB when I discovered the 700MB PyTorch dependency problem, fixing a Python 3.14 / pydantic-core binary wheel compatibility issue, and rewriting the LangChain import paths when the library extracted its modules in newer versions. The only things I didn't write are the third-party libraries.

**What the interviewer is testing:** Can you clearly articulate your own contribution? Are you honest?
**Possible follow-up:** What parts did you find hardest to implement?

---

**Q2. What was the hardest technical problem you encountered in this project?**
**A2.** Several real ones. First, the Python 3.14 + pydantic-core wheel issue — pydantic-core is Rust-compiled and no pre-built wheel existed for Python 3.14, so pip failed silently. Fixed by pinning `pydantic>=2.11`. Second, the ChromaDB ONNX model download timeout — `DefaultEmbeddingFunction` downloads its model lazily on the first request, not at startup. On a slow connection this exceeded the frontend's 60-second timeout. I tried switching to the HuggingFace Inference API for embeddings, but the machine had no DNS access to `api-inference.huggingface.co`. Final fix: call `_get_collection()` in the FastAPI lifespan so the model downloads at boot. Third, a schema reuse bug — the `/tools/meetings/{id}/automate` endpoint shared `ToolRunRequest` with the direct `/tools/run` endpoint. The automate endpoint fetches action items from the DB, but the shared schema required them in the request body, causing a 422 for every tool call from the UI.

**What the interviewer is testing:** Can you articulate a real technical challenge with a real solution?
**Possible follow-up:** How did you debug the pydantic-core issue — what was your process?

---

**Q3. What would you do differently if you started over?**
**A3.** Three things. First, I'd design the database schema more carefully upfront — storing summaries as JSON strings was a convenient shortcut but makes querying harder. I'd normalise action items into their own table from day one. Second, I'd add background job processing from the start — the summarisation endpoint currently blocks for 10-20 seconds waiting for the LLM. That's a bad user experience and would be a bigger refactor to fix later. Third, I'd set up the evaluation harness before writing prompts, not after — you can't measure prompt improvements without a baseline.

**What the interviewer is testing:** Do you reflect on your decisions and learn from them?
**Possible follow-up:** How long would it take to implement background job processing now?

---

**Q4. What did you learn from building this project?**
**A4.** Several important things. First, LLM output is far less reliable than documentation suggests — you need defensive parsing for every LLM response in production. Second, dependency management for AI packages is genuinely hard — library APIs change frequently, and Python version compatibility for Rust-compiled packages is a real operational concern. Third, the gap between "works in a demo" and "works reliably" is huge — the JSON extraction and validation work I did is invisible to the user but is what makes the system actually usable. Fourth, testing AI systems requires a different mindset — you mock the LLM and test the plumbing separately from testing the AI quality.

**What the interviewer is testing:** Are you genuinely learning from projects or just shipping demos?
**Possible follow-up:** What's the most important thing you'd teach a junior engineer starting their first AI project?

---

**Q5. How would you scale this for enterprise use?**
**A5.** Major changes in five areas. Infrastructure: PostgreSQL instead of SQLite, Redis for caching and job queuing, multiple FastAPI workers behind a load balancer, hosted vector DB. Authentication: JWT-based multi-user auth with role-based access control — managers can see all team meetings, contributors see only their own. Data isolation: every query filtered by user_id or team_id, encrypted storage at rest. Reliability: background job processing with retry logic, dead letter queues for failed summarisations, circuit breakers for external API calls. Compliance: audit logs for all data access, data retention policies, GDPR-compliant data deletion. The current architecture is designed so most of this is an extension, not a rewrite.

**What the interviewer is testing:** Can you think at enterprise scale? Do you know what enterprise requirements look like?
**Possible follow-up:** How would you price this as a SaaS product?

---

**Q6. How would you make this system more reliable?**
**A6.** Four levers. First, retries with exponential backoff for all external API calls — Groq, any future integrations. Second, circuit breakers — if Groq fails 5 times in a row, stop hammering it and return a meaningful error. Third, idempotent operations — every write has a unique ID, re-submitting the same meeting ID is a safe no-op. Fourth, health checks — the existing `/health` endpoint should check database connectivity and LLM API reachability, not just return 200. Fifth, structured error recovery — if summarisation fails, the meeting record stays in "uploaded" state, making it safe to retry without data corruption.

**What the interviewer is testing:** Do you understand reliability engineering principles?
**Possible follow-up:** What the SLA you'd commit to for a production version of this?

---

**Q7. How would you make this system more secure?**
**A7.** Authentication on every endpoint — currently all endpoints are open. Input sanitisation to mitigate prompt injection — strip or escape instruction-like patterns from transcripts before passing to prompts. API key rotation — secrets should have short TTLs and be rotatable without downtime. Rate limiting — prevent API abuse. Audit logging — log every data access with user ID and timestamp for compliance. Transport security — HTTPS everywhere, no HTTP in production. Secret management — no API keys in `.env` files in production; use AWS Secrets Manager, HashiCorp Vault, or Kubernetes secrets. Data encryption at rest for the SQLite file and ChromaDB directory.

**What the interviewer is testing:** Do you think about security systematically?
**Possible follow-up:** How would you detect if someone is probing your API with prompt injection attempts?

---

**Q8. [Tricky] An interviewer challenges: "This is just a wrapper around ChatGPT. What's technically impressive about it?"**
**A8.** Fair challenge — let me be specific about what's non-trivial. First, Observability & Tracing: We integrated LangSmith for real-time telemetry, recording prompt payloads, token throughput, chain latency, and Pydantic self-healing retries. Second, Codebase Intelligence: We built a Graphify AST Knowledge Graph (326 nodes, 547 edges) mapping dependencies between FastAPI routes, vector DB, and agents. Third, structured extraction with Pydantic validation: defensive parsing and single-pass retries ensure 100% typed output. Fourth, the RAG pipeline with dense vector search (ChromaDB + ONNX `all-MiniLM-L6-v2`), chunking strategy (`512/64`), source attribution, and confidence scoring. Fifth, the tool guardrail registry enforcing schema allowlisting before execution. Sixth, 37 automated tests covering all phases with LLM mocking.

**What the interviewer is testing:** Can you defend your work under pressure and articulate real technical value?
**Possible follow-up:** What would make this project genuinely defensible as senior-level work?
