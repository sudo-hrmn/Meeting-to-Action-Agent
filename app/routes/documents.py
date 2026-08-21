"""
RAG routes — document ingestion and question answering endpoints.
"""
import uuid
from fastapi import APIRouter, HTTPException, status, UploadFile, File
from fastapi.responses import JSONResponse

from app.config.logging import get_logger
from app.schemas.rag import (
    DocumentIngestRequest,
    DocumentIngestResponse,
    QuestionRequest,
    QuestionAnswerResponse,
    SourceReference,
)
from app.agents.rag_agent import ingest_document, answer_question, get_ingested_sources

from fastapi import APIRouter, HTTPException, status, UploadFile, File, Depends
from app.config.security import verify_api_key

logger = get_logger(__name__)
router = APIRouter(prefix="/documents", tags=["RAG — Documents & Q&A"], dependencies=[Depends(verify_api_key)])


@router.get(
    "/sources",
    summary="List ingested document sources",
    description="Returns a list of unique document filenames present in the knowledge base.",
)
async def list_sources_endpoint() -> JSONResponse:
    """Return unique source filenames stored in ChromaDB."""
    sources = get_ingested_sources()
    return JSONResponse(content={"sources": sources, "count": len(sources)})



@router.post(
    "/ingest",
    response_model=DocumentIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a document into the knowledge base",
    description=(
        "Chunks, embeds (HuggingFace), and stores a document in the FAISS vector index. "
        "Documents can then be queried via POST /documents/ask."
    ),
)
async def ingest_document_endpoint(request: DocumentIngestRequest) -> DocumentIngestResponse:
    """
    Ingest a text document into the RAG knowledge base.

    - Splits document into overlapping chunks
    - Embeds with HuggingFace all-MiniLM-L6-v2
    - Stores in local FAISS index (persisted to disk)
    - Returns chunk count and document ID
    """
    doc_id = str(uuid.uuid4())
    try:
        result = await ingest_document(
            content=request.content,
            filename=request.filename,
            doc_id=doc_id,
        )
        return DocumentIngestResponse(
            **result,
            message=f"Document '{request.filename}' ingested successfully with {result['chunks_created']} chunks.",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "invalid_document", "message": str(e)},
        )
    except Exception as e:
        logger.error(f"Document ingestion failed | doc_id={doc_id} | error={e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "ingestion_failed", "message": str(e)},
        )


from app.config.security import sanitize_filename
from app.config.settings import get_settings

@router.post(
    "/ingest/file",
    response_model=DocumentIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest a file",
    description=(
        "Upload a .txt, .md, or .pdf file directly. "
        "The file will be read, chunked, embedded, and stored in ChromaDB."
    ),
)
async def ingest_file_endpoint(file: UploadFile = File(...)) -> DocumentIngestResponse:
    """
    Upload a file (TXT, Markdown, or PDF) and ingest it into the knowledge base.

    PDF files are parsed with pypdf; text/markdown are read directly.
    """
    settings = get_settings()
    doc_id = str(uuid.uuid4())
    raw_filename = file.filename or "uploaded_file"
    filename = sanitize_filename(raw_filename)

    try:
        raw = await file.read()
        max_bytes = settings.max_file_size_mb * 1024 * 1024
        if len(raw) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail={"error": "file_too_large", "message": f"File size exceeds maximum allowed limit of {settings.max_file_size_mb}MB."},
            )

        # PDF handling
        if filename.lower().endswith(".pdf"):
            import io
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(raw))
            content = "\n\n".join(page.extract_text() or "" for page in reader.pages)
        else:
            content = raw.decode("utf-8", errors="ignore")

        if not content.strip():
            raise ValueError("File appears to be empty or could not be read.")

        result = await ingest_document(content=content, filename=filename, doc_id=doc_id)
        return DocumentIngestResponse(
            **result,
            message=f"File '{filename}' uploaded and ingested with {result['chunks_created']} chunks.",
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "invalid_file", "message": str(e)},
        )
    except Exception as e:
        logger.error(f"File ingestion failed | filename={filename} | error={e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "file_ingestion_failed", "message": "An error occurred while processing the file."},
        )


@router.post(
    "/ask",
    response_model=QuestionAnswerResponse,
    summary="Ask a question against the knowledge base",
    description=(
        "Retrieves relevant document chunks from FAISS, then uses Groq LLM to generate "
        "a grounded answer with source attribution. Requires at least one document to be ingested first."
    ),
)
async def ask_question_endpoint(request: QuestionRequest) -> QuestionAnswerResponse:
    """
    Answer a question using retrieval-augmented generation.

    - Embeds the question
    - Retrieves top-4 similar chunks from FAISS
    - Calls Groq LLM with question + context
    - Returns answer with confidence level and source references
    """
    try:
        result = await answer_question(
            question=request.question,
            filename=request.filename,
            doc_id=request.doc_id,
        )
        sources = [
            SourceReference(
                source=s.get("source", "Unknown"),
                excerpt=s.get("excerpt", ""),
                relevance_score=s.get("relevance_score", 0.0),
            )
            for s in result.get("sources", [])
        ]
        return QuestionAnswerResponse(
            question=request.question,
            answer=result.get("answer", ""),
            confidence=result.get("confidence", "low"),
            reasoning=result.get("reasoning", ""),
            sources=sources,
            sources_used=result.get("sources_used", []),
        )
    except Exception as e:
        logger.error(f"RAG Q&A failed | question={request.question[:50]!r} | error={e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "qa_failed", "message": str(e)},
        )
