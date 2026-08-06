# Section 2 — Architecture Questions

---

**Q1. Walk me through the end-to-end architecture of your system.**
**A1.** The system has three layers. The frontend is a Streamlit app that communicates with the backend over HTTP. The backend is a FastAPI application with three router groups: `/meetings` for transcript management, `/documents` for RAG, and `/tools` for workflow automation. Each router delegates to a service or agent layer — routes only handle HTTP concerns, all business logic is in services and agents. Storage is SQLite for meeting records and summaries, and ChromaDB for vector embeddings. The AI layer uses LangChain to call Groq's Llama 3.1 API. At startup, FastAPI uses a lifespan context manager to initialise the database, validate API keys, and set up logging.

**What the interviewer is testing:** Can you describe a system end-to-end without getting lost in details?
**Possible follow-up:** Why did you put business logic in services rather than directly in routes?

---

**Q2. Why did you choose FastAPI over Flask or Django?**
**A2.** Three reasons. First, native async support — all my database calls and LLM calls are async, and FastAPI's async-first design means I'm not fighting the framework to do that. Flask requires extensions for async; Django's async support is newer and more complex. Second, automatic Pydantic integration — request bodies and response models are validated automatically just by type-annotating the function signatures. Third, auto-generated interactive docs at `/docs` — that's genuinely useful for a portfolio project and in production. Flask gives you none of this out of the box.

**What the interviewer is testing:** Do you understand why you chose your tools, or did you just follow a tutorial?
**Possible follow-up:** What's a situation where you'd choose Django over FastAPI?

---

**Q3. Why did you use Streamlit for the frontend instead of React or Vue?**
**A3.** For this project the frontend is a demo interface, not the core product. Streamlit lets me build a functional, attractive multi-tab UI in pure Python without switching context to JavaScript. Since I'm primarily a backend/AI engineer, that's the right tradeoff. If this were a customer-facing product with complex state, animations, or real-time updates, I'd use React. But for an AI portfolio project where the interesting work is in the backend, Streamlit is the right call.

**What the interviewer is testing:** Do you understand when to use simple tools vs complex ones?
**Possible follow-up:** What limitation would you hit first with Streamlit in production?

---

**Q4. How is your code organised, and why does the structure matter?**
**A4.** The project follows a layered architecture: routes → services → agents → config. Routes only parse HTTP requests and call services. Services handle database operations and business logic. Agents handle AI and external API calls. Config handles settings, logging, and database initialisation. This separation means I can test services without starting the HTTP server, mock agents without real API calls, and change the AI provider without touching route logic. It also makes the codebase readable — a new engineer knows exactly where to look for any piece of logic.

**What the interviewer is testing:** Do you understand separation of concerns?
**Possible follow-up:** How do you test the service layer in isolation?

---

**Q5. How does data flow when a user uploads a transcript and requests a summary?**
**A5.** The Streamlit frontend sends a POST to `/meetings/upload` with the transcript and title. FastAPI validates the request body via Pydantic — rejects if transcript is under 50 chars. The route calls `create_meeting()` in the service layer, which inserts a row into SQLite and returns a UUID. The frontend then sends POST to `/meetings/{id}/summarise`. The route fetches the meeting row, passes the transcript to `summarise_meeting()` in the agent layer. The agent constructs a prompt, calls Groq via LangChain, extracts JSON from the response using regex, validates it against the `SummaryResult` Pydantic model, and returns it. The route calls `save_summary()` to persist the result, then returns the full analysis to the frontend.

**What the interviewer is testing:** Can you trace data through a real system you built?
**Possible follow-up:** What happens if the LLM returns malformed JSON?

---

**Q6. [System Design] How would you redesign this for 10,000 users per day?**
**A6.** Several changes. First, replace SQLite with PostgreSQL — SQLite doesn't handle concurrent writes. Second, move summarisation to a background task queue (Celery + Redis or FastAPI background tasks) so the HTTP response is immediate and the user polls for results. Third, add a caching layer — if the same transcript is uploaded twice, detect the duplicate and return cached results. Fourth, replace ChromaDB with a hosted vector DB like Pinecone or Weaviate for horizontal scalability. Fifth, put the FastAPI app behind a load balancer with multiple workers (Gunicorn + Uvicorn workers). Sixth, add rate limiting per user to control LLM API costs.

**What the interviewer is testing:** Can you think beyond dev-mode architecture?
**Possible follow-up:** How would you handle LLM API rate limits at scale?

---

**Q7. [Advanced] Why did you use a lifespan context manager instead of @app.on_event("startup")?**
**A7.** `@app.on_event("startup")` is deprecated since FastAPI 0.93. The lifespan context manager is the modern replacement — it uses a single `async with` block to group startup and shutdown logic, which is cleaner and more Pythonic. It also gives you a guarantee that shutdown code runs even if startup raises an exception partway through. In my implementation, the lifespan validates the Groq API key, initialises the SQLite database, and sets up structured logging — all before the first request is accepted.

**What the interviewer is testing:** Are you using modern FastAPI patterns or copying outdated tutorials?
**Possible follow-up:** How would you handle a startup failure — e.g., the database can't be created?
