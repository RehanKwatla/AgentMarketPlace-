"""Pytest Configuration and Shared Fixtures."""
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.shared.config import Settings, get_settings


@pytest.fixture(scope="session")
def client() -> TestClient:
    """FastAPI TestClient fixture."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_settings() -> Settings:
    """Provides standard test settings instance."""
    return get_settings()
