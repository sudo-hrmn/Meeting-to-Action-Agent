"""
Pydantic schemas for Meeting-related request/response models.

Why Pydantic schemas:
- Input validation happens automatically before any business logic runs
- Response models ensure the API contract is explicit and documented
- FastAPI uses these directly to generate OpenAPI docs
- Separating schemas from DB models keeps the layers clean
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


# ─── Request Models ───────────────────────────────────────────────────────────

class MeetingUploadRequest(BaseModel):
    """Payload for uploading a raw meeting transcript."""

    transcript: str = Field(
        ...,
        min_length=50,
        description="Raw meeting transcript text (minimum 50 characters)",
        examples=["Alice: Let's start. Bob: We need to ship by Friday..."],
    )
    title: Optional[str] = Field(
        None,
        max_length=200,
        description="Optional meeting title",
        examples=["Q3 Planning Meeting"],
    )

    @field_validator("transcript")
    @classmethod
    def transcript_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Transcript cannot be blank or whitespace-only")
        return v.strip()


# ─── Response Models ──────────────────────────────────────────────────────────

class MeetingUploadResponse(BaseModel):
    """Returned after a successful transcript upload."""

    id: str = Field(..., description="Unique meeting identifier (UUID)")
    title: Optional[str] = Field(None, description="Meeting title if provided")
    status: str = Field(..., description="Current processing status")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    message: str = Field(..., description="Human-readable status message")


class SummaryResult(BaseModel):
    """Structured LLM output for a meeting summary."""

    summary: str = Field(..., description="Concise meeting summary (2-4 sentences)")
    key_topics: list[str] = Field(default_factory=list, description="Main topics discussed")
    decisions: list[str] = Field(default_factory=list, description="Decisions made in the meeting")
    participants: list[str] = Field(default_factory=list, description="People mentioned or present")
    action_items: list[dict] = Field(
        default_factory=list,
        description="Action items with task, owner, deadline, priority",
    )
    requirements: list[dict] = Field(
        default_factory=list,
        description="Requirements extracted with category and priority",
    )
    risks: list[dict] = Field(
        default_factory=list,
        description="Risks identified with severity and mitigation",
    )


class MeetingDetailResponse(BaseModel):
    """Full meeting record including summary if available."""

    id: str
    title: Optional[str]
    transcript: str
    status: str
    created_at: str
    updated_at: str
    summary: Optional[SummaryResult] = None


class MeetingSummariseResponse(BaseModel):
    """Response from the summarise endpoint."""

    meeting_id: str
    status: str
    summary: SummaryResult
    message: str = "Meeting summarised successfully"


class MeetingListItem(BaseModel):
    """Lightweight meeting record for list views."""

    id: str
    title: Optional[str]
    status: str
    created_at: str


class ErrorResponse(BaseModel):
    """Structured error response — never expose raw Python tracebacks."""

    error: str = Field(..., description="Error type/code")
    message: str = Field(..., description="Human-readable error description")
    request_id: Optional[str] = Field(None, description="Request trace ID for debugging")
