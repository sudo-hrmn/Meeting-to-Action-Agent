"""
Phase 4 schemas — tool workflow request/response models.
"""
from typing import Any, Optional
from pydantic import BaseModel, Field


class ToolRunRequest(BaseModel):
    """Request to run a tool workflow on a meeting's action items."""
    tool_name: str = Field(
        ...,
        description="Tool to run: 'email_draft' | 'csv_export' | 'calendar_event'",
        examples=["email_draft"],
    )
    action_items: list[dict] = Field(
        ...,
        description="Action items to process (from meeting summary)",
    )
    meeting_title: Optional[str] = Field(
        None,
        description="Meeting title for context in generated output",
    )


class MeetingAutomateRequest(BaseModel):
    """Request to run a tool from a meeting — action_items are fetched from the DB."""
    tool_name: str = Field(
        ...,
        description="Tool to run: 'email_draft' | 'csv_export' | 'calendar_event'",
        examples=["email_draft"],
    )
    meeting_title: Optional[str] = Field(
        None,
        description="Override meeting title for generated output",
    )


class ToolRunResponse(BaseModel):
    """Response from a tool workflow execution."""
    tool: str = Field(..., description="Name of the tool that was run")
    status: str = Field(..., description="'success' | 'failed'")
    output: Any = Field(..., description="Tool output (string for email/CSV, list for calendar)")
    metadata: dict = Field(default_factory=dict, description="Tool execution metadata")
    error: Optional[str] = Field(None, description="Error message if tool failed")


class AvailableToolsResponse(BaseModel):
    """List of available tools with descriptions."""
    tools: dict[str, str]
    total: int
