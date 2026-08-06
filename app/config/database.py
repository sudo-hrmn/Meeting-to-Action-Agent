"""
Database configuration and connection management.

Why SQLite + aiosqlite:
- Zero setup for a portfolio project — no Docker, no Postgres install
- aiosqlite gives us async access that plays nicely with FastAPI's async event loop
- Sufficient for the scale of a meeting notes system
- Tables are created on startup so the app is self-initialising
"""
import aiosqlite
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from app.config.settings import get_settings
from app.config.logging import get_logger

logger = get_logger(__name__)
_DB_PATH = None


def get_db_path() -> str:
    """Resolve database file path from settings."""
    global _DB_PATH
    if _DB_PATH is None:
        _DB_PATH = get_settings().database_path
    return _DB_PATH


async def init_db() -> None:
    """
    Create all tables on application startup.

    Using IF NOT EXISTS means this is idempotent — safe to call on every restart
    without wiping data.
    """
    db_path = get_db_path()
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS meetings (
                id          TEXT PRIMARY KEY,
                title       TEXT,
                transcript  TEXT NOT NULL,
                status      TEXT NOT NULL DEFAULT 'uploaded',
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS meeting_summaries (
                id              TEXT PRIMARY KEY,
                meeting_id      TEXT NOT NULL UNIQUE,
                summary         TEXT,
                key_topics      TEXT,   -- JSON array stored as string
                decisions       TEXT,   -- JSON array stored as string
                participants    TEXT,   -- JSON array stored as string
                action_items    TEXT,   -- JSON array stored as string
                requirements    TEXT,   -- JSON array stored as string
                risks           TEXT,   -- JSON array stored as string
                raw_llm_output  TEXT,
                created_at      TEXT NOT NULL,
                FOREIGN KEY (meeting_id) REFERENCES meetings(id)
            )
        """)
        await db.commit()
    logger.info(f"Database initialised at: {db_path}")


@asynccontextmanager
async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """
    Async context manager for database connections.

    Usage:
        async with get_db() as db:
            await db.execute(...)

    Why context manager: ensures connections are always closed even if an
    exception occurs mid-query, preventing connection leaks.
    """
    db_path = get_db_path()
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row  # enables dict-style row access
        yield db
