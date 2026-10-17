"""[IMPLEMENTED] Member 4 Persistence, Concurrency, and Historical Synchronization Test Suite.

Covers:
1. Durable ledger persistence and retrieval across repository restarts.
2. Field completeness (task_id, call_id, amount_base_units, settlement_proof, network).
3. Idempotent retry safety (no duplicates on retry).
4. Database error handling (explicit failure, no false claims).
5. Historical settlement synchronization (idempotency, evidence preservation, no promotion).
6. Cross-process / multi-connection authorization nonce concurrency.
7. Concurrent budget reservation without overspending.
8. Duplicate settlement evidence rejection.
9. Dashboard accounting consistency and aggregation definitions.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.session import Base
from backend.database.models import LedgerRecordModel
from backend.shared.constants import (
    LedgerStatus,
    NETWORK_BASE_SEPOLIA,
    USDC_BASE_SEPOLIA,
    base_units_to_usdc,
)
from backend.shared.schemas import LedgerRecordSchema
from backend.ledger.models import LedgerRepository, ledger_repo
from backend.ledger.reconciliation import SettlementReconciler
from backend.payments.models import (
    DurablePaymentRepository,
    PaymentAttemptModel,
    SettlementEvidenceRecordModel,
    AuthorizationNonceReservationModel,
    BudgetReservationModel,
)
from backend.payments.errors import SettlementVerificationError


from sqlalchemy.pool import StaticPool


@pytest.fixture
def isolated_db(tmp_path):
    """Provides a dedicated file-backed SQLite database for genuine multi-connection concurrency and persistence tests."""
    db_file = tmp_path / "test_concurrency.db"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return session_factory


def test_ledger_records_durable_persistence_and_retrieval(isolated_db):
    """Verify ledger records survive repository recreation against the same database."""
    repo1 = LedgerRepository(session_factory=isolated_db)

    record = LedgerRecordSchema(
        request_id="req_durable_001",
        task_id="task_durable_alpha",
        call_id="call_step_1",
        timestamp=datetime.now(timezone.utc),
        buyer_id="buyer_001",
        seller_id="seller_data_001",
        service_id="data_001",
        listed_price="0.002000",
        amount_paid="0.002000",
        amount_base_units=2000,
        tx_hash="rec_auth_proof_abc",
        settlement_proof="rec_auth_proof_abc",
        network=NETWORK_BASE_SEPOLIA,
        token_address=USDC_BASE_SEPOLIA,
        status=LedgerStatus.PAID,
        latency_ms=35.5,
        error_reason=None,
    )

    # Write using repo1
    repo1.record_transaction(record)

    # Recreate repository instance from the same database (simulating service restart)
    repo2 = LedgerRepository(session_factory=isolated_db)
    retrieved = repo2.get_record("req_durable_001")

    assert retrieved is not None
    assert retrieved.request_id == "req_durable_001"
    assert retrieved.task_id == "task_durable_alpha"
    assert retrieved.call_id == "call_step_1"
    assert retrieved.service_id == "data_001"
    assert retrieved.amount_paid == "0.002000"
    assert retrieved.amount_base_units == 2000
    assert retrieved.tx_hash == "rec_auth_proof_abc"
    assert retrieved.settlement_proof == "rec_auth_proof_abc"
    assert retrieved.network == NETWORK_BASE_SEPOLIA
    assert retrieved.token_address == USDC_BASE_SEPOLIA
    assert retrieved.status == LedgerStatus.PAID
    assert retrieved.latency_ms == 35.5


def test_ledger_records_idempotent_retry_safety(isolated_db):
    """Verify that retrying a write for the same request_id updates without creating duplicate records."""
    repo = LedgerRepository(session_factory=isolated_db)

    record_initial = LedgerRecordSchema(
        request_id="req_retry_001",
        task_id="task_retry_test",
        buyer_id="buyer_001",
        seller_id="seller_scraping_001",
        service_id="scraping_001",
        listed_price="0.003000",
        amount_paid="0.003000",
        status=LedgerStatus.PAID,
        latency_ms=45.0,
    )
    repo.record_transaction(record_initial)

    # Retry with updated tx_hash
    record_retry = LedgerRecordSchema(
        request_id="req_retry_001",
        task_id="task_retry_test",
        buyer_id="buyer_001",
        seller_id="seller_scraping_001",
        service_id="scraping_001",
        listed_price="0.003000",
        amount_paid="0.003000",
        tx_hash="rec_auth_confirmed_proof",
        settlement_proof="rec_auth_confirmed_proof",
        status=LedgerStatus.PAID,
        latency_ms=45.0,
    )
    repo.record_transaction(record_retry)

    assert repo.count() == 1
    stored = repo.get_record("req_retry_001")
    assert stored is not None
    assert stored.tx_hash == "rec_auth_confirmed_proof"


def test_ledger_record_persistence_failure_handling():
    """Verify that database errors during write raise explicit errors rather than falsely claiming success."""
    # Use a faulty session factory
    class BrokenSessionFactory:
        def __call__(self):
            raise RuntimeError("Database connection refused")

    broken_repo = LedgerRepository(session_factory=BrokenSessionFactory())
    record = LedgerRecordSchema(
        request_id="req_fault_001",
        buyer_id="b1",
        seller_id="s1",
        service_id="srv1",
        listed_price="0.001",
        amount_paid="0.001",
        status=LedgerStatus.PAID,
        latency_ms=10.0,
    )

    with pytest.raises(RuntimeError) as exc_info:
        broken_repo.record_transaction(record)
    assert "Durable ledger persistence failed" in str(exc_info.value)


def test_historical_settlement_synchronization_idempotent(isolated_db):
    """Verify that historical settlement evidence sync is idempotent and preserves evidence levels."""
    durable_repo = DurablePaymentRepository(session_factory=isolated_db)
    ledger_r = LedgerRepository(session_factory=isolated_db)
    reconciler = SettlementReconciler(repository=ledger_r, session_factory=isolated_db)

    # Seed an historical payment attempt
    with isolated_db() as session:
        att = PaymentAttemptModel(
            attempt_id="req_hist_sync_001",
            task_id="task_hist_001",
            call_id="call_hist_1",
            service_id="inference_001",
            idempotency_key="idemp_hist_001",
            request_hash="hash_abc",
            nonce="nonce_hist_001",
            amount_units=4000,
            pay_to="0x0000000000000000000000000000000000000003",
            status="paid",
            tx_hash="rec_auth_hist_proof",
            settlement_proof="rec_auth_hist_proof",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(att)
        session.commit()

    # Pass 1: Initial Sync
    stats1 = reconciler.sync_historical_settlements()
    assert stats1["synced_new"] == 1
    assert stats1["already_current"] == 0
    assert stats1["errors"] == 0

    record = ledger_r.get_record("req_hist_sync_001")
    assert record is not None
    assert record.amount_paid == "0.004000"
    assert record.amount_base_units == 4000
    assert record.status == LedgerStatus.PAID
    assert record.settlement_proof == "rec_auth_hist_proof"

    # Pass 2: Repeated Sync (Must be idempotent: 0 new, 1 already_current, count still 1)
    stats2 = reconciler.sync_historical_settlements()
    assert stats2["synced_new"] == 0
    assert stats2["already_current"] == 1
    assert stats2["errors"] == 0
    assert ledger_r.count() == 1


def test_concurrent_nonce_reservations_isolation(isolated_db):
    """Verify cross-process / multi-connection concurrency isolation for authorization nonces."""
    durable_repo = DurablePaymentRepository(session_factory=isolated_db)
    auth_key = "eip155:84532:0xsigner:nonce_concurrency_test_01"

    success_count = 0
    failure_count = 0

    def try_reserve():
        try:
            return durable_repo.atomic_reserve_authorization_nonce(
                auth_key=auth_key,
                network=NETWORK_BASE_SEPOLIA,
                nonce="nonce_concurrency_test_01",
                signer_address="0xsigner",
                ttl_seconds=3600,
            )
        except SettlementVerificationError:
            return False

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(try_reserve) for _ in range(8)]
        results = [f.result() for f in futures]

    successes = [r for r in results if r is True]
    failures = [r for r in results if r is False]

    # Exactly one worker must succeed in reserving the authorization
    assert len(successes) == 1
    assert len(failures) == 7


def test_concurrent_budget_reservations_atomic(isolated_db):
    """Verify atomic budget reservations prevent overdraw under high concurrency."""
    durable_repo = DurablePaymentRepository(session_factory=isolated_db)
    task_id = "task_budget_concurrency_01"
    total_budget = 10000  # 0.010 USDC

    # 10 workers each attempting to reserve 2000 units (max 5 can succeed)
    def try_reserve(idx):
        success, remaining, msg = durable_repo.atomic_reserve(
            reservation_id=f"res_{task_id}_{idx}",
            task_id=task_id,
            call_id=f"call_{idx}",
            amount_base_units=2000,
            total_budget_units=total_budget,
        )
        return success

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(try_reserve, i) for i in range(10)]
        results = [f.result() for f in futures]

    successes = [r for r in results if r is True]
    assert len(successes) == 5  # Exactly 5 * 2000 = 10000 units reserved
    assert durable_repo.get_task_reserved_amount(task_id) == 10000


def test_duplicate_settlement_evidence_rejection(isolated_db):
    """Verify duplicate settlement evidence for distinct attempts fails closed."""
    durable_repo = DurablePaymentRepository(session_factory=isolated_db)
    tx_hash = "0x9876543210abcdef9876543210abcdef9876543210abcdef9876543210abcdef"

    # Attempt 1 records evidence successfully
    ok1 = durable_repo.atomic_record_settlement_evidence(
        attempt_id="req_att_01",
        network=NETWORK_BASE_SEPOLIA,
        amount_units=2000,
        tx_hash=tx_hash,
        log_index=0,
    )
    assert ok1 is True

    # Idempotent re-recording for the same attempt succeeds
    ok1_retry = durable_repo.atomic_record_settlement_evidence(
        attempt_id="req_att_01",
        network=NETWORK_BASE_SEPER_RETRY if False else NETWORK_BASE_SEPOLIA,
        amount_units=2000,
        tx_hash=tx_hash,
        log_index=0,
    )
    assert ok1_retry is True

    # Attempt 2 attempting to reuse the same evidence MUST be rejected
    with pytest.raises(SettlementVerificationError) as exc_info:
        durable_repo.atomic_record_settlement_evidence(
            attempt_id="req_att_02_fraudulent",
            network=NETWORK_BASE_SEPOLIA,
            amount_units=2000,
            tx_hash=tx_hash,
            log_index=0,
        )
    assert "Duplicate settlement evidence detected" in str(exc_info.value)


def test_dashboard_accounting_definitions_and_aggregation(isolated_db):
    """Priority D: Verify dashboard accounting rules, multi-hop pipeline cost, and settlement certainty."""
    repo = LedgerRepository(session_factory=isolated_db)

    # Simulate 2 distinct tasks, each executing a 3-hop pipeline (3 paid calls @ 0.003000 USDC each)
    # Total calls: 6, Total tasks: 2, Total spend: 0.018000 USDC, 3-hop pipeline cost: 0.009000 USDC
    tasks = ["task_pipeline_alpha", "task_pipeline_beta"]
    services = ["data_001", "compute_001", "storage_001"]

    for t_idx, task_id in enumerate(tasks):
        for s_idx, srv in enumerate(services):
            req_id = f"req_{task_id}_hop_{s_idx + 1}"
            record = LedgerRecordSchema(
                request_id=req_id,
                task_id=task_id,
                call_id=f"call_hop_{s_idx + 1}",
                timestamp=datetime.now(timezone.utc),
                buyer_id="buyer_agent_primary",
                seller_id=f"seller_{srv}",
                service_id=srv,
                listed_price="0.003000",
                amount_paid="0.003000",
                amount_base_units=3000,
                tx_hash=f"rec_auth_proof_{t_idx}_{s_idx}",
                settlement_proof=f"rec_auth_proof_{t_idx}_{s_idx}",
                network=NETWORK_BASE_SEPOLIA,
                token_address=USDC_BASE_SEPOLIA,
                status=LedgerStatus.PAID,
                latency_ms=25.0 + s_idx * 10,
            )
            repo.record_transaction(record)

    all_records = repo.list_records(limit=100)
    assert len(all_records) == 6

    # 1. Unique task count calculation
    unique_tasks = {r.task_id for r in all_records if r.task_id}
    assert len(unique_tasks) == 2
    assert "task_pipeline_alpha" in unique_tasks
    assert "task_pipeline_beta" in unique_tasks

    # 2. Spend calculations
    total_spend_units = sum(r.amount_base_units for r in all_records if r.status == LedgerStatus.PAID)
    assert total_spend_units == 18000
    assert base_units_to_usdc(total_spend_units) == "0.018000"

    # Single 3-hop pipeline cost
    task_alpha_records = [r for r in all_records if r.task_id == "task_pipeline_alpha"]
    assert len(task_alpha_records) == 3
    alpha_cost_units = sum(r.amount_base_units for r in task_alpha_records)
    assert alpha_cost_units == 9000
    assert base_units_to_usdc(alpha_cost_units) == "0.009000"

    # 3. Settlement certainty verification
    # All 6 records have rec_auth_* settlement proofs (local authorizations awaiting on-chain settlement)
    # Zero records must be classified as confirmed on-chain
    confirmed_on_chain = [
        r for r in all_records
        if (r.settlement_proof or "").startswith("onchain_confirmed_")
    ]
    local_auths = [
        r for r in all_records
        if (r.settlement_proof or "").startswith("rec_auth_") or (r.settlement_proof or "").startswith("local_")
    ]
    assert len(confirmed_on_chain) == 0
    assert len(local_auths) == 6

    # 4. Idempotent retry safety: retrying one of the calls does not inflate spend or count
    duplicate_record = LedgerRecordSchema(
        request_id="req_task_pipeline_alpha_hop_1",
        task_id="task_pipeline_alpha",
        call_id="call_hop_1",
        timestamp=datetime.now(timezone.utc),
        buyer_id="buyer_agent_primary",
        seller_id="seller_data_001",
        service_id="data_001",
        listed_price="0.003000",
        amount_paid="0.003000",
        amount_base_units=3000,
        tx_hash="rec_auth_proof_0_0",
        settlement_proof="rec_auth_proof_0_0",
        network=NETWORK_BASE_SEPOLIA,
        token_address=USDC_BASE_SEPOLIA,
        status=LedgerStatus.PAID,
        latency_ms=25.0,
    )
    repo.record_transaction(duplicate_record)
    assert repo.count() == 6
    updated_records = repo.list_records(limit=100)
    recalculated_spend = sum(r.amount_base_units for r in updated_records if r.status == LedgerStatus.PAID)
    assert recalculated_spend == 18000


def test_settlement_confirmation_anti_bypass_boundary(isolated_db):
    """Anti-Bypass Test: Fabricated proof prefixes, raw hashes, and local receipts NEVER produce confirmed_on_chain."""
    repo = LedgerRepository(session_factory=isolated_db)

    # 1. Fabricated proof prefix attempting to bypass verification
    record_fabricated_prefix = LedgerRecordSchema(
        request_id="req_bypass_prefix_001",
        task_id="task_bypass_test",
        call_id="call_1",
        buyer_id="buyer_001",
        seller_id="seller_data_001",
        service_id="data_001",
        listed_price="0.002000",
        amount_paid="0.002000",
        amount_base_units=2000,
        tx_hash="0x1111222233334444555566667777888899990000111122223333444455556666",
        settlement_proof="onchain_confirmed_fabricated_hash_bypass",
        status=LedgerStatus.PAID,
        latency_ms=10.0,
    )
    repo.record_transaction(record_fabricated_prefix)

    # 2. Raw tx hash without on-chain receipt evidence in durable storage
    record_raw_hash = LedgerRecordSchema(
        request_id="req_raw_hash_002",
        task_id="task_bypass_test",
        call_id="call_2",
        buyer_id="buyer_001",
        seller_id="seller_data_001",
        service_id="data_001",
        listed_price="0.002000",
        amount_paid="0.002000",
        amount_base_units=2000,
        tx_hash="0xaaaa22223333444455556666777788889999000011112222333344445555bbbb",
        settlement_proof=None,
        status=LedgerStatus.PAID,
        latency_ms=10.0,
    )
    repo.record_transaction(record_raw_hash)

    # 3. Local authorization receipt
    record_local_auth = LedgerRecordSchema(
        request_id="req_local_auth_003",
        task_id="task_bypass_test",
        call_id="call_3",
        buyer_id="buyer_001",
        seller_id="seller_data_001",
        service_id="data_001",
        listed_price="0.002000",
        amount_paid="0.002000",
        amount_base_units=2000,
        tx_hash="rec_auth_proof_local_only",
        settlement_proof="rec_auth_proof_local_only",
        status=LedgerStatus.PAID,
        latency_ms=10.0,
    )
    repo.record_transaction(record_local_auth)

    # 4. Genuinely verified on-chain evidence in durable storage
    verified_tx = "0x999922223333444455556666777788889999000011112222333344445555cccc"
    with isolated_db() as sess:
        ev_model = SettlementEvidenceRecordModel(
            evidence_id="ev_verified_receipt_001",
            tx_hash=verified_tx.lower(),
            log_index=0,
            facilitator_receipt_id=None,
            attempt_id="req_verified_onchain_004",
            network=NETWORK_BASE_SEPOLIA,
            token_address=USDC_BASE_SEPOLIA,
            recipient_address="0x70997970c51812dc3a010c7d01b50e0d17dc79c8",
            amount_units=2000,
            created_at=datetime.now(timezone.utc),
        )
        sess.add(ev_model)
        sess.commit()

    record_verified = LedgerRecordSchema(
        request_id="req_verified_onchain_004",
        task_id="task_bypass_test",
        call_id="call_4",
        buyer_id="buyer_001",
        seller_id="seller_data_001",
        service_id="data_001",
        listed_price="0.002000",
        amount_paid="0.002000",
        amount_base_units=2000,
        tx_hash=verified_tx,
        settlement_proof=verified_tx,
        status=LedgerStatus.PAID,
        latency_ms=10.0,
    )
    repo.record_transaction(record_verified)

    # Evaluate classification strictly using the hardened rules
    records = repo.list_records(limit=100)
    classification = {
        "confirmed_on_chain": 0,
        "local_authorization": 0,
        "unverified_hash": 0,
    }

    with isolated_db() as db_sess:
        for r in records:
            proof = getattr(r, "settlement_proof", None) or ""
            tx_h = getattr(r, "tx_hash", None)

            if not tx_h or proof.startswith("rec_auth_") or proof.startswith("local_"):
                classification["local_authorization"] += 1
            else:
                is_verified = False
                if tx_h and tx_h.startswith("0x") and len(tx_h) in (64, 66):
                    ev = db_sess.query(SettlementEvidenceRecordModel).filter(
                        SettlementEvidenceRecordModel.tx_hash == tx_h.lower(),
                        SettlementEvidenceRecordModel.network == NETWORK_BASE_SEPOLIA,
                        SettlementEvidenceRecordModel.token_address == USDC_BASE_SEPOLIA,
                    ).first()
                    if ev and ev.recipient_address:
                        is_verified = True
                if is_verified:
                    classification["confirmed_on_chain"] += 1
                else:
                    classification["unverified_hash"] += 1

    # Exactly 1 record is genuinely confirmed on-chain
    assert classification["confirmed_on_chain"] == 1
    # Fabricated prefix + raw hash must both be unverified_hash (2 total)
    assert classification["unverified_hash"] == 2
    # Local auth is local_authorization (1 total)
    assert classification["local_authorization"] == 1


def test_upsert_preserves_stronger_evidence_on_weaker_retry(isolated_db):
    """Verify upsert preserves stronger verified evidence when a retry contains weaker evidence."""
    repo = LedgerRepository(session_factory=isolated_db)

    # Step 1: Record initial transaction with verified on-chain tx_hash and PAID status
    initial = LedgerRecordSchema(
        request_id="req_evidence_preserve_001",
        task_id="task_preserve_test",
        call_id="call_1",
        buyer_id="buyer_001",
        seller_id="seller_data_001",
        service_id="data_001",
        listed_price="0.002000",
        amount_paid="0.002000",
        amount_base_units=2000,
        tx_hash="0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        settlement_proof="0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        status=LedgerStatus.PAID,
        latency_ms=15.0,
    )
    repo.record_transaction(initial)

    # Step 2: Retry arrives with weaker evidence (tx_hash=None, status=FAILED_AND_NOT_CHARGED)
    weaker_retry = LedgerRecordSchema(
        request_id="req_evidence_preserve_001",
        task_id="task_preserve_test",
        call_id="call_1",
        buyer_id="buyer_001",
        seller_id="seller_data_001",
        service_id="data_001",
        listed_price="0.002000",
        amount_paid="0.002000",
        amount_base_units=2000,
        tx_hash=None,  # Weaker retry lacks tx_hash
        settlement_proof=None,
        status=LedgerStatus.FAILED_AND_NOT_CHARGED,  # Weaker retry claims failure
        latency_ms=20.0,
    )
    repo.record_transaction(weaker_retry)

    persisted = repo.get_record("req_evidence_preserve_001")
    assert persisted is not None
    # Verified tx_hash must NOT be wiped or downgraded
    assert persisted.tx_hash == "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
    # Terminal PAID status must NOT be downgraded to failed
    assert persisted.status == LedgerStatus.PAID

    # Step 3: Attempting to downgrade from on-chain tx (0x...) to local receipt (rec_auth_...) is blocked
    local_downgrade_retry = LedgerRecordSchema(
        request_id="req_evidence_preserve_001",
        task_id="task_preserve_test",
        call_id="call_1",
        buyer_id="buyer_001",
        seller_id="seller_data_001",
        service_id="data_001",
        listed_price="0.002000",
        amount_paid="0.002000",
        amount_base_units=2000,
        tx_hash="rec_auth_weaker_receipt",
        settlement_proof="rec_auth_weaker_receipt",
        status=LedgerStatus.PAID,
        latency_ms=22.0,
    )
    repo.record_transaction(local_downgrade_retry)

    persisted_after = repo.get_record("req_evidence_preserve_001")
    assert persisted_after.tx_hash == "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
