# Section 8 — Evaluation & Testing Questions

---

**Q1. How do you test an AI system — the output is non-deterministic?**
**A1.** You mock the LLM for unit and integration tests, and test the real LLM separately in evaluation suites. In my test suite, I patch `summarise_meeting` with `AsyncMock` that returns a fixed `SummaryResult` object. This makes tests fast, free (no API calls), and deterministic. What I'm actually testing is: does the route correctly call the service, does the service correctly persist the result, does the response model serialise correctly. LLM output quality is tested separately with a curated set of test transcripts and expected outputs, evaluated manually or with an LLM-as-judge approach.

**What the interviewer is testing:** Do you know how to test AI systems without being blocked by non-determinism?
**Possible follow-up:** How would you detect if a model update degraded your extraction quality?

---

**Q2. Walk me through your test suite — what does it cover?**
**A2.** I have 37 tests across 4 files. `test_phase1.py` covers the core API: health check, upload with valid/invalid transcripts, 404 for unknown meeting, list endpoint, summarise with mocked LLM, summarise non-existent meeting. `test_phase2.py` covers JSON extraction utility (valid, fenced, empty, malformed), report endpoint (404, not summarised, full report with Markdown + JSON). `test_phase3.py` covers chunking utilities, JSON object extraction, ingest endpoint, and Q&A endpoint with mocked LLM. `test_phase4.py` covers tool guardrails (unknown tool, non-list input, missing task field), each tool's output, and API endpoint integration tests.

**What the interviewer is testing:** Can you explain your test coverage concisely?
**Possible follow-up:** What's not tested that should be?

---

**Q3. How do you test that the JSON extraction utility handles malformed LLM output?**
**A3.** I have specific unit tests for the `_extract_json_array` and `_extract_json_object` utility functions. Each test passes a different input variant: a clean JSON string, a JSON string wrapped in markdown fences, an empty array, and a completely malformed non-JSON string. The last case tests graceful degradation — the function should return an empty list or a fallback dict rather than raising an unhandled exception. This is critical because LLM output is unpredictable and you can never guarantee it will be valid JSON.

**What the interviewer is testing:** Do you test edge cases, not just happy paths?
**Possible follow-up:** How would you add a test for a partial JSON response?

---

**Q4. How do you measure hallucination in your extraction pipeline?**
**A4.** I don't have automated hallucination measurement in this MVP — that's a known gap. The mitigation is in the prompt design (instructing the model not to fabricate) and in the output schema (using "TBD" and "Unassigned" as sentinel values). For a production system, I would build an evaluation harness: take 20-30 carefully labelled test transcripts with ground-truth action items, run the extraction pipeline on all of them, and measure precision and recall — how many extracted items are actually in the transcript, and how many real items were missed. You could also use an LLM-as-judge with a verification prompt.

**What the interviewer is testing:** Do you understand evaluation methodology for AI systems?
**Possible follow-up:** What's the difference between precision and recall in this context?

---

**Q5. How do you test the RAG pipeline without making real LLM calls?**
**A5.** I split the RAG tests into two parts. The utility functions — `_chunk_text` and `_extract_json_object` — are pure Python and tested with unit tests, no mocking needed. For the endpoint integration test, I let ChromaDB run for real (it's fast and local), but mock only the Groq LLM call using `patch("app.agents.rag_agent.ChatGroq")` and returning a fixed response. This means I'm actually testing: does ingestion create chunks in ChromaDB, does similarity search return results, does the prompt get built correctly, does the response model validate. The LLM's generation quality is not tested in this suite.

**What the interviewer is testing:** Do you know how to mock at the right level of abstraction?
**Possible follow-up:** How would you test that your RAG prompt template is being filled correctly?

---

**Q6. [Advanced] What would a proper evaluation set for your extraction agent look like?**
**A6.** A good evaluation set would have: 20-30 diverse meeting transcripts covering different meeting types (planning, retrospective, incident review, sales call), different quality levels (clean notes, messy informal speech, short vs long), and different edge cases (no action items, all action items, ambiguous owners, multiple people sharing one task). For each transcript, I'd create ground-truth labels: the exact list of action items a human expert would extract. Then I'd measure: precision (did the model extract things that are actually action items?), recall (did it miss any real action items?), and field accuracy (did it get the owner and deadline right?).

**What the interviewer is testing:** Do you understand how to build ground-truth evaluation for extraction tasks?
**Possible follow-up:** How would you handle inter-annotator disagreement — two humans labelling differently?

---

**Q7. What's not covered in your current test suite?**
**A7.** Honest answer: several things. No end-to-end test with a real LLM call — all LLM calls are mocked. No load testing — I haven't tested concurrent requests. No test for the Streamlit frontend. No test for the ChromaDB persistence — I don't verify that data survives a process restart. No adversarial tests — transcripts designed to confuse the extraction agent. No evaluation harness with labelled ground truth. These are all known gaps that I'd address in a production hardening phase. The current test suite validates the plumbing — the API contracts, the business logic, and the tool guardrails — which is the most important layer.

**What the interviewer is testing:** Are you honest about limitations? Do you know what good coverage looks like?
**Possible follow-up:** If you had one week to improve test coverage, what would you add first?
