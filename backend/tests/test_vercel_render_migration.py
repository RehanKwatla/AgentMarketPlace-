"""Tests for Vercel + Render Deployment Migration Configuration.

Verifies:
1. Database URL normalization for Render PostgreSQL (postgres:// -> postgresql://).
2. Production database URL enforcement (prohibiting SQLite fallback in production).
3. CORS allowlist behavior and wildcard restriction in production.
4. Health check endpoint probing real database readiness and failing safely if DB is down.
5. Standalone database migration execution.
"""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.main import app
from backend.database.session import normalize_database_url, init_db


def test_normalize_database_url_render_postgres_scheme():
    """Verify that Render's postgres:// URI scheme is normalized to postgresql:// for SQLAlchemy."""
    raw_url = "postgres://agent_user:secret_pass@dpg-abc12345.render.com/agent_marketplace"
    normalized = normalize_database_url(raw_url, environment="production")
    assert normalized.startswith("postgresql://")
    assert not normalized.startswith("postgres://")
    assert "agent_user:secret_pass@dpg-abc12345.render.com/agent_marketplace" in normalized


def test_normalize_database_url_preserves_postgresql_scheme():
    """Verify standard postgresql:// and postgresql+psycopg2:// URLs are preserved intact."""
    std_url = "postgresql://user:pass@localhost:5432/db"
    assert normalize_database_url(std_url, environment="production") == std_url

    driver_url = "postgresql+psycopg2://user:pass@localhost:5432/db"
    assert normalize_database_url(driver_url, environment="production") == driver_url


def test_normalize_database_url_rejects_sqlite_in_production():
    """Verify that production fails clearly when configured with SQLite instead of silently falling back."""
    with pytest.raises(ValueError, match="Production environment requires a PostgreSQL DATABASE_URL"):
        normalize_database_url("sqlite:///./local_data/ledger.db", environment="production")

    with pytest.raises(ValueError, match="Production environment requires a PostgreSQL DATABASE_URL"):
        normalize_database_url("", environment="production")

    with pytest.raises(ValueError, match="Production environment requires a PostgreSQL DATABASE_URL"):
        normalize_database_url(None, environment="production")


def test_normalize_database_url_allows_sqlite_in_development():
    """Verify that development/test environments allow SQLite."""
    dev_url = normalize_database_url("sqlite:///./local_data/ledger.db", environment="development")
    assert dev_url == "sqlite:///./local_data/ledger.db"

    fallback = normalize_database_url("", environment="development")
    assert fallback.startswith("sqlite")


def test_health_check_database_connected():
    """Verify /health returns 200 OK and database: connected under normal operation."""
    client = TestClient(app)
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["services"]["database"] == "connected"


def test_health_check_database_disconnected_returns_503():
    """Verify /health returns 503 Service Unavailable if database connectivity fails."""
    client = TestClient(app)
    with patch("backend.database.session.SessionLocal", side_effect=Exception("Connection refused")):
        res = client.get("/health")
        assert res.status_code == 503
        data = res.json()
        assert data["status"] == "unhealthy"
        assert data["services"]["database"] == "disconnected"


def test_cors_allowlist_configured_origin():
    """Verify that allowed origins receive CORS headers."""
    client = TestClient(app)
    res = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET"
        }
    )
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_rejects_unlisted_origin():
    """Verify that unlisted origins do NOT receive access-control-allow-origin header."""
    client = TestClient(app)
    res = client.options(
        "/health",
        headers={
            "Origin": "https://malicious-website.com",
            "Access-Control-Request-Method": "GET"
        }
    )
    assert res.headers.get("access-control-allow-origin") is None


def test_standalone_database_initialization():
    """Verify standalone init_db execution runs cleanly without errors."""
    init_db()


def test_frontend_production_missing_api_base_url_safety_guard():
    """Verify frontend client.ts explicitly blocks missing VITE_API_BASE_URL in production."""
    import pathlib
    client_ts_path = pathlib.Path(__file__).resolve().parent.parent.parent / "frontend" / "src" / "api" / "client.ts"
    assert client_ts_path.exists(), "frontend/src/api/client.ts must exist"
    content = client_ts_path.read_text(encoding="utf-8")
    assert "Deployment Configuration Error: VITE_API_BASE_URL is not set" in content
    assert "isProd" in content
    assert "throw new Error" in content


def test_frontend_built_bundle_no_secrets_leakage():
    """Verify built frontend bundle in dist/ does not contain secrets, private keys, or credentials."""
    import pathlib
    dist_dir = pathlib.Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    if not dist_dir.exists():
        pytest.skip("frontend/dist does not exist; run npm run build first")

    for file_path in dist_dir.rglob("*.js"):
        content = file_path.read_text(encoding="utf-8")
        assert "BUYER_PRIVATE_KEY" not in content
        assert "OPENAI_API_KEY" not in content
        assert "GROQ_API_KEY" not in content
        assert "postgresql://" not in content
        assert "postgres://" not in content


def test_render_yaml_specification_integrity():
    """Verify render.yaml accurately reflects application entrypoint and settings."""
    import pathlib
    render_yaml_path = pathlib.Path(__file__).resolve().parent.parent.parent / "render.yaml"
    assert render_yaml_path.exists(), "render.yaml must exist"
    content = render_yaml_path.read_text(encoding="utf-8")
    assert "backend.main:app" in content
    assert "uvicorn backend.main:app --host 0.0.0.0 --port $PORT" in content
    assert "healthCheckPath: /health" in content
    assert "agent-marketplace-postgres" in content
