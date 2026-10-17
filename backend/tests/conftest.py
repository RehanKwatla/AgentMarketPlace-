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


@pytest.fixture(autouse=True)
def enforce_test_provider_mode():
    """Ensure test isolation by setting default provider_settings.mode to FAKE for test sessions."""
    try:
        from backend.sellers.providers.config import provider_settings, ProviderMode
        orig_mode = provider_settings.mode
        provider_settings.mode = ProviderMode.FAKE
    except Exception:
        orig_mode = None

    yield

    if orig_mode is not None:
        try:
            from backend.sellers.providers.config import provider_settings
            provider_settings.mode = orig_mode
        except Exception:
            pass


@pytest.fixture(autouse=True)
def clean_ledger_state():
    """Ensure test isolation by clearing ledger repository state between tests."""
    try:
        from backend.ledger.models import ledger_repo
        ledger_repo.clear()
    except Exception:
        pass
    yield
    try:
        from backend.ledger.models import ledger_repo
        ledger_repo.clear()
    except Exception:
        pass



