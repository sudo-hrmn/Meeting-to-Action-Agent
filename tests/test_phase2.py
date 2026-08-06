"""
Phase 2 tests — extraction agents and report endpoint.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

from app.main import app
from app.config.database import init_db
from app.schemas.meeting import SummaryResult
from app.agents.extraction_agents import _extract_json_array


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True, scope="session")
async def setup_database():
    await init_db()


@pytest.fixture
def sample_transcript() -> str:
    return (
        "Alice (PM): We need to ship the payment integration by September 15th. "
        "Bob (Eng): I'll own that. Risk: if the Stripe API specs are delayed, we'll slip. "
        "Alice: Let's send them an escalation email. Agreed: we're using Stripe. "
        "Requirement: we need monitoring dashboards before go-live. "
        "Alice: Also, Bob needs to hire two backend engineers by end of August."
    )


@pytest.fixture
def stored_meeting_with_summary(sample_transcript):
    """Returns a meeting_id after upload + mock summarise."""
    return sample_transcript


# ─── Unit Tests: JSON extraction utility ─────────────────────────────────────

def test_extract_json_array_plain():
    """Parses a plain JSON array string."""
    text = '[{"task": "Do something", "owner": "Alice"}]'
    result = _extract_json_array(text)
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["task"] == "Do something"


def test_extract_json_array_with_fences():
    """Parses JSON wrapped in markdown code fences."""
    text = '```json\n[{"task": "Deploy", "owner": "Bob"}]\n```'
    result = _extract_json_array(text)
    assert isinstance(result, list)
    assert result[0]["owner"] == "Bob"


def test_extract_json_array_empty():
    """Returns empty list for empty array."""
    result = _extract_json_array("[]")
    assert result == []


def test_extract_json_array_malformed():
    """Gracefully returns empty list for broken JSON."""
    result = _extract_json_array("this is not json at all")
    assert result == []


# ─── Integration Tests: Report endpoint ───────────────────────────────────────

@pytest.fixture
def mock_summary() -> SummaryResult:
    return SummaryResult(
        summary="Team agreed on Stripe integration due September 15th.",
        key_topics=["Payment integration", "Monitoring"],
        decisions=["Use Stripe as payment provider"],
        participants=["Alice", "Bob"],
        action_items=[
            {"task": "Ship payment integration", "owner": "Bob",
             "deadline": "September 15th", "priority": "high"},
        ],
        requirements=[
            {"requirement": "Monitoring dashboards before go-live",
             "category": "technical", "priority": "must-have"},
        ],
        risks=[
            {"risk": "Stripe API specs delay", "severity": "high",
             "mitigation_suggestion": "Send escalation email"},
        ],
    )


@pytest.mark.asyncio
async def test_report_returns_404_unknown_meeting():
    """Report endpoint returns 404 for unknown meeting."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/meetings/nonexistent-id/report")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_report_returns_not_summarised_if_no_summary(sample_transcript):
    """Report endpoint indicates meeting not yet summarised."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        upload = await client.post(
            "/meetings/upload",
            json={"transcript": sample_transcript, "title": "Phase 2 Test"}
        )
        meeting_id = upload.json()["id"]
        response = await client.get(f"/meetings/{meeting_id}/report")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "not_summarised"


@pytest.mark.asyncio
async def test_report_returns_markdown_and_json(sample_transcript, mock_summary):
    """Report endpoint returns both Markdown and JSON after summarisation."""
    with patch(
        "app.routes.meetings.summarise_meeting",
        new_callable=AsyncMock,
        return_value=mock_summary,
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            upload = await client.post(
                "/meetings/upload",
                json={"transcript": sample_transcript, "title": "Report Test Meeting"}
            )
            meeting_id = upload.json()["id"]

            # Summarise
            await client.post(f"/meetings/{meeting_id}/summarise", json={})

            # Get report
            response = await client.get(f"/meetings/{meeting_id}/report")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["markdown"] is not None
    assert "## 📋 Action Items" in data["markdown"]
    assert "## ⚠️ Risks" in data["markdown"]
    assert data["json_data"] is not None
    assert "action_items" in data["json_data"]
    assert "risks" in data["json_data"]
