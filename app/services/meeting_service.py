"""
Meeting service — all database operations for meetings.

Why a service layer:
- Routes stay thin (just parse HTTP, call service, return response)
- Business logic is testable without spinning up a web server
- SQLite queries are isolated here; swapping to Postgres later touches only this file
"""
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.config.database import get_db
from app.config.logging import get_logger
from app.schemas.meeting import (
    MeetingUploadRequest,
    MeetingUploadResponse,
    MeetingDetailResponse,
    MeetingListItem,
    SummaryResult,
)

logger = get_logger(__name__)


def _now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


async def create_meeting(request: MeetingUploadRequest) -> MeetingUploadResponse:
    """
    Persist a new meeting transcript to the database.

    Generates a UUID for the meeting ID so we never depend on auto-increment
    integers leaking information about total record count.
    """
    meeting_id = str(uuid.uuid4())
    now = _now_iso()

    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO meetings (id, title, transcript, status, created_at, updated_at)
            VALUES (?, ?, ?, 'uploaded', ?, ?)
            """,
            (meeting_id, request.title, request.transcript, now, now),
        )
        await db.commit()

    logger.info(f"Meeting created | id={meeting_id} | title={request.title!r}")

    return MeetingUploadResponse(
        id=meeting_id,
        title=request.title,
        status="uploaded",
        created_at=now,
        message="Transcript uploaded successfully. Use /meetings/{id}/summarise to analyse.",
    )


async def get_meeting(meeting_id: str) -> Optional[MeetingDetailResponse]:
    """
    Fetch a meeting by ID, including its summary if one exists.

    Returns None if not found (caller decides whether to raise 404).
    """
    async with get_db() as db:
        # Fetch meeting record
        cursor = await db.execute(
            "SELECT * FROM meetings WHERE id = ?", (meeting_id,)
        )
        row = await cursor.fetchone()

        if row is None:
            return None

        meeting = dict(row)

        # Fetch summary if available
        cursor = await db.execute(
            "SELECT * FROM meeting_summaries WHERE meeting_id = ?", (meeting_id,)
        )
        summary_row = await cursor.fetchone()
        summary = None

        if summary_row:
            s = dict(summary_row)
            summary = SummaryResult(
                summary=s.get("summary", ""),
                key_topics=json.loads(s.get("key_topics") or "[]"),
                decisions=json.loads(s.get("decisions") or "[]"),
                participants=json.loads(s.get("participants") or "[]"),
                action_items=json.loads(s.get("action_items") or "[]"),
                requirements=json.loads(s.get("requirements") or "[]"),
                risks=json.loads(s.get("risks") or "[]"),
            )

    return MeetingDetailResponse(
        id=meeting["id"],
        title=meeting.get("title"),
        transcript=meeting["transcript"],
        status=meeting["status"],
        created_at=meeting["created_at"],
        updated_at=meeting["updated_at"],
        summary=summary,
    )


async def list_meetings() -> list[MeetingListItem]:
    """Return all meetings ordered by most recent first."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id, title, status, created_at FROM meetings ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()

    return [
        MeetingListItem(
            id=row["id"],
            title=dict(row).get("title"),
            status=row["status"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


async def save_summary(meeting_id: str, result: SummaryResult) -> None:
    """
    Persist the LLM summary result and update meeting status.

    Uses INSERT OR REPLACE so re-summarising a meeting updates cleanly
    without a separate UPDATE + INSERT logic branch.
    """
    summary_id = str(uuid.uuid4())
    now = _now_iso()

    async with get_db() as db:
        await db.execute(
            """
            INSERT OR REPLACE INTO meeting_summaries
                (id, meeting_id, summary, key_topics, decisions, participants,
                 action_items, requirements, risks, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                summary_id,
                meeting_id,
                result.summary,
                json.dumps(result.key_topics),
                json.dumps(result.decisions),
                json.dumps(result.participants),
                json.dumps(result.action_items),
                json.dumps(result.requirements),
                json.dumps(result.risks),
                now,
            ),
        )
        # Update meeting status
        await db.execute(
            "UPDATE meetings SET status = 'summarised', updated_at = ? WHERE id = ?",
            (now, meeting_id),
        )
        await db.commit()

    logger.info(f"Summary saved | meeting_id={meeting_id}")
