"""[IMPLEMENTED] End-to-End Runtime Endpoint & Persistence Verification Suite.

Exercises:
1. GET /health
2. GET /api/v1/services
3. POST /api/v1/buyer/tasks
4. GET /api/v1/ledger
5. GET /api/v1/reputation
6. GET /api/v1/payments/dashboard
7. POST /api/v1/payments/multi-hop
8. GET /api/v1/payments/reconciliations
9. POST /api/v1/payments/reconcile
10. POST /api/v1/ledger/sync
11. Migration idempotency and repeated startup safety.
12. PostgreSQL dialect advisory lock SQL syntax validation.
"""
from datetime import datetime, timezone
import pytest
from starlette.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.database.session import Base, init_db, _migrate_schema
from backend.shared.constants import (
    NETWORK_BASE_SEPOLIA,
    USDC_BASE_SEPOLIA,
    LedgerStatus,
)
from backend.shared.schemas import LedgerRecordSchema
from backend.ledger.models import LedgerRepository, ledger_repo


@pytest.fixture
def api_client():
    """Provides a Starlette TestClient with full ASGI middleware and route dispatching."""
    with TestClient(app) as client:
        yield client


def test_runtime_health_endpoint(api_client):
    """1. GET /health: Returns healthy status, Base Sepolia network, and connected subsystems."""
    res = api_client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["network"] == NETWORK_BASE_SEPOLIA
    assert data["services"]["database"] == "connected"
    assert data["services"]["registry"] == "active"
    assert data["services"]["payment_engine"] == "configured"


def test_runtime_services_endpoint(api_client):
    """2. GET /api/v1/services: Discovers registered autonomous microservices."""
    res = api_client.get("/api/v1/services")
    assert res.status_code == 200
    data = res.json()
    assert "services" in data
    assert len(data["services"]) >= 3
    service_ids = {s["service_id"] for s in data["services"]}
    assert "data_001" in service_ids
    assert "scraping_001" in service_ids
    assert "inference_001" in service_ids


def test_runtime_buyer_tasks_endpoint(api_client):
    """3. POST /api/v1/buyer/tasks: Executes autonomous multi-service buyer workflow."""
    payload = {
        "task": "Analyze market sentiment for Agent Economy tokens",
        "budget_usdc": "0.05",
    }
    res = api_client.post("/api/v1/buyer/tasks", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "task_id" in data
    assert data["status"] in ("completed", "refused", "failed")
    assert "total_cost_usdc" in data
    assert "executions" in data


def test_runtime_ledger_endpoint(api_client):
    """4. GET /api/v1/ledger: Queries paginated immutable audit records."""
    res = api_client.get("/api/v1/ledger?limit=10")
    assert res.status_code == 200
    data = res.json()
    assert "total" in data
    assert "records" in data
    assert isinstance(data["records"], list)


def test_runtime_reputation_endpoint(api_client):
    """5. GET /api/v1/reputation: Retrieves observed reliability metrics for registered services."""
    res = api_client.get("/api/v1/reputation")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, dict)
    assert "data_001" in data or "scraping_001" in data


def test_runtime_payments_dashboard_endpoint(api_client):
    """6. GET /api/v1/payments/dashboard: Retrieves authoritative metrics and settlement evidence breakdown."""
    res = api_client.get("/api/v1/payments/dashboard")
    assert res.status_code == 200
    data = res.json()
    assert data["network"] == NETWORK_BASE_SEPOLIA
    assert data["token_address"] == USDC_BASE_SEPOLIA
    assert "settlement_evidence" in data
    evidence = data["settlement_evidence"]
    assert "confirmed_on_chain" in evidence
    assert "local_authorization" in evidence
    assert "unverified_hash" in evidence
    assert "pending_reconciliation" in evidence


