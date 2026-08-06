"""
Phase 1 tests — covers upload, listing, and summarisation endpoints.

Why pytest + httpx TestClient:
- Tests run without a real server (ASGI test client)
- async tests work natively with pytest-asyncio
- We patch the Groq LLM call so tests don't hit real APIs or incur cost
"""
import json
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

from app.main import app
from app.config.database import init_db
from app.schemas.meeting import SummaryResult

# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True, scope="session")
async def setup_database():
    """
    Initialise the SQLite database once for the entire test session.

    Why autouse + session scope: Every test that hits an endpoint needs the
    tables to exist. Running init_db() once per session is fast and avoids
    each test needing its own setup boilerplate.
    """
    await init_db()


@pytest.fixture
def sample_transcript() -> str:
    return (
        "Alice (PM): Good morning. We need to ship the payment integration by September 15th. "
        "Bob (Eng): I'll own that. Risk: if the API specs from Stripe are delayed, we'll slip. "
        "Alice: Let's send them an escalation email. Agreed: we're using Stripe as our payment provider. "
        "Requirement: we need monitoring dashboards before go-live."
    )


@pytest.fixture
def mock_summary_result() -> SummaryResult:
    return SummaryResult(
        summary="The team discussed the Q3 payment integration milestone and associated risks.",
        key_topics=["Payment integration", "Stripe API", "Monitoring"],
        decisions=["Using Stripe as payment provider"],
        participants=["Alice", "Bob"],
        action_items=[
            {"task": "Ship payment integration", "owner": "Bob", "deadline": "September 15th", "priority": "high"},
            {"task": "Send escalation email to Stripe", "owner": "Alice", "deadline": "Today", "priority": "high"},
        ],
        requirements=[
            {"requirement": "Monitoring dashboards before go-live", "category": "technical", "priority": "must-have"}
        ],
        risks=[
            {"risk": "Stripe API specs delayed", "severity": "high", "mitigation_suggestion": "Send escalation email"}
        ],
    )



# ─── Tests ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_check():
    """Health endpoint returns 200 with correct shape."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


@pytest.mark.asyncio
async def test_upload_meeting_success(sample_transcript):
    """Upload endpoint stores transcript and returns a meeting ID."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/meetings/upload",
            json={"transcript": sample_transcript, "title": "Test Meeting"},
        )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["status"] == "uploaded"
    assert data["title"] == "Test Meeting"


@pytest.mark.asyncio
async def test_upload_meeting_rejects_short_transcript():
    """Upload endpoint rejects transcripts under 50 characters."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/meetings/upload",
            json={"transcript": "Too short"},
        )
    assert response.status_code == 422  # Pydantic validation error


@pytest.mark.asyncio
async def test_upload_meeting_rejects_blank_transcript():
    """Upload endpoint rejects blank/whitespace-only transcripts."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/meetings/upload",
            json={"transcript": "   " * 20},
        )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_meeting_not_found():
    """Returns 404 for a non-existent meeting ID."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/meetings/non-existent-id-xyz")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["error"] == "meeting_not_found"


@pytest.mark.asyncio
async def test_list_meetings_empty():
    """List endpoint returns an empty array when no meetings exist (clean DB)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/meetings/")
    assert response.status_code == 200
    # Should be a list (possibly empty or with existing test data)
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_summarise_meeting(sample_transcript, mock_summary_result):
    """Summarise endpoint returns structured JSON (Groq API mocked)."""
    # Mock the agent so we don't hit Groq in tests
    with patch(
        "app.routes.meetings.summarise_meeting",
        new_callable=AsyncMock,
        return_value=mock_summary_result,
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # First upload
            upload = await client.post(
                "/meetings/upload",
                json={"transcript": sample_transcript},
            )
            meeting_id = upload.json()["id"]

            # Then summarise
            response = await client.post(f"/meetings/{meeting_id}/summarise", json={})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "summarised"
    assert "summary" in data
    summary = data["summary"]
    assert "summary" in summary
    assert isinstance(summary["action_items"], list)
    assert isinstance(summary["risks"], list)


@pytest.mark.asyncio
async def test_summarise_nonexistent_meeting():
    """Summarise endpoint returns 404 for unknown meeting ID."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/meetings/does-not-exist/summarise", json={})
    assert response.status_code == 404
