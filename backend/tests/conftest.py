"""Pytest Configuration and Shared Fixtures."""
import os
import tempfile
from pathlib import Path

# The autouse ledger fixture clears its database between tests. Never let the
# suite point that fixture at a developer's configured local_data/ledger.db.
_TEST_DATABASE_DIRECTORY = tempfile.TemporaryDirectory(prefix="di06-pytest-")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_TEST_DATABASE_DIRECTORY.name).as_posix()}/ledger.db"

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.shared.config import Settings, get_settings


def pytest_sessionfinish(session, exitstatus):
    """Close pooled SQLite handles before deleting this test's temporary database."""
    try:
        from backend.database.session import engine
        engine.dispose()
    finally:
        _TEST_DATABASE_DIRECTORY.cleanup()


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



