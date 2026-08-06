"""
Tool-using workflows — Phase 4.

Safe tool calling with guardrails:
- All tools are pure functions (no real external I/O in MVP — safe mocks)
- Each tool validates its input before executing
- Tool results are always structured JSON
- A registry pattern makes it easy to add/remove tools without changing route logic

Tools available:
  - email_draft   : Generate email from action items
  - csv_export    : Export action items to CSV string
  - calendar_event: Generate calendar event JSON from deadlines
"""
import csv
import io
import json
from datetime import datetime, timezone
from typing import Any

from app.config.logging import get_logger

logger = get_logger(__name__)

# ─── Tool Registry ────────────────────────────────────────────────────────────

AVAILABLE_TOOLS = {
    "email_draft": "Generate a professional email draft from meeting action items",
    "csv_export": "Export action items as a CSV string (downloadable)",
    "calendar_event": "Generate calendar event JSON for action item deadlines",
}


class ToolValidationError(ValueError):
    """Raised when a tool receives invalid or unsafe input."""
    pass


def _validate_tool_name(tool_name: str) -> None:
    """Guardrail: reject unknown tool names before execution."""
    if tool_name not in AVAILABLE_TOOLS:
        raise ToolValidationError(
            f"Unknown tool: '{tool_name}'. "
            f"Available tools: {', '.join(AVAILABLE_TOOLS.keys())}"
        )


def _validate_action_items(action_items: list) -> None:
    """Guardrail: ensure action items are well-formed before processing."""
    if not isinstance(action_items, list):
        raise ToolValidationError("action_items must be a list")
    for i, item in enumerate(action_items):
        if not isinstance(item, dict):
            raise ToolValidationError(f"action_item[{i}] must be a dict")
        if "task" not in item:
            raise ToolValidationError(f"action_item[{i}] missing required field: 'task'")


# ─── Tool Implementations ─────────────────────────────────────────────────────