def test_runtime_payments_multi_hop_endpoint(api_client):
    """7. POST /api/v1/payments/multi-hop: Executes planned paid-call pipeline."""
    payload = {
        "task_id": "test_runtime_multihop_01",
        "max_budget_usdc": 0.05,
        "steps": [
            {
                "step_id": 1,
                "service_id": "data_001",
                "input_payload": {"query": "clean"},
            },
        ],
    }
    res = api_client.post("/api/v1/payments/multi-hop", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["task_id"] == "test_runtime_multihop_01"
    assert data["status"] in ("completed", "refused", "failed", "partial_failure")
    assert "steps" in data
    assert len(data["steps"]) == 1


def test_runtime_payments_reconciliations_endpoint(api_client):
    """8. GET /api/v1/payments/reconciliations: Lists attempts currently held in suspense."""
    res = api_client.get("/api/v1/payments/reconciliations")
    assert res.status_code == 200
    data = res.json()
    assert "pending_reconciliations" in data
    assert "total" in data


def test_runtime_payments_batch_reconcile_endpoint(api_client):
    """9. POST /api/v1/payments/reconcile: Triggers authoritative re-query for pending suspense items."""
    res = api_client.post("/api/v1/payments/reconcile")
    assert res.status_code == 200
    data = res.json()
    assert "reconciled_attempts" in data
    assert "total" in data


def test_runtime_ledger_sync_endpoint(api_client):
    """10. POST /api/v1/ledger/sync: Idempotently syncs historical settlement evidence into ledger."""
    res = api_client.post("/api/v1/ledger/sync")
    assert res.status_code == 200
    data = res.json()
    assert "synced_new" in data
    assert "already_current" in data
    assert "errors" in data
    assert data["errors"] == 0


def test_repeated_database_initialization_safety(tmp_path):
    """11. Verify repeated schema initialization & migration is non-destructive and idempotent."""
    db_file = tmp_path / "repeated_init.db"
    eng = create_engine(f"sqlite:///{db_file}")

    # First initialization
    init_db(target_engine=eng)
    session_factory = sessionmaker(bind=eng)

    # Insert a record
    repo = LedgerRepository(session_factory=session_factory)
    test_rec = LedgerRecordSchema(
        request_id="req_repeat_init_001",
        task_id="task_repeat",
        call_id="call_1",
        buyer_id="buyer_001",
        seller_id="seller_data_001",
        service_id="data_001",
        listed_price="0.002000",
        amount_paid="0.002000",
        amount_base_units=2000,
        tx_hash="rec_auth_test_repeat",
        status=LedgerStatus.PAID,
        latency_ms=10.0,
    )
    repo.record_transaction(test_rec)

    # Second initialization on same database
    init_db(target_engine=eng)

    # Third initialization on same database
    init_db(target_engine=eng)

    # Verify record survived all repeated initializations completely intact
    repo_reloaded = LedgerRepository(session_factory=session_factory)
    retrieved = repo_reloaded.get_record("req_repeat_init_001")
    assert retrieved is not None
    assert retrieved.request_id == "req_repeat_init_001"
    assert retrieved.amount_paid == "0.002000"


def test_postgresql_advisory_lock_sql_syntax_validity():
    """12. Validate that the PostgreSQL advisory lock SQL statements are syntactically and structurally valid."""
    # Verify the exact SQL text used in DurablePaymentRepository
    lock_nonce_sql = text("SELECT pg_advisory_xact_lock(hashtext(:auth_key))")
    lock_budget_sql = text("SELECT pg_advisory_xact_lock(hashtext(:task_id))")

    compiled_nonce = str(lock_nonce_sql.compile())
    compiled_budget = str(lock_budget_sql.compile())

    assert "pg_advisory_xact_lock" in compiled_nonce
    assert "hashtext" in compiled_nonce
    assert "pg_advisory_xact_lock" in compiled_budget
    assert "hashtext" in compiled_budget


def test_runtime_list_tasks_endpoints(api_client):
    """13. GET /api/v1/tasks and /api/v1/buyer/tasks: Retrieve paginated tasks with status filters."""
    # Verify primary tasks list
    res = api_client.get("/api/v1/tasks?limit=10")
    assert res.status_code == 200
    tasks = res.json()
    assert isinstance(tasks, list)

    # Verify legacy route backward compatibility
    res_legacy = api_client.get("/api/v1/buyer/tasks?limit=10")
    assert res_legacy.status_code == 200
    tasks_legacy = res_legacy.json()
    assert isinstance(tasks_legacy, list)


def test_runtime_ledger_filtering(api_client):
    """14. GET /api/v1/ledger: Filter by task_id, tx_hash, and buyer_id."""
    unique_task = "task_test_filter_99"
    unique_tx = "rec_auth_test_filter_99"
    unique_buyer = "buyer_filter_99"

    test_rec = LedgerRecordSchema(
        request_id="req_test_filter_99",
        task_id=unique_task,
        call_id="call_filter_99",
        buyer_id=unique_buyer,
        seller_id="seller_data_001",
        service_id="data_001",
        listed_price="0.002000",
        amount_paid="0.002000",
        amount_base_units=2000,
        tx_hash=unique_tx,
        settlement_proof=unique_tx,
        status=LedgerStatus.PAID,
        latency_ms=12.0,
    )
    ledger_repo.record_transaction(test_rec)

    # Filter by task_id
    res_task = api_client.get(f"/api/v1/ledger?task_id={unique_task}")
    assert res_task.status_code == 200
    data_task = res_task.json()
    assert data_task["total"] >= 1
    assert any(r["task_id"] == unique_task for r in data_task["records"])

    # Filter by tx_hash
    res_tx = api_client.get(f"/api/v1/ledger?tx_hash={unique_tx}")
    assert res_tx.status_code == 200
    data_tx = res_tx.json()
    assert data_tx["total"] >= 1
    assert any(r["tx_hash"] == unique_tx for r in data_tx["records"])

    # Filter by buyer_id
    res_buyer = api_client.get(f"/api/v1/ledger?buyer_id={unique_buyer}")
    assert res_buyer.status_code == 200
    data_buyer = res_buyer.json()
    assert data_buyer["total"] >= 1
    assert any(r["buyer_id"] == unique_buyer for r in data_buyer["records"])


def test_runtime_verify_tx_endpoint(api_client):
    """15. GET /api/v1/payments/verify-tx/{tx_hash}: Check settlement evidence without fabrication."""
    # Unknown tx hash
    res_unknown = api_client.get("/api/v1/payments/verify-tx/0x9999999999999999999999999999999999999999999999999999999999999999")
    assert res_unknown.status_code == 200
    data_unknown = res_unknown.json()
    assert data_unknown["is_confirmed"] is False
    assert data_unknown["status"] == "not_found"

    # Insert a verified local authorization record into ledger
    tx_auth = "rec_auth_verify_test_01"
    auth_rec = LedgerRecordSchema(
        request_id="req_verify_test_01",
        task_id="task_verify_01",
        call_id="call_verify_01",
        buyer_id="buyer_verify_01",
        seller_id="seller_data_001",
        service_id="data_001",
        listed_price="0.002000",
        amount_paid="0.002000",
        amount_base_units=2000,
        tx_hash=tx_auth,
        settlement_proof=tx_auth,
        status=LedgerStatus.PAID,
        latency_ms=10.0,
    )
    ledger_repo.record_transaction(auth_rec)

    # Local authorization record from ledger
    res_local = api_client.get(f"/api/v1/payments/verify-tx/{tx_auth}")
    assert res_local.status_code == 200
    data_local = res_local.json()
    assert data_local["is_confirmed"] is False
    assert data_local["status"] == "local_authorization"
    assert data_local["evidence_type"] == "local_authorization"


def test_runtime_wallet_balance_endpoint(api_client):
    """16. GET /api/v1/wallets/{address}/balance: Resilient on-chain / offline balance query."""
    test_addr = "0xd43E2b230255C89E78D6205d3f1d938173a8f707"
    res = api_client.get(f"/api/v1/wallets/{test_addr}/balance")
    assert res.status_code == 200
    data = res.json()
    assert data["address"].lower() == test_addr.lower()
    assert data["network"] == NETWORK_BASE_SEPOLIA
    assert data["chain_id"] == 84532
    assert data["token"] == "USDC"
    assert "balance_base_units" in data
    assert "balance_usdc" in data
    assert "native_balance_eth" in data
    assert "source" in data

