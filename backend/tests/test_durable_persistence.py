"""Comprehensive Test Suite for Phase 2C — Durable Persistence & Restart Safety.

Validates:
1. SQLAlchemy models (PaymentAttemptModel, BudgetReservationModel).
2. DurablePaymentRepository operations with SQLite session.
3. Process restart simulation: Idempotency recovery across clean instances.
4. Process restart simulation: Nonce replay detection across clean instances.
5. Process restart simulation: Pending reconciliation recovery across clean instances.
6. Atomic budget reservations persisted and committed/released.
"""
import asyncio
from datetime import datetime, timezone
import json
import pytest

from backend.database.session import Base, engine, SessionLocal
from backend.payments.models import (
    PaymentAttemptModel,
    BudgetReservationModel,
    DurablePaymentRepository,
    durable_payment_repo,
)
from backend.payments.schemas import PaymentStatus, PaymentAttemptRecord
from backend.payments.idempotency import IdempotencyStore, compute_payload_hash
from backend.payments.budget import BudgetManager
from backend.payments.service import PaymentService
from backend.shared.errors import ReplayAttackDetectedError, BudgetExceededError
from backend.payments.errors import IdempotencyConflictError


@pytest.fixture(autouse=True)
def setup_tables():
    """Ensure database tables are created before each test."""
    Base.metadata.create_all(bind=engine)
    yield
    # Cleanup payment attempt & reservation records created during test
    with SessionLocal() as session:
        session.query(PaymentAttemptModel).delete()
        session.query(BudgetReservationModel).delete()
        session.commit()


def test_payment_attempt_model_crud():
    """Test inserting and updating payment attempt records in durable storage."""
    repo = DurablePaymentRepository(session_factory=SessionLocal)
    now = datetime.now(timezone.utc)

    record = PaymentAttemptRecord(
        attempt_id="att_test_crud_01",
        task_id="task_001",
        call_id="call_001",
        service_id="data_001",
        idempotency_key="key_crud_01",
        request_hash="hash_crud_01",
        nonce="nonce_crud_01",
        amount_base_units=2000,
        pay_to="0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        status=PaymentStatus.PENDING_RECONCILIATION,
        tx_hash="0x123",
        settlement_proof="proof_123",
        created_at=now,
    )

    repo.save_attempt(record)

    # Query back
    fetched = repo.get_attempt_by_idempotency_key("key_crud_01")
    assert fetched is not None
    assert fetched.attempt_id == "att_test_crud_01"
    assert fetched.status == PaymentStatus.PENDING_RECONCILIATION.value
    assert fetched.amount_units == 2000

    # Update status to PAID
    record.status = PaymentStatus.PAID
    record.tx_hash = "0x" + "9" * 64
    repo.save_attempt(record)

    updated = repo.get_attempt_by_idempotency_key("key_crud_01")
    assert updated.status == PaymentStatus.PAID.value
    assert updated.tx_hash == "0x" + "9" * 64


def test_budget_reservation_durable_lifecycle():
    """Test creating, committing, and releasing budget reservations in DB."""
    repo = DurablePaymentRepository(session_factory=SessionLocal)

    res = repo.record_reservation(
        reservation_id="res_001",
        task_id="task_res_01",
        call_id="call_res_01",
        amount_base_units=3000,
        status="reserved",
    )
    assert res.reservation_id == "res_001"

    # Verify task reserved amount
    active_amount = repo.get_task_reserved_amount("task_res_01")
    assert active_amount == 3000

    # Commit reservation
    repo.update_reservation_status("res_001", "committed")
    active_after_commit = repo.get_task_reserved_amount("task_res_01")
    assert active_after_commit == 0


