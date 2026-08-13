"""
Summarisation Agent — calls Groq LLM and returns structured meeting analysis.

Why this design:
- Prompt is loaded from a .txt file (not hardcoded) so we can iterate on it without
  touching Python code
- We use a strict JSON-only prompt and validate the output with Pydantic
- If JSON parsing fails we retry once with a correction prompt before raising
- LangChain wraps the Groq client so we can swap models or providers by changing config

Groq model used: llama-3.1-8b-instant (free tier, very fast)
"""
import json
import random
import re
from pathlib import Path
from typing import Optional

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

from app.config.settings import get_settings
from app.config.logging import get_logger
from app.schemas.meeting import SummaryResult

logger = get_logger(__name__)

SAMPLE_DOMAINS = [
    "AI Feature Integration & Roadmap",
    "Security Audit & Compliance Review",
    "Q4 Cloud Infrastructure & Migration",
    "Mobile App UI/UX Redesign",
    "Payment Gateway & Billing Escalation",
    "Customer Support Automation & Chatbot",
]

NAMES_POOL = [
    "Alex", "Jordan", "Priya", "Marcus", "Elena", "Liam", "Sophia", "Wei",
    "Fatima", "Carlos", "Hannah", "Rohan", "Maya", "Tariq", "Chloe", "Diego",
    "Sarah", "Vikram", "Nina", "David", "Amina", "Kiran", "Sam", "Olivia",
    "Lucas", "Zainab", "Mateo", "Ananya", "Julian", "Fatima"
]


async def generate_sample_transcript() -> dict[str, str]:
    """
    Generate a realistic, synthetic meeting transcript dynamically using LLM with random names.
    Returns a dict with 'title' and 'transcript'.
    """
    domain = random.choice(SAMPLE_DOMAINS)
    selected_names = random.sample(NAMES_POOL, 4)
    n1, n2, n3, n4 = selected_names
    names_str = f"{n1}, {n2}, {n3}, and {n4}"

    prompt = (
        f"Generate a raw, unscripted conversational meeting transcript between 4 team members named {names_str} discussing '{domain}'.\n\n"
        f"CRITICAL FORMAT RULES:\n"
        f"1. Output ONLY spoken dialogue lines using these exact names: '{n1} (PM): ...', '{n2} (Engineering): ...', '{n3} (Design): ...', '{n4} (Analyst): ...'.\n"
        f"2. DO NOT include headers, titles, 'Attendees', 'Action Items', 'Decisions', or summary bullet points at the end. NEVER format with Markdown headers or lists.\n"
        f"3. Make it sound like a real natural spoken conversation: casual phrasing ('yeah totally', 'hang on', 'quick check'), natural back-and-forth, and conversational flow.\n"
        f"4. Weave tasks, deadlines, decisions, and risks naturally into the spoken dialogue (e.g., '{n2}, can you take care of the auth API by Friday?' -> 'Yeah sure, I'll own that and push it before EOD Friday.').\n"
        f"5. Assign concrete action items to {names_str} with explicit deadlines ('by Friday EOD', 'tomorrow afternoon', 'September 15th').\n"
        f"6. Total length should be around 180-280 words.\n\n"
        f"Return ONLY raw dialogue using names {names_str}. No headers, no bullet points, no extra commentary."
    )
    llm = _get_llm()
    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        transcript_text = str(response.content).strip()
        # Post-processing clean-up: remove any leftover headers if LLM included them
        lines = [line for line in transcript_text.splitlines() if not line.startswith(("#", "**Attendees", "**Action Items", "**Meeting Transcript", "**Decisions", "- "))]
        transcript_text = "\n\n".join([l for l in lines if l.strip()])
    except Exception as e:
        logger.warning(f"Failed to generate dynamic transcript | fallback used | error={e}")
        transcript_text = (
            f"{n1} (PM): Hey everyone, let me share my screen real quick... okay, can everyone see the Q3 roadmap?\n\n"
            f"{n2} (Eng): Yeah we can see it. So on the backend side, auth is completely done. Payment integration is our main bottleneck right now — I'll take full ownership of that and aim to ship it before September 15th.\n\n"
            f"{n3} (UX): Quick check from design — payment flow wireframes are about 80% finished. I should have the final Figma components ready by Friday EOD. But one major risk though: if we don't get the updated Stripe API specs from vendor by Tuesday, that September deadline will slip.\n\n"
            f"{n4} (Analyst): Good point {n3}. Also, I'm working on the revenue projection model. I'll finalize the business case metrics and share the deck by September 1st.\n\n"
            f"{n1} (PM): Perfect. So we're officially deciding to move forward with Stripe. {n2}, let's make sure we track that vendor risk closely."
        )
    return {
        "title": f"{domain} Sync",
        "transcript": transcript_text,
    }


