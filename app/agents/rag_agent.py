"""
RAG pipeline using ChromaDB — document ingestion and retrieval-augmented Q&A.

Why ChromaDB instead of FAISS + sentence-transformers:
- ChromaDB bundles its own ONNX-based embedding model (all-MiniLM-L6-v2)
  via its default embedding function — no PyTorch, no separate install
- Persistent by default: data survives restarts automatically
- LangChain has a first-class ChromaDB integration
- Installs in seconds vs FAISS+sentence-transformers pulling ~700MB of PyTorch

Architecture:
  Document text → chunk → ChromaDB (embeds + stores internally)
  Question → ChromaDB similarity search → top-k chunks → Groq LLM → grounded answer
"""
import json
import re
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

from app.config.settings import get_settings
from app.config.logging import get_logger

logger = get_logger(__name__)

# ChromaDB persistence directory
CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "meeting_knowledge_base"

# Chunking settings
CHUNK_SIZE = 512
CHUNK_OVERLAP = 64
TOP_K_RESULTS = 4

# Module-level singletons — initialised once per process
_chroma_client: Optional[chromadb.PersistentClient] = None
_collection = None


def _get_collection():
    """
    Return the ChromaDB collection, creating client + collection on first call.

    Uses ChromaDB's default embedding function (ONNX all-MiniLM-L6-v2 internally)
    so we get consistent embeddings without any extra dependencies.
    """
    global _chroma_client, _collection

    if _collection is None:
        logger.info(f"Initialising ChromaDB at: {CHROMA_PATH}")
        _chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
        _collection = _chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=DefaultEmbeddingFunction(),
            metadata={"hnsw:space": "cosine"},  # cosine similarity for text
        )
        logger.info(f"ChromaDB collection ready | docs={_collection.count()}")

    return _collection


def _chunk_text(text: str) -> list[str]:
    """Split text into overlapping chunks using LangChain's splitter."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_text(text)


async def ingest_document(content: str, filename: str, doc_id: str) -> dict:
    """
    Chunk, embed, and store a document in ChromaDB.

    ChromaDB handles embedding automatically — we just pass text.
    Each chunk gets a unique ID derived from the doc_id + chunk index.
    """
    if not content.strip():
        raise ValueError("Document content is empty")

    chunks = _chunk_text(content)
    if not chunks:
        raise ValueError("Document produced no chunks after splitting")

    logger.info(f"Ingesting document | filename={filename} | chunks={len(chunks)}")

    collection = _get_collection()

    # Build parallel lists for ChromaDB batch add
    ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [
        {"source": filename, "doc_id": doc_id, "chunk_index": i}
        for i in range(len(chunks))
    ]

    # ChromaDB upsert is idempotent — re-ingesting the same doc_id updates it cleanly
    collection.upsert(documents=chunks, metadatas=metadatas, ids=ids)

    logger.info(f"Document ingested | filename={filename} | chunks={len(chunks)}")
    return {
        "doc_id": doc_id,
        "filename": filename,
        "chunks_created": len(chunks),
        "status": "ingested",
    }


def _extract_json_object(text: str) -> dict:
    """Extract a JSON object from LLM output, stripping markdown fences if present."""
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        text = match.group(1)
    else:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            text = match.group(0)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {
            "answer": text.strip(),
            "confidence": "low",
            "reasoning": "Could not parse structured response from LLM",
            "sources_used": [],
        }


async def answer_question(question: str) -> dict:
    """
    Retrieval-augmented question answering using ChromaDB + Groq.

    Steps:
    1. Query ChromaDB for top-k chunks similar to the question
    2. Build context string from retrieved chunks with source attribution
    3. Call Groq LLM with question + grounded context
    4. Parse structured JSON response
    5. Return answer with source references
    """
    collection = _get_collection()

    if collection.count() == 0:
        return {
            "answer": (
                "No documents have been ingested yet. "
                "Upload documents via POST /documents/ingest first."
            ),
            "confidence": "high",
            "reasoning": "Knowledge base is empty",
            "sources": [],
            "sources_used": [],
        }

    logger.info(f"RAG query | question={question[:80]!r}")

    # Similarity search
    results = collection.query(
        query_texts=[question],
        n_results=min(TOP_K_RESULTS, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    docs = results["documents"][0]
    metas = results["metadatas"][0]
    distances = results["distances"][0]

    if not docs:
        return {
            "answer": "No relevant information found in the knowledge base.",
            "confidence": "low",
            "reasoning": "Similarity search returned no results",
            "sources": [],
            "sources_used": [],
        }

    # Build context with source attribution
    context_parts = []
    source_refs = []
    for doc, meta, dist in zip(docs, metas, distances):
        source = meta.get("source", "Unknown")
        context_parts.append(f"[Source: {source}]\n{doc}")
        source_refs.append({
            "source": source,
            "excerpt": doc[:300],
            "relevance_score": round(float(dist), 4),
        })

    context = "\n\n---\n\n".join(context_parts)

    # Load prompt template
    prompt_path = Path(__file__).parent.parent / "prompts" / "rag_qa.txt"
    prompt_template = prompt_path.read_text(encoding="utf-8")
    prompt = prompt_template.replace("{context}", context).replace("{question}", question)

    # Call Groq LLM
    settings = get_settings()
    llm = ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=0.0,
        max_tokens=1024,
    )

    logger.info(f"Calling Groq for RAG answer | sources={len(source_refs)}")
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    result = _extract_json_object(response.content)
    result["sources"] = source_refs

    logger.info(f"RAG answer ready | confidence={result.get('confidence', 'unknown')}")
    return result