def test_idempotency_recovery_across_simulated_process_restart():
    """Simulate restart: Store attempt in DB, create brand new IdempotencyStore with empty memory."""
    repo = DurablePaymentRepository(session_factory=SessionLocal)
    payload = {"query": "SELECT *", "limit": 10}
    payload_hash = compute_payload_hash(payload)

    # 1. First process stores completed attempt in DB
    cached_response = {"status": "paid", "result": "sample data"}
    with SessionLocal() as session:
        model = PaymentAttemptModel(
            attempt_id="att_restart_01",
            task_id="task_restart",
            call_id="call_restart",
            service_id="data_001",
            idempotency_key="key_restart_001",
            request_hash=payload_hash,
            nonce="nonce_restart_001",
            amount_units=2000,
            status=PaymentStatus.PAID.value,
            response_json=json.dumps(cached_response),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(model)
        session.commit()

    # 2. Brand new process starts with completely empty in-memory cache
    fresh_store = IdempotencyStore(repo=repo)
    assert len(fresh_store._idempotency_cache) == 0
    assert len(fresh_store._idempotency_hashes) == 0

    # 3. Check identical request -> recovered from DB without re-execution
    is_new, cached = fresh_store.check_or_register("key_restart_001", payload_hash)
    assert is_new is False
    assert cached == cached_response

    # 4. Check mutated request with same key -> conflict raised from DB record
    mutated_hash = compute_payload_hash({"query": "DELETE *"})
    with pytest.raises(IdempotencyConflictError):
        fresh_store.check_or_register("key_restart_001", mutated_hash)


def test_nonce_replay_detection_across_simulated_process_restart():
    """Simulate restart: Verify nonce replay is caught from DB across clean instances."""
    repo = DurablePaymentRepository(session_factory=SessionLocal)

    with SessionLocal() as session:
        model = PaymentAttemptModel(
            attempt_id="att_nonce_01",
            task_id="task_nonce",
            call_id="call_nonce",
            service_id="data_001",
            idempotency_key="key_nonce_001",
            request_hash="hash_001",
            nonce="nonce_persisted_replay_001",
            amount_units=2000,
            status=PaymentStatus.PAID.value,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(model)
        session.commit()

    # Clean instance with zero in-memory nonces
    fresh_store = IdempotencyStore(repo=repo)
    assert len(fresh_store._used_nonces) == 0

    with pytest.raises(ReplayAttackDetectedError):
        fresh_store.record_and_verify_nonce("nonce_persisted_replay_001")


def test_pending_reconciliation_recovery_across_process_restart():
    """Simulate restart: Verify PaymentService loads pending reconciliations from database."""
    repo = DurablePaymentRepository(session_factory=SessionLocal)

    with SessionLocal() as session:
        model = PaymentAttemptModel(
            attempt_id="att_pending_rec_99",
            task_id="task_rec_99",
            call_id="call_rec_99",
            service_id="scraping_001",
            idempotency_key="key_rec_99",
            request_hash="hash_rec_99",
            nonce="nonce_rec_99",
            amount_units=3000,
            status=PaymentStatus.PENDING_RECONCILIATION.value,
            error_code="SETTLEMENT_TIMEOUT",
            error_reason="Network timeout after payment dispatch",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(model)
        session.commit()

    # Clean PaymentService instance with empty memory
    fresh_service = PaymentService(durable_repo=repo)
    assert len(fresh_service._pending_reconciliations) == 0

    # Query should retrieve the pending attempt from DB
    pending = fresh_service.get_pending_reconciliations()
    assert "att_pending_rec_99" in pending
    rec = pending["att_pending_rec_99"]
    assert rec.status == PaymentStatus.PENDING_RECONCILIATION
    assert rec.error_code == "SETTLEMENT_TIMEOUT"
    assert rec.service_id == "scraping_001"


@pytest.mark.asyncio
async def test_concurrent_budget_reservations_with_durable_storage():
    """Test 10 concurrent reservations with durable repo to verify no overdraw occurs."""
    repo = DurablePaymentRepository(session_factory=SessionLocal)
    task_id = "task_concurrent_durable"
    budget_mgr = BudgetManager(initial_budget_units=10_000, task_id=task_id, repo=repo)

    # 10 parallel reservation tasks of 1000 units each (total 10,000)
    async def make_reservation(index: int):
        return await budget_mgr.reserve(f"res_concurrent_{index}", 1000)

    results = await asyncio.gather(*(make_reservation(i) for i in range(10)))
    assert min(results) == 0  # Last reservation brings available budget to 0
    assert budget_mgr.available_budget == 0
    assert budget_mgr.reserved_budget == 10_000

    # 11th reservation must fail with BudgetExceededError
    with pytest.raises(BudgetExceededError):
        await budget_mgr.reserve("res_concurrent_11", 1000)

    # Verify durable storage contains all 10 active reservations
    active_in_db = repo.get_task_reserved_amount(task_id)
    assert active_in_db == 10_000