def tool_email_draft(action_items: list[dict], meeting_title: str = "Meeting") -> dict:
    """
    Generate a professional follow-up email from action items.

    Why a function (not an LLM call): Email templates are deterministic.
    Using string formatting is faster, cheaper, and more reliable than
    an LLM for this use case.
    """
    _validate_action_items(action_items)

    now = datetime.now(timezone.utc).strftime("%B %d, %Y")

    # Normalize priority — map any non-standard value to high / medium / low
    _PRIORITY_DISPLAY = {
        "high":   "🔴 High",
        "medium": "🟡 Medium",
        "low":    "🟢 Low",
    }

    def _normalize_priority(raw: str | None) -> str:
        if not raw:
            return "🟡 Medium"
        key = raw.strip().lower()
        # Map requirement-style values that leak from requirements extraction
        if key in ("must-have", "critical", "urgent"):
            return "🔴 High"
        if key in ("should-have", "nice-to-have", "optional"):
            return "🟢 Low"
        return _PRIORITY_DISPLAY.get(key, "🟡 Medium")

    lines = [
        f"Subject: Meeting Follow-Up: {meeting_title} — {now}",
        "",
        "Hi Team,",
        "",
        f"Please find below the agreed action items from our **{meeting_title}** meeting on {now}.",
        "Each owner is responsible for completing their task by the stated deadline.",
        "",
        "─" * 52,
        "  ACTION ITEMS",
        "─" * 52,
        "",
    ]

    for i, item in enumerate(action_items, 1):
        task     = item.get("task", "Unknown task")
        owner    = item.get("owner", "Unassigned")
        deadline = item.get("deadline", "TBD")
        priority = _normalize_priority(item.get("priority"))
        context  = item.get("context", "").strip()

        lines.append(f"  {i}.  {task}")
        lines.append(f"       👤  Owner:    {owner}")
        lines.append(f"       📅  Deadline: {deadline}")
        lines.append(f"       🎯  Priority: {priority}")
        if context:
            lines.append(f"       📝  Note:     {context}")
        lines.append("")

    lines += [
        "─" * 52,
        "",
        "Please reply to confirm you have seen your action item(s).",
        "If you foresee any blockers, flag them as early as possible.",
        "",
        "Best regards,",
        "[Your Name]",
    ]

    email_body = "\n".join(lines)
    logger.info(f"Email draft generated | action_items={len(action_items)}")

    return {
        "tool": "email_draft",
        "output": email_body,
        "metadata": {
            "action_item_count": len(action_items),
            "meeting_title": meeting_title,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    }



def tool_csv_export(action_items: list[dict]) -> dict:
    """
    Export action items as a CSV string.

    Why CSV: Universal format — works with Excel, Google Sheets, pandas.
    The CSV string can be returned to the frontend for direct download.
    """
    _validate_action_items(action_items)

    output = io.StringIO()
    fieldnames = ["#", "Task", "Owner", "Deadline", "Priority", "Context"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for i, item in enumerate(action_items, 1):
        writer.writerow({
            "#": i,
            "Task": item.get("task", ""),
            "Owner": item.get("owner", "Unassigned"),
            "Deadline": item.get("deadline", "TBD"),
            "Priority": item.get("priority", "medium"),
            "Context": item.get("context", ""),
        })

    csv_string = output.getvalue()
    logger.info(f"CSV export generated | rows={len(action_items)}")

    return {
        "tool": "csv_export",
        "output": csv_string,
        "metadata": {
            "row_count": len(action_items),
            "columns": fieldnames,
            "format": "text/csv",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    }


def tool_calendar_event(action_items: list[dict], meeting_title: str = "Follow-up") -> dict:
    """
    Generate Google Calendar-compatible event JSON for action item deadlines.

    Why JSON (not actual API call): Safe mock — no OAuth or external I/O.
    The output format matches the Google Calendar API schema so it can be
    directly used in a real integration later.
    """
    _validate_action_items(action_items)

    events = []
    for item in action_items:
        if item.get("deadline") and item["deadline"].lower() not in ("tbd", "not specified", ""):
            events.append({
                "summary": f"[Action] {item.get('task', 'Task')}",
                "description": (
                    f"Action item from: {meeting_title}\n"
                    f"Owner: {item.get('owner', 'Unassigned')}\n"
                    f"Priority: {item.get('priority', 'medium')}\n"
                    f"Context: {item.get('context', '')}"
                ),
                "start": {"date": item.get("deadline", "TBD"), "timeZone": "UTC"},
                "end": {"date": item.get("deadline", "TBD"), "timeZone": "UTC"},
                "attendees": [{"email": f"{item.get('owner', 'team').lower().replace(' ', '.')}@team.com"}],
                "reminders": {"useDefault": True},
            })

    logger.info(f"Calendar events generated | count={len(events)}")

    return {
        "tool": "calendar_event",
        "output": events,
        "metadata": {
            "event_count": len(events),
            "items_skipped": len(action_items) - len(events),
            "note": "Events with 'TBD' or unspecified deadlines are excluded.",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    }


# ─── Tool Dispatcher ─────────────────────────────────────────────────────────

def dispatch_tool(tool_name: str, action_items: list[dict], **kwargs: Any) -> dict:
    """
    Safe tool dispatcher — validates input then routes to the correct tool.

    Guardrail chain:
    1. Tool name must be in AVAILABLE_TOOLS (prevents injection of unknown operations)
    2. action_items must be a valid list of dicts with 'task' field
    3. Tool function handles its own internal validation

    This is the single entry point for all tool calls — centralised guardrails.
    """
    _validate_tool_name(tool_name)

    logger.info(f"Tool dispatch | tool={tool_name} | items={len(action_items)}")

    if tool_name == "email_draft":
        return tool_email_draft(action_items, kwargs.get("meeting_title", "Meeting"))
    elif tool_name == "csv_export":
        return tool_csv_export(action_items)
    elif tool_name == "calendar_event":
        return tool_calendar_event(action_items, kwargs.get("meeting_title", "Follow-up"))
    else:
        # This should never be reached due to _validate_tool_name, but defensive
        raise ToolValidationError(f"Tool '{tool_name}' has no implementation.")