# Load prompt once at module import time
_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "summarise.txt"
_PROMPT_TEMPLATE: Optional[str] = None


def _load_prompt() -> str:
    """Load and cache the summarisation prompt from disk."""
    global _PROMPT_TEMPLATE
    if _PROMPT_TEMPLATE is None:
        _PROMPT_TEMPLATE = _PROMPT_PATH.read_text(encoding="utf-8")
        logger.info(f"Prompt loaded from: {_PROMPT_PATH}")
    return _PROMPT_TEMPLATE


def _extract_json(text: str) -> str:
    """
    Extract JSON from LLM output even if it wraps it in markdown code blocks.

    Some models ignore 'return ONLY JSON' instructions and wrap output in
    ```json ... ```. This strips that safely.
    """
    # Try to find JSON block in markdown fences
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return match.group(1)
    # Try to find raw JSON object
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group(0)
    return text


def _get_llm() -> ChatGroq:
    """Initialise the Groq LLM client with settings from config."""
    settings = get_settings()
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
    )


async def summarise_meeting(transcript: str, meeting_id: str) -> SummaryResult:
    """
    Analyse a meeting transcript and return structured extraction results.

    Steps:
    1. Build the prompt with the transcript injected
    2. Call Groq LLM
    3. Parse JSON from response
    4. Validate with Pydantic SummaryResult schema
    5. Return validated result

    Raises:
        ValueError: If the LLM response cannot be parsed as valid JSON after retry
        Exception: If the Groq API call fails
    """
    prompt_template = _load_prompt()
    prompt = prompt_template.replace("{transcript}", transcript)

    llm = _get_llm()

    logger.info(f"Calling Groq LLM | meeting_id={meeting_id} | model={get_settings().groq_model}")

    # Primary LLM call
    messages = [HumanMessage(content=prompt)]
    response = await llm.ainvoke(messages)
    raw_output = response.content

    logger.debug(f"LLM raw output | meeting_id={meeting_id} | length={len(raw_output)}")

    # Parse JSON from response
    try:
        json_str = _extract_json(raw_output)
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.warning(
            f"JSON parse failed on first attempt | meeting_id={meeting_id} | error={e}"
        )
        # Retry with explicit correction prompt
        correction_prompt = (
            f"The previous response was not valid JSON. "
            f"Here is what was returned:\n\n{raw_output}\n\n"
            f"Please return ONLY the corrected, valid JSON object. No explanation, no markdown."
        )
        retry_response = await llm.ainvoke([HumanMessage(content=correction_prompt)])
        try:
            json_str = _extract_json(retry_response.content)
            data = json.loads(json_str)
        except json.JSONDecodeError as retry_err:
            logger.error(
                f"JSON parse failed after retry | meeting_id={meeting_id} | error={retry_err}"
            )
            raise ValueError(
                f"LLM did not return valid JSON after retry. "
                f"Raw output: {retry_response.content[:200]}"
            )

    # Validate and coerce with Pydantic
    try:
        result = SummaryResult(**data)
    except Exception as validation_err:
        logger.error(
            f"Schema validation failed | meeting_id={meeting_id} | error={validation_err}"
        )
        # Build a partial result rather than failing completely
        result = SummaryResult(
            summary=data.get("summary", "Summary extraction failed."),
            key_topics=data.get("key_topics", []),
            decisions=data.get("decisions", []),
            participants=data.get("participants", []),
            action_items=data.get("action_items", []),
            requirements=data.get("requirements", []),
            risks=data.get("risks", []),
        )

    logger.info(
        f"Summarisation complete | meeting_id={meeting_id} | "
        f"topics={len(result.key_topics)} | actions={len(result.action_items)}"
    )
    return result
