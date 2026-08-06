"""
Extraction agents for Phase 2 — action items, requirements, and risks.

Why three separate agents (not one):
- Each agent has a focused, smaller prompt → better JSON output quality
- Failures in one don't block the others (they run independently)
- Easier to tune, test, and monitor each extraction type separately
- In production you could even run them in parallel (future optimisation)

All agents share the same Groq LLM client and JSON extraction utilities
from the base agent pattern established in Phase 1.
"""
import json
import re
from pathlib import Path
from typing import Optional

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

from app.config.settings import get_settings
from app.config.logging import get_logger

logger = get_logger(__name__)
_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

# Cache prompts at module load time
_prompt_cache: dict[str, str] = {}


def _load_prompt(name: str) -> str:
    """Load and cache a prompt file by name (without .txt extension)."""
    if name not in _prompt_cache:
        path = _PROMPTS_DIR / f"{name}.txt"
        _prompt_cache[name] = path.read_text(encoding="utf-8")
        logger.info(f"Prompt cached: {name}")
    return _prompt_cache[name]


def _get_llm() -> ChatGroq:
    """Return a configured Groq LLM instance."""
    s = get_settings()
    return ChatGroq(
        api_key=s.groq_api_key,
        model=s.groq_model,
        temperature=s.llm_temperature,
        max_tokens=s.llm_max_tokens,
    )


def _extract_json_array(text: str) -> list:
    """
    Extract a JSON array from LLM output, handling markdown code fences.
    Falls back to an empty list on parse failure (graceful degradation).
    """
    # Strip markdown fences
    match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
    if match:
        text = match.group(1)
    else:
        # Try to find raw array
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            text = match.group(0)

    try:
        result = json.loads(text)
        return result if isinstance(result, list) else []
    except json.JSONDecodeError:
        return []


async def _run_extraction(prompt_name: str, transcript: str, meeting_id: str) -> list:
    """
    Generic extraction runner — loads prompt, calls LLM, returns parsed list.
    Used by all three extraction agents below.
    """
    prompt_template = _load_prompt(prompt_name)
    prompt = prompt_template.replace("{transcript}", transcript)
    llm = _get_llm()

    logger.info(f"Running {prompt_name} extraction | meeting_id={meeting_id}")
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    result = _extract_json_array(response.content)
    logger.info(f"{prompt_name} extracted {len(result)} items | meeting_id={meeting_id}")
    return result


async def extract_action_items(transcript: str, meeting_id: str) -> list[dict]:
    """
    Extract action items from meeting transcript.

    Returns list of dicts with: task, owner, deadline, priority, context
    Returns empty list (not an error) if no action items are found.
    """
    return await _run_extraction("action_items", transcript, meeting_id)


async def extract_requirements(transcript: str, meeting_id: str) -> list[dict]:
    """
    Extract project requirements from meeting transcript.

    Returns list of dicts with: requirement, category, priority, source, rationale
    """
    return await _run_extraction("requirements", transcript, meeting_id)


async def extract_risks(transcript: str, meeting_id: str) -> list[dict]:
    """
    Extract risks and blockers from meeting transcript.

    Returns list of dicts with: risk, type, severity, probability, impact,
    mitigation_suggestion, owner
    """
    return await _run_extraction("risks", transcript, meeting_id)
