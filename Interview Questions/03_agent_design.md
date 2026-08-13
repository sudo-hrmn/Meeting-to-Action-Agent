# Section 3 — Agent Design Questions

---

**Q1. What is an AI agent, and how is your project an example of one?**
**A1.** An AI agent is a system that uses an LLM not just to answer questions, but to take actions — calling tools, making decisions, producing structured outputs, and interacting with external systems. In my project, each agent receives a transcript, applies a task-specific prompt, calls the LLM, extracts and validates the output, and returns a structured result. The workflow automation agents go further — they use tool calling to produce artifacts like emails and CSVs. The RAG agent retrieves relevant document chunks before calling the LLM, which is a form of grounded reasoning.

**What the interviewer is testing:** Do you understand what "agent" means technically vs. buzzword usage?
**Possible follow-up:** How would you make your agents stateful across multiple turns?

---

**Q2. How did you design your summarisation prompt, and what choices did you make?**
**A2.** The prompt is stored in a `.txt` file, not hardcoded in Python. This is intentional — it separates prompt engineering from code engineering and lets you iterate on prompts without touching the codebase. The prompt instructs the LLM to return valid JSON only, defines the exact schema with field names and types, provides an example output, and explicitly tells it not to invent information not in the transcript. I also instruct it to return empty arrays rather than null for list fields, which prevents downstream Pydantic validation errors.

**What the interviewer is testing:** Do you know how to write effective prompts?
**Possible follow-up:** How do you prevent the LLM from hallucinating action items that weren't mentioned?

---

**Q3. The LLM sometimes wraps JSON in markdown code fences like ```json. How do you handle that?**
**A3.** I use a regex extractor before attempting JSON parsing. The extractor first tries to strip markdown fences — it looks for ```` ```json ... ``` ```` patterns and extracts the content. If that doesn't match, it falls back to finding the first `{` and last `}` in the output. Only then does it call `json.loads()`. If that still fails, I raise a `ValueError` with the raw LLM output attached, which the route layer catches and returns as a 422 with a clear error message. This gives the caller actionable information rather than a cryptic 500.

**What the interviewer is testing:** Do you handle real LLM output quirks, or do you assume perfect output?
**Possible follow-up:** What would you add to make the retry logic smarter?

---

**Q4. How do you validate that the LLM output matches your expected schema?**
**A4.** After JSON extraction, I pass the dict directly to a Pydantic model constructor — `SummaryResult(**parsed_json)`. Pydantic validates field types, checks required fields are present, and applies any field-level validators. If validation fails, Pydantic raises a `ValidationError` with a detailed message about which fields failed. I catch that, log it with the raw LLM output for debugging, and return a 422 to the caller. The Pydantic model also has `default_factory=list` on all array fields, so even if the LLM omits them, the model still constructs successfully.

**What the interviewer is testing:** Do you use Pydantic properly, or just as a dict wrapper?
**Possible follow-up:** How would you handle a schema change — e.g., adding a new field — without breaking existing stored summaries?

---

**Q5. What are guardrails in the context of your tool calling system?**
**A5.** Guardrails are validation checks that run before any tool executes. In my system, every tool call goes through `dispatch_tool()` — a single entry point. It first checks the tool name against a registry of known tools; if it's not in the registry, it raises a `ToolValidationError` before any execution. Then it validates the `action_items` input — must be a list, each item must be a dict, each item must have a `task` field. Only if all checks pass does it route to the actual tool function. This prevents injection of unknown tool names and ensures tools receive well-formed inputs.

**What the interviewer is testing:** Do you know how to make AI tool calling safe?
**Possible follow-up:** What would you add to prevent a tool from being called too many times in a loop?

---

**Q6. [Advanced] How do you control hallucination in your extraction agents?**
**A6.** Three techniques. First, the prompt explicitly says "only extract information that is explicitly stated in the transcript — do not infer or fabricate." Second, for fields like `owner` and `deadline`, I instruct the model to use "Unassigned" or "TBD" when the value isn't clearly stated, rather than guessing. Third, for the RAG agent specifically, the prompt grounds the answer strictly in retrieved context: "answer ONLY based on the context provided below." The response schema also includes a `confidence` field — low confidence is a signal to flag the answer for human review rather than acting on it automatically.

**What the interviewer is testing:** Do you understand hallucination and how to mitigate it practically?
**Possible follow-up:** How would you measure your hallucination rate systematically?

---

**Q7. [Tricky] Why do you have separate prompt files per extraction task rather than one large prompt that does everything?**
**A7.** Three practical reasons. First, quality — focused prompts produce better outputs. When a single prompt asks for summary, action items, requirements, and risks simultaneously, the model spreads attention across all four tasks and tends to do all of them at medium quality. Separate prompts let each agent operate at peak quality for its specific task. Second, maintainability — if I want to improve risk extraction, I edit `risks.txt` without touching action item logic. Third, testability — I can write independent test cases for each extraction task.

**What the interviewer is testing:** Do you make intentional engineering decisions about prompts?
**Possible follow-up:** Wouldn't separate LLM calls be slower and more expensive?
