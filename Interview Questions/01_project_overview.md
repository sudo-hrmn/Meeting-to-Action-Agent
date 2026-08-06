# Section 1 — Project Overview Questions

---

**Q1. Tell me about your Meeting-to-Action Agent project.**
**A1.** It's an AI system that solves a very real problem: most meetings generate no structured output. People walk out with vague notes and forget who owns what. My project takes a raw transcript — from Zoom, Teams, or manual notes — and in under 30 seconds extracts a structured JSON with the summary, key decisions, action items with owners and deadlines, requirements, and risks. It also has a document Q&A layer using RAG and a tool layer that can generate follow-up emails, CSV exports, and calendar events. The backend is FastAPI, the LLM is Groq Llama 3.1, storage is SQLite, and the vector store is ChromaDB.

**What the interviewer is testing:** Can you explain a technical project clearly to a non-technical person? Do you understand what problem you solved?
**Possible follow-up:** How is this different from just asking ChatGPT to summarise a meeting?

---

**Q2. How is this different from just pasting the transcript into ChatGPT?**
**A2.** Three main differences. First, persistence — every transcript is stored in a database with its analysis. ChatGPT has no memory across sessions. Second, structured outputs — I enforce a strict JSON schema. ChatGPT returns free-form text; you can't programmatically parse that into downstream tools. Third, automation — once the analysis is done, the system can automatically generate follow-up emails, CSV exports, or calendar events. It's a pipeline, not a one-shot prompt. And the RAG layer means you can ask questions against your own internal documents, not just the current transcript.

**What the interviewer is testing:** Do you understand the difference between a chatbot and an agentic system?
**Possible follow-up:** What would you add to make it actually better than ChatGPT?

---

**Q3. Who are the target users of this system?**
**A3.** Primarily product managers, engineering leads, and project managers — anyone who runs recurring meetings and needs to track commitments. In an enterprise context, it could be used by ops teams who manage many meetings per week and need a structured audit trail of decisions and action items. For a smaller team, it saves 30 minutes of manual note cleanup after every meeting.

**What the interviewer is testing:** Can you think about real users, not just the tech?
**Possible follow-up:** How would you validate that users actually find this useful?

---

**Q4. What is the MVP scope of this project?**
**A4.** The MVP covers four things: transcript upload with SQLite persistence, AI summarisation with structured JSON output, a RAG layer for document Q&A, and three workflow tools — email draft, CSV export, and calendar event generation. I deliberately excluded things like real-time transcription, OAuth integrations, and multi-user support. Those are Phase 6+ features. The MVP tests the core AI pipeline and validates that structured extraction actually works reliably.

**What the interviewer is testing:** Can you scope a project realistically? Do you understand MVP vs full product?
**Possible follow-up:** What's the first feature you would add after MVP?

---

**Q5. What would you add in a future version of this project?**
**A5.** Several things. First, real integrations — a Zoom webhook that auto-sends new transcripts to the upload endpoint, or a Google Meet API connector. Second, multi-user support with authentication — right now it's single-user. Third, a speaker diarisation layer so action items are automatically attributed to the right person by voice. Fourth, a proper evaluation framework that scores extraction quality against labelled test sets. Fifth, async background processing — right now summarisation blocks the HTTP request; in production that should be a background task with a job status endpoint.

**What the interviewer is testing:** Do you think beyond MVP? Can you prioritise features?
**Possible follow-up:** How would you handle multi-user data isolation?

---

**Q6. How is this different from a simple chatbot?**
**A6.** A chatbot answers questions in a conversational loop. This system is a structured extraction pipeline with multiple specialised agents. It doesn't chat — it analyses, extracts, validates, stores, and automates. The output isn't a free-form response; it's a typed Pydantic model with validated fields. And it takes action: it writes to a database, generates files, and can trigger downstream workflows. That's the difference between a chatbot and an agentic AI system.

**What the interviewer is testing:** Do you know what "agentic" means in practice?
**Possible follow-up:** Can you explain what makes an AI system "agentic"?

---

**Q7. [Tricky] If the LLM already extracts action items, why do you need separate extraction agents for action items, requirements, and risks?**
**A7.** Great question. You could do it in one prompt, but in practice focused prompts outperform mega-prompts. Each extraction agent has a prompt that's tuned specifically for its task — the action item prompt emphasises owner attribution and deadline inference; the risk prompt emphasises severity classification and mitigation. When you combine them into one prompt, the model tries to do too much at once and quality drops — especially for the minority categories like risks, which get underweighted. Separate agents also let you tune, test, and monitor each extraction type independently.

**What the interviewer is testing:** Do you understand prompt engineering tradeoffs?
**Possible follow-up:** How do you measure which approach produces better output?
