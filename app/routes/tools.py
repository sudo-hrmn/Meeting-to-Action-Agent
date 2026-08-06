"""
Tool workflow routes — Phase 4 endpoints.
"""
from fastapi import APIRouter, HTTPException, status

from app.config.logging import get_logger
from app.schemas.tools import ToolRunRequest, ToolRunResponse, AvailableToolsResponse, MeetingAutomateRequest
from app.tools.workflow_tools import dispatch_tool, AVAILABLE_TOOLS, ToolValidationError
from app.services.meeting_service import get_meeting

logger = get_logger(__name__)
router = APIRouter(prefix="/tools", tags=["Tools — Workflow Automation"])


@router.get(
    "/",
    response_model=AvailableToolsResponse,
    summary="List available tools",
    description="Returns all tools available for automating post-meeting workflows.",
)
async def list_tools() -> AvailableToolsResponse:
    """Return the tool registry — what tools exist and what they do."""
    return AvailableToolsResponse(tools=AVAILABLE_TOOLS, total=len(AVAILABLE_TOOLS))


@router.post(
    "/run",
    response_model=ToolRunResponse,
    summary="Run a tool on action items",
    description=(
        "Run a workflow tool on a list of action items. "
        "Available tools: email_draft, csv_export, calendar_event."
    ),
)
async def run_tool(request: ToolRunRequest) -> ToolRunResponse:
    """
    Execute a workflow tool with guardrail validation.

    1. Tool name is validated against the registry
    2. Action items are validated for structure
    3. Tool is dispatched and result returned
    """
    try:
        result = dispatch_tool(
            tool_name=request.tool_name,
            action_items=request.action_items,
            meeting_title=request.meeting_title or "Meeting",
        )
        return ToolRunResponse(
            tool=result["tool"],
            status="success",
            output=result["output"],
            metadata=result.get("metadata", {}),
        )
    except ToolValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "tool_validation_error", "message": str(e)},
        )
    except Exception as e:
        logger.error(f"Tool execution failed | tool={request.tool_name} | error={e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "tool_failed", "message": str(e)},
        )


@router.post(
    "/meetings/{meeting_id}/automate",
    response_model=ToolRunResponse,
    summary="Automate workflows from a meeting",
    description=(
        "Run a tool directly on a meeting's action items. "
        "The meeting must be summarised first. "
        "Tool: email_draft | csv_export | calendar_event"
    ),
)
async def automate_from_meeting(meeting_id: str, request: MeetingAutomateRequest) -> ToolRunResponse:
    """
    Load action items from a summarised meeting and run a tool on them.

    Convenience endpoint — combines fetching action items + running tool.
    """
    meeting = await get_meeting(meeting_id)
    if meeting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "meeting_not_found", "message": f"No meeting with id: {meeting_id}"},
        )
    if meeting.summary is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "not_summarised",
                "message": "Meeting has not been summarised yet. Run POST /meetings/{id}/summarise first.",
            },
        )

    action_items = meeting.summary.action_items
    try:
        result = dispatch_tool(
            tool_name=request.tool_name,
            action_items=action_items,
            meeting_title=meeting.title or "Meeting",
        )
        return ToolRunResponse(
            tool=result["tool"],
            status="success",
            output=result["output"],
            metadata=result.get("metadata", {}),
        )
    except ToolValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "tool_validation_error", "message": str(e)},
        )
    except Exception as e:
        logger.error(f"Tool automation failed | meeting_id={meeting_id} | tool={request.tool_name}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "automation_failed", "message": str(e)},
        )
