# Section 9 — Deployment & Production Readiness

---

**Q1. Is this project production-ready?**
**A1.** Honestly, it's production-style but not production-ready. The architecture follows production patterns: structured logging, typed config via Pydantic Settings, proper async, lifespan management, error handling with structured responses, and 37 tests. But several things would need to change for real production: SQLite → PostgreSQL for concurrent writes, synchronous summarisation → background job queue (Celery or FastAPI background tasks), single-user → multi-user with authentication, no monitoring → Prometheus metrics + alerting, local ChromaDB → hosted vector DB. I made intentional tradeoffs for a portfolio project — the patterns are production-quality even if the infrastructure isn't.

**What the interviewer is testing:** Do you know the difference between "production-pattern" and "production-ready"?
**Possible follow-up:** What would be the first three things you'd change before deploying this?

---

**Q2. How do you manage configuration and secrets in this project?**
**A2.** I use Pydantic's `BaseSettings` in `app/config/settings.py`. It automatically reads from environment variables and `.env` files via python-dotenv. The settings class defines typed fields for every config value — `groq_api_key: str`, `log_level: str = "INFO"`, `groq_model: str = "llama-3.1-8b-instant"`. The function is decorated with `@lru_cache()` so the settings object is loaded once and reused. The `.env` file is gitignored. I provide `.env.example` with all variables documented but no real values. In production, secrets would be injected via environment variables from a secrets manager like AWS Secrets Manager or HashiCorp Vault.

**What the interviewer is testing:** Do you understand proper config and secrets management?
**Possible follow-up:** Why use lru_cache on get_settings()? What's the risk?

---

**Q3. How does your logging work?**
**A3.** I use Python's standard `logging` module with a structured format: `{timestamp} | {level} | {logger_name} | {message}`. I have a `get_logger(__name__)` utility that all modules use to get a named logger. The log level is configurable via `LOG_LEVEL` environment variable — `INFO` in production, `DEBUG` for local development. Every meaningful event is logged: API key validation at startup, each database operation, each LLM call (with the meeting ID for correlation), tool dispatch, ChromaDB initialisation. I don't log sensitive content like transcripts or API responses — just event types and metadata.

**What the interviewer is testing:** Do you understand production logging practices?
**Possible follow-up:** How would you add request IDs to correlate logs across a request lifecycle?

---

**Q4. How would you deploy this to production?**
**A4.** For a small deployment: containerise with Docker, run with Gunicorn + Uvicorn workers (`gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 4`), deploy on a cloud VM (EC2, DigitalOcean Droplet) or a container service (ECS, Cloud Run). For the database, replace SQLite with a managed PostgreSQL (RDS, Supabase). For the vector store, use Pinecone or Weaviate instead of local ChromaDB. Put the FastAPI app behind an NGINX reverse proxy with HTTPS. Use environment variables for all secrets — no `.env` files in production. Add a health check endpoint (already done at `/health`) for load balancer probes.

**What the interviewer is testing:** Can you describe a realistic deployment path?
**Possible follow-up:** How would you do zero-downtime deployments?

---

**Q5. How would you control LLM API costs at scale?**
**A5.** Several strategies. First, caching — if the same transcript is submitted twice, return the cached result instead of calling Groq again. Use the transcript hash as the cache key. Second, model tiering — use a small fast model (llama-3.1-8b-instant) for all extraction, and only escalate to a larger model for complex reasoning. Third, rate limiting — limit API calls per user per day to prevent abuse. Fourth, chunk size optimisation — smaller, more precise prompts use fewer tokens. Fifth, async batch processing — instead of calling the LLM four times sequentially for summary + action items + requirements + risks, batch them or run them concurrently. Currently they're sequential which wastes wall-clock time.

**What the interviewer is testing:** Do you think about operational cost in AI systems?
**Possible follow-up:** How would you monitor your token usage per request?

---

**Q6. [Advanced] How would you add authentication to this API?**
**A6.** For simple API key auth: use FastAPI's `Depends()` with a custom `verify_api_key` dependency that reads the `Authorization: Bearer {key}` header and validates against a list of valid keys stored in the database or environment. For user-based auth: add JWT authentication using `python-jose` or `fastapi-users`. Each meeting would have a `user_id` foreign key, and queries would be filtered to the authenticated user's data. The dependency would decode the JWT, validate the signature, and inject the user object. This would need to be added to all routes that touch user-specific data.

**What the interviewer is testing:** Do you know how to add auth to a FastAPI app?
**Possible follow-up:** How would you handle token refresh?

---

**Q7. What monitoring would you add in production?**
**A7.** Three layers. First, application metrics via Prometheus: request count, request latency, error rate, LLM call latency, LLM token usage. Expose a `/metrics` endpoint with the `prometheus-fastapi-instrumentator` library. Second, structured logs shipped to a log aggregation service like Datadog, Loki, or CloudWatch — searchable by meeting_id, user_id, and error type. Third, alerting: alert if error rate exceeds 1%, if LLM API latency exceeds 30s, or if the health check fails. For AI-specific monitoring, I'd track extraction quality drift — if the average number of action items per meeting drops suddenly, the model or prompt may have regressed.

**What the interviewer is testing:** Do you know what production AI systems need for observability?
**Possible follow-up:** How would you detect that your RAG quality has degraded in production?
