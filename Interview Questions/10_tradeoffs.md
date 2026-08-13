# Section 10 — Tradeoffs & Alternatives

---

**Q1. LangChain vs LangGraph — why did you use LangChain and not LangGraph?**
**A1.** LangGraph is designed for stateful, multi-step agent workflows with branching logic and cycles — like an agent that can call tools, observe results, decide to retry, then call different tools. My agents are all single-pass: input → prompt → LLM → parse → output. There's no branching, no cycles, no need to maintain agent state across steps. LangChain's `ChatGroq` and `HumanMessage` give me exactly what I need with far less complexity. I'd introduce LangGraph if I needed to build a multi-turn conversation agent or an agent that autonomously decides which extraction tasks to run based on transcript content.

**What the interviewer is testing:** Do you choose tools based on fit, not trends?
**Possible follow-up:** Can you describe a scenario where LangGraph would be necessary?

---

**Q2. ChromaDB vs FAISS vs Pinecone — how do they compare for this use case?**
**A2.** FAISS is a library — you manage everything: embeddings (needs separate model), serialisation, and loading. It's fastest for large-scale similarity search but has significant setup overhead. ChromaDB is a full vector database — it handles embeddings internally, persists automatically, and has a simple API. For a local portfolio project, ChromaDB is better than FAISS. Pinecone is a managed cloud vector database — no local storage, horizontally scalable, but costs money and requires an API key. For production at scale, Pinecone or Weaviate. For development and portfolio, ChromaDB. I initially planned FAISS but switched to ChromaDB when I realised sentence-transformers would pull 700MB of PyTorch.

**What the interviewer is testing:** Do you understand the tradeoffs across vector database options?
**Possible follow-up:** If you had 10 million documents to index, which would you choose?

---

**Q3. SQLite vs PostgreSQL — when does SQLite become the wrong choice?**
**A3.** SQLite is wrong when: (1) you have multiple concurrent writer processes — SQLite uses file-level locking, so multiple API workers would serialise all writes or corrupt data; (2) you need complex relational queries with joins across large tables; (3) you need full-text search, geospatial, or other PostgreSQL-specific features; (4) you need point-in-time recovery or replication. For this project, a single uvicorn process with sequential writes is fine. The moment I add multiple workers (`--workers 4`) or deploy with Gunicorn, I need PostgreSQL.

**What the interviewer is testing:** Do you know the actual limits of SQLite?
**Possible follow-up:** How would you detect database write conflicts in production?

---

**Q4. Local LLM (Ollama) vs API LLM (Groq) — what are the tradeoffs?**
**A4.** Local LLM via Ollama: completely free, no internet dependency, full data privacy, but requires a machine with 8-16GB RAM minimum, slower inference on CPU, and you're responsible for model updates. Groq API: free tier available, extremely fast (they use custom LPU hardware), simple to set up, but requires internet and API key. I chose Groq because: it's free enough for a portfolio project, setup is one `pip install` and an API key, and inference speed is excellent (under 5 seconds). For a privacy-sensitive enterprise deployment where data can't leave the premises, Ollama with a quantised Llama 3 model is the right answer.

**What the interviewer is testing:** Can you reason about build-vs-buy and privacy tradeoffs in LLM?
**Possible follow-up:** How would you switch from Groq to Ollama with minimal code changes?

---

**Q5. Single agent vs multi-agent — why did you use separate agents for each extraction task?**
**A5.** I use what I'd call a "specialist pattern" — one focused agent per extraction type, each with its own prompt file. This isn't a true multi-agent system (no agent-to-agent communication or orchestration), but each agent operates independently. The alternative is one "super prompt" that extracts everything simultaneously. I chose specialist agents because: extraction quality is higher (focused context window), each agent is independently testable, you can retune one without affecting others, and you can run them in parallel if needed. The cost is more LLM calls — but with Groq's free tier and fast inference, that's acceptable.

**What the interviewer is testing:** Do you understand agent decomposition patterns?
**Possible follow-up:** How would you orchestrate these agents if one agent's output feeds another?

---

**Q6. Prompt engineering vs fine-tuning — which approach did you choose and why?**
**A6.** Prompt engineering entirely. Fine-tuning was not the right choice here for several reasons: it requires a labelled training dataset (I don't have hundreds of annotated meeting transcripts), it's expensive to run, and it would lock me to a specific model version. Prompt engineering with a strong base model like Llama 3.1 gives excellent results for structured extraction tasks. The model already understands concepts like "action items," "owners," and "deadlines" from pre-training. I just need to tell it the output format and constraints. If extraction quality were consistently poor despite prompt tuning, fine-tuning with a small domain-specific dataset would be the next step.

**What the interviewer is testing:** Do you understand when fine-tuning is and isn't appropriate?
**Possible follow-up:** What would your fine-tuning training data look like for this task?

---

**Q7. Structured output (JSON) vs free-form text output — why enforce structure?**
**A7.** Free-form text output is not programmable. If the LLM returns "Bob should handle the payment integration by September," I can't reliably extract the owner, task, and deadline into structured fields without another LLM call. Structured JSON output lets me directly map to Pydantic models, store in the database with typed fields, display in the UI with proper formatting, and pass into tools (email, CSV, calendar) without parsing. The tradeoff is that JSON validation adds complexity and can fail if the LLM deviates from the schema. I mitigate this with a robust JSON extractor and Pydantic validation with sensible defaults.

**What the interviewer is testing:** Do you understand why structured output matters for agentic systems?
**Possible follow-up:** How would you handle a case where strict JSON parsing consistently fails for a specific type of transcript?
