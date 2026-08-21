"""
Security unit tests for API key auth, security headers, rate limiting, and sanitization.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config.settings import get_settings
from app.config.security import sanitize_filename


def test_security_headers_present():
    """Verify security headers are injected in HTTP responses."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-XSS-Protection") == "1; mode=block"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


def test_sanitize_filename():
    """Verify filename path traversal and unsafe character stripping."""
    assert sanitize_filename("../../etc/passwd.txt") == "passwd.txt"
    assert sanitize_filename("my<file>?name.pdf") == "my_file__name.pdf"
    assert sanitize_filename("normal_doc.md") == "normal_doc.md"


def test_api_key_auth_enforcement(monkeypatch):
    """Verify that setting API_KEY enforces X-API-Key validation."""
    settings = get_settings()
    monkeypatch.setattr(settings, "api_key", "secret_test_key_123")

    client = TestClient(app)

    # Missing API key -> 401 Unauthorized
    res_unauthorized = client.get("/meetings/")
    assert res_unauthorized.status_code == 401
    assert res_unauthorized.json()["detail"]["error"] == "unauthorized"

    # Invalid API key -> 401 Unauthorized
    res_bad_key = client.get("/meetings/", headers={"X-API-Key": "wrong_key"})
    assert res_bad_key.status_code == 401

    # Valid API key -> 200 OK
    res_valid = client.get("/meetings/", headers={"X-API-Key": "secret_test_key_123"})
    assert res_valid.status_code == 200


def test_file_upload_size_limit():
    """Verify file upload size restriction."""
    client = TestClient(app)
    # Create oversized content (11MB > default 10MB limit)
    oversized_content = b"A" * (11 * 1024 * 1024)
    files = {"file": ("bigfile.txt", oversized_content, "text/plain")}
    response = client.post("/documents/ingest/file", files=files)
    assert response.status_code == 413
    assert response.json()["detail"]["error"] == "file_too_large"
