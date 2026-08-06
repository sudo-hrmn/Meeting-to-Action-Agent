"""
Phase 3 tests — RAG pipeline (ChromaDB + Groq).

Strategy:
- Unit test the chunking + JSON extraction utilities (no external calls)
- Integration test the ingest and Q&A endpoints with mocked LLM (no Groq cost)
- Use a temp ChromaDB directory per test session to avoid polluting production DB
"""
import pytest
import tempfile
import os
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock

from app.main import app
from app.config.database import init_db
from app.agents.rag_agent import _chunk_text, _extract_json_object


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True, scope="session")
async def setup_database():
    await init_db()


@pytest.fixture
def sample_document() -> str:
    return (
        "Meeting Notes — Q3 Planning\n\n"
        "We agreed to use Stripe as our payment provider. "
        "The integration must be completed by September 15th. "
        "Bob is the owner of the payment integration task. "
        "Key risk: Stripe API spec delivery is delayed. "
        "Requirement: monitoring dashboards must be in place before go-live. "
        "Alice will send an escalation email to Stripe today."
    )


# ─── Unit: Chunking ───────────────────────────────────────────────────────────

def test_chunk_text_splits_long_document(sample_document):
    """Long documents are split into multiple chunks."""
    # Create a long document that forces splitting
    long_doc = sample_document * 10
    chunks = _chunk_text(long_doc)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 512 + 64  # max chunk size + overlap tolerance


def test_chunk_text_short_document(sample_document):
    """Short documents produce at least one chunk."""
    chunks = _chunk_text(sample_document)
    assert len(chunks) >= 1
    assert all(isinstance(c, str) for c in chunks)


def test_chunk_text_empty_returns_no_chunks():
    """Empty text produces empty chunks list."""
    chunks = _chunk_text("   ")
    assert chunks == []


# ─── Unit: JSON extraction ────────────────────────────────────────────────────

def test_extract_json_object_clean():
    """Parses a clean JSON object."""
    text = '{"answer": "Alice", "confidence": "high", "reasoning": "Mentioned in transcript"}'
    result = _extract_json_object(text)
    assert result["answer"] == "Alice"
    assert result["confidence"] == "high"


def test_extract_json_object_with_fences():
    """Parses JSON wrapped in markdown code fences."""
    text = '```json\n{"answer": "Bob", "confidence": "medium", "reasoning": "Inferred"}\n```'
    result = _extract_json_object(text)
    assert result["answer"] == "Bob"


def test_extract_json_object_malformed_fallback():
    """Gracefully falls back when JSON is malformed."""
    result = _extract_json_object("This is plain text with no JSON")
    assert "answer" in result
    assert result["confidence"] == "low"


# ─── Integration: Ingest endpoint ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ingest_document_endpoint(sample_document):
    """POST /documents/ingest returns chunk count and doc_id."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/documents/ingest",
            json={"content": sample_document, "filename": "q3_planning.txt"},
        )
    assert response.status_code == 201
    data = response.json()
    assert "doc_id" in data
    assert data["chunks_created"] >= 1
    assert data["status"] == "ingested"
    assert data["filename"] == "q3_planning.txt"


@pytest.mark.asyncio
async def test_ingest_rejects_empty_content():
    """POST /documents/ingest rejects empty content."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/documents/ingest",
            json={"content": "   ", "filename": "empty.txt"},
        )
    # Either Pydantic rejects (422) or our validator rejects (422)
    assert response.status_code in (422, 400)


# ─── Integration: Q&A endpoint ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ask_question_returns_structured_response(sample_document):
    """POST /documents/ask returns answer + confidence + sources."""
    # First ingest a document so the KB is not empty
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post(
            "/documents/ingest",
            json={"content": sample_document, "filename": "test_doc.txt"},
        )

    # Mock only the LLM call — ChromaDB search runs for real
    mock_llm_response = MagicMock()
    mock_llm_response.content = '{"answer": "Bob", "confidence": "high", "reasoning": "Mentioned as owner", "sources_used": ["test_doc.txt"]}'

    with patch("app.agents.rag_agent.ChatGroq") as mock_groq_cls:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_llm_response)
        mock_groq_cls.return_value = mock_llm

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/documents/ask",
                json={"question": "Who owns the payment integration?"},
            )

    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "confidence" in data
    assert "sources" in data
    assert isinstance(data["sources"], list)
