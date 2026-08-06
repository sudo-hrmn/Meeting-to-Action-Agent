"""
Phase 4 tests — tool workflow guardrails and endpoints.
"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.config.database import init_db
from app.tools.workflow_tools import (
    dispatch_tool,
    tool_email_draft,
    tool_csv_export,
    tool_calendar_event,
    ToolValidationError,
    AVAILABLE_TOOLS,
)


@pytest.fixture(autouse=True, scope="session")
async def setup_database():
    await init_db()


@pytest.fixture
def sample_action_items():
    return [
        {"task": "Ship payment integration", "owner": "Bob",
         "deadline": "2026-09-15", "priority": "high", "context": "Core Q3 milestone"},
        {"task": "Send escalation email to Stripe", "owner": "Alice",
         "deadline": "2026-08-07", "priority": "high", "context": "Unblock API specs"},
        {"task": "Hire two backend engineers", "owner": "Alice",
         "deadline": "TBD", "priority": "medium", "context": "Team growth"},
    ]


# ─── Unit: Tool Guardrails ────────────────────────────────────────────────────

def test_dispatch_rejects_unknown_tool(sample_action_items):
    """Guardrail: unknown tool names are rejected before execution."""
    with pytest.raises(ToolValidationError, match="Unknown tool"):
        dispatch_tool("delete_everything", sample_action_items)


def test_dispatch_rejects_non_list_action_items():
    """Guardrail: action_items must be a list."""
    with pytest.raises(ToolValidationError, match="must be a list"):
        dispatch_tool("email_draft", "not a list")


def test_dispatch_rejects_missing_task_field():
    """Guardrail: each action item must have a 'task' field."""
    with pytest.raises(ToolValidationError, match="missing required field"):
        dispatch_tool("email_draft", [{"owner": "Bob"}])


# ─── Unit: Email Draft Tool ───────────────────────────────────────────────────

def test_email_draft_produces_correct_structure(sample_action_items):
    """Email draft contains subject, greeting, action items, and sign-off."""
    result = tool_email_draft(sample_action_items, "Q3 Planning")
    assert result["tool"] == "email_draft"
    assert "Subject:" in result["output"]
    assert "Q3 Planning" in result["output"]
    assert "Bob" in result["output"]
    assert "Ship payment integration" in result["output"]
    assert "metadata" in result


def test_email_draft_handles_empty_list():
    """Email draft with no action items still produces valid output."""
    result = tool_email_draft([], "Empty Meeting")
    assert result["tool"] == "email_draft"
    assert isinstance(result["output"], str)


# ─── Unit: CSV Export Tool ────────────────────────────────────────────────────

def test_csv_export_has_correct_headers(sample_action_items):
    """CSV includes standard column headers."""
    result = tool_csv_export(sample_action_items)
    assert result["tool"] == "csv_export"
    csv_output = result["output"]
    assert "#,Task,Owner,Deadline,Priority,Context" in csv_output


def test_csv_export_row_count(sample_action_items):
    """CSV has exactly one row per action item plus header."""
    result = tool_csv_export(sample_action_items)
    lines = [l for l in result["output"].strip().split("\n") if l]
    assert len(lines) == len(sample_action_items) + 1  # +1 for header


# ─── Unit: Calendar Event Tool ───────────────────────────────────────────────

def test_calendar_events_skip_tbd_deadlines(sample_action_items):
    """Items with TBD deadlines are excluded from calendar events."""
    result = tool_calendar_event(sample_action_items, "Q3 Planning")
    events = result["output"]
    # "TBD" item should be excluded
    for event in events:
        assert "TBD" not in event["start"]["date"]


def test_calendar_event_structure(sample_action_items):
    """Generated events have required Google Calendar fields."""
    result = tool_calendar_event(sample_action_items, "Q3 Planning")
    events = result["output"]
    assert len(events) >= 1
    for event in events:
        assert "summary" in event
        assert "start" in event
        assert "end" in event
        assert "attendees" in event


# ─── Integration: Tool API Endpoints ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_tools_endpoint():
    """GET /tools/ returns all available tools."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/tools/")
    assert response.status_code == 200
    data = response.json()
    assert "tools" in data
    assert "email_draft" in data["tools"]
    assert "csv_export" in data["tools"]
    assert "calendar_event" in data["tools"]


@pytest.mark.asyncio
async def test_run_tool_email_draft_endpoint(sample_action_items):
    """POST /tools/run with email_draft returns email output."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/tools/run",
            json={
                "tool_name": "email_draft",
                "action_items": sample_action_items,
                "meeting_title": "Q3 Planning",
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["tool"] == "email_draft"
    assert "Subject:" in data["output"]


@pytest.mark.asyncio
async def test_run_tool_csv_export_endpoint(sample_action_items):
    """POST /tools/run with csv_export returns CSV string."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/tools/run",
            json={"tool_name": "csv_export", "action_items": sample_action_items},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "Task" in data["output"]


@pytest.mark.asyncio
async def test_run_tool_rejects_unknown_tool(sample_action_items):
    """POST /tools/run with unknown tool returns 400."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/tools/run",
            json={"tool_name": "dangerous_tool", "action_items": sample_action_items},
        )
    assert response.status_code == 400
    assert "tool_validation_error" in response.json()["detail"]["error"]
