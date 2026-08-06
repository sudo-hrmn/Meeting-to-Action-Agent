# Section 6 — Backend / FastAPI Questions

---

**Q1. How did you structure your FastAPI endpoints?**
**A1.** I have three router groups: `/meetings` for transcript lifecycle (upload, summarise, get, list, report), `/documents` for RAG (ingest text, ingest file, ask question), and `/tools` for workflow automation (list tools, run tool, automate from meeting). Each router is a separate Python file under `app/routes/`. The routers are registered in `main.py` with `app.include_router()`. This keeps each domain's endpoints co-located and makes it easy to add or remove a feature without touching other parts of the codebase.

**What the interviewer is testing:** Do you understand FastAPI router organisation?
**Possible follow-up:** How would you add versioning — e.g., `/v1/meetings`?

---

**Q2. How does Pydantic validation work in your API?**
**A2.** FastAPI automatically validates all request bodies and response models using Pydantic. I define a Pydantic model for each request — for example, `MeetingUploadRequest` has a `transcript` field with `min_length=50`. If a request comes in with a shorter transcript, FastAPI returns a 422 Unprocessable Entity with a detailed error message before my code even runs. The same applies to response models — if my service returns a dict that doesn't match the declared response model, FastAPI raises an error at the response boundary. This gives me two layers of validation: input and output.

**What the interviewer is testing:** Do you know how Pydantic integrates with FastAPI?
**Possible follow-up:** What's the difference between a Pydantic model and a dataclass here?

---

**Q3. How do you handle errors in your API — what's your error response strategy?**
**A3.** All errors return structured JSON, never raw Python exceptions. Every route has a try/except block. Specific exceptions — like `ValueError` from the LLM returning invalid output — map to specific HTTP codes (422) with an `error` field and `message` field in the response body. Unexpected exceptions map to 500 with a generic message but detailed server-side logging. The principle is: the caller always gets actionable information (which field failed, what went wrong) and the server always logs the full context for debugging. I also fail fast at startup — if the Groq API key is missing, the app raises `RuntimeError` before accepting any requests.

**What the interviewer is testing:** Do you think about API consumers and operational debugging?
**Possible follow-up:** How would you add a request ID to correlate logs with API responses?

---

**Q4. Why is async important in your backend?**
**A4.** All expensive operations in my backend are I/O-bound: database queries, LLM API calls, file reads. With async, when one request is waiting for the LLM API response, the event loop can handle other incoming requests. With synchronous code, that waiting thread is blocked and can't serve other requests. Since LLM calls can take 5-20 seconds, this is significant. I use `async def` on all route handlers, `await` on all database calls (via aiosqlite), and `await` on all LangChain LLM calls (via `.ainvoke()`). The net effect is that the server can handle many concurrent requests with a single process.

**What the interviewer is testing:** Do you understand async I/O and when it matters?
**Possible follow-up:** Are there any parts of your code that block the event loop?

---

**Q5. How do you handle file uploads in FastAPI?**
**A5.** I use FastAPI's `UploadFile` type on the `POST /documents/ingest/file` endpoint. FastAPI handles multipart form data automatically when you declare an `UploadFile = File(...)` parameter. Inside the handler, I call `await file.read()` to get the raw bytes. For PDFs I use pypdf to extract text. For text/markdown I decode UTF-8. The key safety checks are: reject if content is empty after extraction, handle `UnicodeDecodeError` gracefully for binary files, and log the filename for traceability. I use `file.filename` for source attribution in ChromaDB metadata.

**What the interviewer is testing:** Do you know the FastAPI file upload pattern?
**Possible follow-up:** How would you add a file size limit to prevent memory exhaustion?

---

**Q6. [Advanced] What is dependency injection in FastAPI and do you use it?**
**A6.** FastAPI has a built-in dependency injection system using `Depends()`. You define a function that returns something — a database connection, the current user, a configuration object — and declare it as a parameter with `Depends(my_function)`. FastAPI calls it automatically and injects the result. In my current project I use it implicitly — `get_settings()` is cached with `lru_cache` and acts as a simple singleton dependency. If I were to add user authentication, I'd create a `get_current_user` dependency and inject it into protected routes. For testing, dependencies can be overridden with `app.dependency_overrides` — this is how you inject a mock database for testing.

**What the interviewer is testing:** Do you know FastAPI's DI system?
**Possible follow-up:** How would you override a dependency in tests?

---

**Q7. How did you configure CORS and why is it needed?**
**A7.** CORS — Cross-Origin Resource Sharing — is needed because my Streamlit frontend runs on port 8501 and the FastAPI backend runs on port 8000. Browsers block requests from one origin to another by default unless the server explicitly allows it. I added `CORSMiddleware` in `main.py` with `allow_origins=settings.allowed_origins`, `allow_methods=["*"]`, and `allow_credentials=True`. In development, `allowed_origins` is set to `["*"]` for convenience. In production, you'd lock this to the specific frontend domain. Streamlit makes HTTP requests from the server, not the browser, so technically CORS isn't required for Streamlit itself — but it's good practice and needed if you ever add a browser-side JS client.

**What the interviewer is testing:** Do you understand web security basics?
**Possible follow-up:** What other middleware would you add in production?
