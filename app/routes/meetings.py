"""
Meeting routes — HTTP endpoints for the meeting workflow.

Route design principles:
- Routes only parse HTTP and delegate to services/agents
- All inputs validated by Pydantic before the function body runs
- All errors returned as structured JSON (never raw exceptions)
- Async throughout to avoid blocking the event loop
"""
import uuid
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from app.config.logging import get_logger
from app.schemas.meeting import (
    MeetingUploadRequest,
    MeetingUploadResponse,
    MeetingSummariseResponse,
    MeetingDetailResponse,
    MeetingListItem,
    ErrorResponse,
)
from app.services.meeting_service import (
    create_meeting,
    get_meeting,
    list_meetings,
    save_summary,
)
from app.agents.summarise_agent import summarise_meeting
from app.services.report_service import generate_report
from app.schemas.report import MeetingReportResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/meetings", tags=["Meetings"])


@router.post(
    "/upload",
    response_model=MeetingUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a meeting transcript",
    description=(
        "Upload raw meeting transcript text. Returns a meeting ID that can be used "
        "to trigger summarisation and retrieve results."
    ),
)
async def upload_meeting(request: MeetingUploadRequest) -> MeetingUploadResponse:
    """
    Store a new meeting transcript.

    - Validates the transcript is non-empty (≥50 chars)
    - Generates a UUID for the meeting
    - Persists to SQLite
    - Returns the meeting ID for subsequent calls
    """
    try:
        result = await create_meeting(request)
        return result
    except Exception as e:
        logger.error(f"Failed to upload meeting | error={e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "upload_failed", "message": str(e)},
        )


@router.post(
    "/{meeting_id}/summarise",
    response_model=MeetingSummariseResponse,
    summary="Analyse and summarise a meeting",
    description=(
        "Runs the AI agent on the uploaded transcript and returns structured JSON "
        "with summary, key topics, decisions, action items, requirements, and risks."
    ),
)
async def summarise_meeting_endpoint(meeting_id: str) -> MeetingSummariseResponse:
    """
    Trigger AI summarisation for a previously uploaded meeting.

    - Fetches the transcript from the database
    - Calls the Groq LLM agent
    - Saves the structured result
    - Returns the full structured analysis
    """
    # Verify meeting exists
    meeting = await get_meeting(meeting_id)
    if meeting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "meeting_not_found", "message": f"No meeting with id: {meeting_id}"},
        )

    try:
        # Run the AI agent
        summary_result = await summarise_meeting(
            transcript=meeting.transcript,
            meeting_id=meeting_id,
        )
        # Persist the result
        await save_summary(meeting_id, summary_result)

        return MeetingSummariseResponse(
            meeting_id=meeting_id,
            status="summarised",
            summary=summary_result,
        )

    except ValueError as e:
        logger.error(f"Agent returned invalid output | meeting_id={meeting_id} | error={e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "llm_output_invalid",
                "message": f"The AI agent did not return valid structured output: {str(e)}",
            },
        )
    except Exception as e:
        logger.error(f"Summarisation failed | meeting_id={meeting_id} | error={e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "summarisation_failed", "message": str(e)},
        )


@router.get(
    "/",
    response_model=list[MeetingListItem],
    summary="List all meetings",
    description="Returns all uploaded meetings ordered by most recent first.",
)
async def get_meetings() -> list[MeetingListItem]:
    """Return all meetings (lightweight list view)."""
    try:
        return await list_meetings()
    except Exception as e:
        logger.error(f"Failed to list meetings | error={e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "fetch_failed", "message": str(e)},
        )


@router.get(
    "/{meeting_id}",
    response_model=MeetingDetailResponse,
    summary="Get meeting details",
    description="Returns the full meeting record including transcript and summary if available.",
)
async def get_meeting_detail(meeting_id: str) -> MeetingDetailResponse:
    """Fetch full meeting details including summary."""
    meeting = await get_meeting(meeting_id)
    if meeting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "meeting_not_found", "message": f"No meeting with id: {meeting_id}"},
        )
    return meeting


@router.get(
    "/{meeting_id}/report",
    response_model=MeetingReportResponse,
    summary="Get full meeting report",
    description=(
        "Returns the full structured meeting report as both Markdown and JSON. "
        "The meeting must be summarised first via POST /meetings/{id}/summarise."
    ),
)
async def get_meeting_report(meeting_id: str) -> MeetingReportResponse:
    """
    Generate and return the full meeting report.

    Returns:
    - markdown: Complete, formatted Markdown report (shareable, Notion-ready)
    - json_data: Structured JSON with all extracted fields
    """
    report = await generate_report(meeting_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "meeting_not_found", "message": f"No meeting with id: {meeting_id}"},
        )
    return MeetingReportResponse(**report)
