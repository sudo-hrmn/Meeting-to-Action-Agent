"""
Schemas for RAG document ingestion and question answering.
"""
import uuid
from typing import Optional
from pydantic import BaseModel, Field


class DocumentIngestRequest(BaseModel):
    """Request to ingest a text document into the knowledge base."""
    content: str = Field(..., min_length=20, max_length=500000, description="Document text content")
    filename: str = Field(..., min_length=1, max_length=255, description="Document filename for attribution")


class DocumentIngestResponse(BaseModel):
    """Response after successful document ingestion."""
    doc_id: str
    filename: str
    chunks_created: int
    status: str
    message: str


class QuestionRequest(BaseModel):
    """Request to ask a question against the knowledge base."""
    question: str = Field(..., min_length=3, max_length=2000, description="Question to answer from the knowledge base")
    filename: Optional[str] = Field(default=None, description="Optional document filename to restrict search scope")
    doc_id: Optional[str] = Field(default=None, description="Optional document ID to restrict search scope")



class SourceReference(BaseModel):
    """A retrieved source chunk with relevance score."""
    source: str = Field(..., description="Source document filename")
    excerpt: str = Field(..., description="Relevant excerpt from the source")
    relevance_score: float = Field(..., description="Similarity score (lower = more similar in FAISS)")


class QuestionAnswerResponse(BaseModel):
    """Response from the RAG Q&A system."""
    question: str
    answer: str
    confidence: str = Field(..., description="high | medium | low")
    reasoning: str = Field(..., description="How the answer was derived from sources")
    sources: list[SourceReference] = Field(default_factory=list)
    sources_used: list[str] = Field(default_factory=list)
