"""
FastAPI application entry point — Meeting-to-Action Agent.

This file wires everything together:
- Creates the FastAPI app with metadata for auto-generated docs
- Registers all routers
- Initialises the database on startup
- Adds CORS middleware for Streamlit frontend
- Provides a health check endpoint

Design decision: Using lifespan context manager (not deprecated @app.on_event)
for startup/shutdown hooks as recommended by FastAPI since v0.93.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config.settings import get_settings
from app.config.logging import get_logger, setup_logging
from app.config.database import init_db
from app.agents.rag_agent import _get_collection
from app.routes.meetings import router as meetings_router
from app.routes.documents import router as documents_router
from app.routes.tools import router as tools_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan — runs setup on startup, teardown on shutdown.

    Why lifespan vs @app.on_event:
    - @app.on_event("startup") is deprecated since FastAPI 0.93
    - Lifespan context manager is the modern, recommended approach
    - Gives clean startup/shutdown symmetry
    """
    settings = get_settings()

    # ── Startup ──────────────────────────────────────────────────────────────
    setup_logging(log_level=settings.log_level, app_name="meeting-agent")
    logger = get_logger("meeting-agent.startup")

    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"LLM model: {settings.groq_model}")

    # Validate critical API keys on startup — fail fast rather than fail mid-request
    if not settings.groq_api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Add it to your .env file.\n"
            "Get a free key at: https://console.groq.com"
        )

    # Initialise database (creates tables if they don't exist)
    await init_db()

    # Pre-warm ChromaDB — downloads the ONNX embedding model once at startup
    # so the first document upload never hits a timeout waiting for the download.
    _get_collection()

    logger.info("Application startup complete ✓")

    yield  # App is running

    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("Application shutting down")


# ─── App Creation ─────────────────────────────────────────────────────────────

settings = get_settings()

app = FastAPI(
    title="Meeting-to-Action Agent",
    description=(
        "An AI system that transforms meeting transcripts into structured, actionable intelligence. "
        "Upload a transcript, get back summaries, action items, requirements, and risks — "
        "all as structured JSON.\n\n"
        "**Stack:** FastAPI · Groq (Llama 3) · LangChain · SQLite · FAISS\n\n"
        "**GitHub:** [Meeting-to-Action Agent](https://github.com/harman-singh/meeting-to-action-agent)"
    ),
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ─── Middleware ────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────

app.include_router(meetings_router)
app.include_router(documents_router)
app.include_router(tools_router)

# ─── Core Endpoints ───────────────────────────────────────────────────────────

@app.get(
    "/health",
    tags=["System"],
    summary="Health check",
    description="Returns the application health status. Used by load balancers and monitoring.",
)
async def health_check() -> JSONResponse:
    """Simple liveness probe — returns 200 if the app is running."""
    return JSONResponse(
        content={
            "status": "ok",
            "app": settings.app_name,
            "version": settings.app_version,
        }
    )


@app.get(
    "/",
    tags=["System"],
    summary="API root",
    include_in_schema=False,
)
async def root() -> JSONResponse:
    """Redirect hint for root path."""
    return JSONResponse(
        content={
            "message": "Meeting-to-Action Agent API",
            "docs": "/docs",
            "health": "/health",
        }
    )
