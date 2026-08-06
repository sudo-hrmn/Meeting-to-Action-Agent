"""
Phase 2 schemas — report response models.
"""
from typing import Optional
from pydantic import BaseModel, Field

from app.schemas.meeting import SummaryResult


class MeetingReportResponse(BaseModel):
    """Full meeting report — both human-readable Markdown and machine-readable JSON."""

    meeting_id: str
    title: Optional[str] = None
    status: str = Field(..., description="'ready' | 'not_summarised'")
    markdown: Optional[str] = Field(None, description="Human-readable Markdown report")
    json_data: Optional[dict] = Field(None, description="Structured JSON data")
    error: Optional[str] = Field(None, description="Error message if report cannot be generated")
