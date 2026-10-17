"""Tests for CORS configuration and security hardening."""
from fastapi.testclient import TestClient
from backend.main import app


def test_cors_allowed_origin():
    """Verify that configured frontend origin receives valid CORS headers."""
    client = TestClient(app)
    response = client.get(
        "/health",
        headers={"Origin": "http://localhost:5173"}
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_disallowed_origin():
    """Verify that an arbitrary untrusted origin is rejected/not granted CORS."""
    client = TestClient(app)
    response = client.get(
        "/health",
        headers={"Origin": "https://malicious-attacker-website.com"}
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") is None
