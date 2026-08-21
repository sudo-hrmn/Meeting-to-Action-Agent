"""
Security module — Authentication, Rate Limiting, File Validation, and Security Headers.

Provides:
1. verify_api_key: Optional / Enforced X-API-Key header dependency for FastAPI.
2. SecurityHeadersMiddleware: Adds essential HTTP security headers (CSP, Frame-Options, Nosniff, STS, Referrer-Policy).
3. RateLimiterMiddleware: In-memory sliding window rate limiter to prevent DoS attacks.
4. Input & File Sanitization utilities.
"""
import time
import os
import re
from collections import defaultdict
from typing import Callable

from fastapi import Request, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse

from app.config.settings import get_settings
from app.config.logging import get_logger

logger = get_logger(__name__)

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


async def verify_api_key(api_key_header_val: str = Security(api_key_header)) -> str:
    """
    Validate API key from request header if API key enforcement is configured.
    
    If `API_KEY` setting is empty, auth is skipped (local dev mode).
    If `API_KEY` setting is populated, requests missing or providing an invalid key return 401.
    """
    settings = get_settings()
    configured_key = settings.api_key or os.getenv("API_KEY", "")

    if not configured_key:
        return "unauthenticated_dev_mode"

    if not api_key_header_val or api_key_header_val != configured_key:
        logger.warning(f"Unauthorized API key access attempt from client header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "unauthorized",
                "message": "Invalid or missing X-API-Key header.",
            },
        )
    return api_key_header_val


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds essential HTTP security headers to all server responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none';"
        return response


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Sliding window in-memory rate limiter middleware.
    Restricts requests per client IP to prevent DoS & API quota exhaustion.
    """

    def __init__(self, app, requests_per_minute: int = 120):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.client_records = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Exclude static docs and health check from rate limiting
        if request.url.path in ("/health", "/docs", "/redoc", "/openapi.json", "/"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - 60

        # Clean old timestamps outside 60s window
        timestamps = [t for t in self.client_records[client_ip] if t > window_start]
        self.client_records[client_ip] = timestamps

        if len(timestamps) >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for client_ip={client_ip} on path={request.url.path}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": f"Too many requests. Maximum {self.requests_per_minute} requests per minute allowed.",
                },
            )

        self.client_records[client_ip].append(now)
        return await call_next(request)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize uploaded filenames to prevent path traversal and metadata manipulation.
    Strips directory paths and special characters.
    """
    basename = os.path.basename(filename)
    clean_name = re.sub(r"[^\w\.\-]", "_", basename)
    return clean_name or "uploaded_file"
