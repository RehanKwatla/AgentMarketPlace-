"""Automated Tests for the Contract Verified Reconciliation Feature."""
import asyncio
import pytest
from unittest.mock import patch
from fastapi import status
from backend.shared.constants import (
    LedgerStatus,
    NETWORK_BASE_SEPOLIA,
    USDC_BASE_SEPOLIA,
)
from backend.shared.errors import (
    LedgerInconsistencyError,
    SettlementUnverifiedError,
)
from backend.shared.schemas import (
    PaymentReconciliationInput,
    SettlementReceipt,
)
from backend.ledger.models import ledger_repo
from backend.ledger.reconciliation import reconciler


@pytest.fixture(autouse=True)
def clean_ledger():
    """Ensure clean ledger state for reconciliation tests."""
    ledger_repo.clear()
    reconciler._failed_reputation_updates.clear()
    reconciler.reputation_calc._pending_repairs.clear()
    yield
    ledger_repo.clear()
    reconciler._failed_reputation_updates.clear()
    reconciler.reputation_calc._pending_repairs.clear()



@pytest.mark.asyncio
async def test_reconciled_payment_creates_one_ledger_entry():
    """1. A successfully reconciled payment creates one ledger entry."""
    req_id = "req_reconcile_success_001"
    tx_hash = "0x" + "a" * 64
    payload = PaymentReconciliationInput(
        request_id=req_id,
        service_id="data_001",
        buyer_id="buyer_test_01",
        seller_id="seller_data_01",
        amount_paid_units=2000,
        listed_price_units=2000,
        tx_hash=tx_hash,
        network=NETWORK_BASE_SEPOLIA,
        token=USDC_BASE_SEPOLIA,
        task_id="task_test_001",
        latency_ms=125.5,
        output_valid=True,
    )

    result = await reconciler.reconcile_payment(payload)
    assert result.reconciled is True
    assert result.status == LedgerStatus.PAID
    assert result.is_duplicate is False
    assert result.ledger_record is not None
    assert result.ledger_record.request_id == req_id
    assert result.ledger_record.status == LedgerStatus.PAID
    assert result.ledger_record.amount_paid_units == 2000
    assert result.ledger_record.amount_paid == "0.002000"
    assert result.ledger_record.tx_hash == tx_hash

    # Verify queryable from repository
    stored = ledger_repo.get_record(req_id)
    assert stored is not None
    assert stored.request_id == req_id
    assert stored.status == LedgerStatus.PAID


@pytest.mark.asyncio
async def test_reprocessing_same_paid_payment_does_not_create_duplicates():
    """2. Reprocessing the same PAID payment does not create duplicates."""
    req_id = "req_reprocess_idempotent_001"
    tx_hash = "0x" + "b" * 64
    payload = PaymentReconciliationInput(
        request_id=req_id,
        service_id="data_001",
        buyer_id="buyer_test_01",
        seller_id="seller_data_01",
        amount_paid_units=2000,
        listed_price_units=2000,
        tx_hash=tx_hash,
        latency_ms=95.0,
    )

    # First reconciliation
    res1 = await reconciler.reconcile_payment(payload)
    assert res1.reconciled is True
    assert res1.is_duplicate is False

    # Second reconciliation of the exact same payment
    res2 = await reconciler.reconcile_payment(payload)
    assert res2.reconciled is True
    assert res2.status == LedgerStatus.PAID
    assert res2.is_duplicate is True
    assert res2.ledger_record is not None

    # Count of records with this request_id must remain 1
    stored = ledger_repo.get_record(req_id)
    assert stored is not None
    assert stored.request_id == req_id


@pytest.mark.asyncio
async def test_concurrent_reconciliation_does_not_create_duplicate_entries():
    """3. Concurrent reconciliation does not create duplicate entries."""
    req_id = "req_concurrent_stress_001"
    tx_hash = "0x" + "c" * 64
    payload = PaymentReconciliationInput(
        request_id=req_id,
        service_id="scraping_001",
        buyer_id="buyer_concurrent_01",
        seller_id="seller_scraping_01",
        amount_paid_units=3000,
        listed_price_units=3000,
        tx_hash=tx_hash,
        latency_ms=210.0,
    )

    # Launch 10 simultaneous reconciliation requests
    tasks = [reconciler.reconcile_payment(payload) for _ in range(10)]
    results = await asyncio.gather(*tasks)

    # All should succeed in reconciling
    for res in results:
        assert res.reconciled is True
        assert res.status == LedgerStatus.PAID
        assert res.ledger_record.request_id == req_id

    # Exactly 1 should be the original insert; the other 9 should be duplicates
    originals = [r for r in results if not r.is_duplicate]
    duplicates = [r for r in results if r.is_duplicate]
    assert len(originals) == 1
    assert len(duplicates) == 9

    # Exactly one record exists in repo
    record = ledger_repo.get_record(req_id)
    assert record is not None
    assert record.amount_paid_units == 3000


@pytest.mark.asyncio
async def test_ledger_fields_match_reconciled_payment():
    """4. Ledger fields match the reconciled payment."""
    req_id = "req_field_match_001"
    tx_hash = "0x" + "d" * 64
    payload = PaymentReconciliationInput(
        request_id=req_id,
        service_id="inference_001",
        buyer_id="buyer_wallet_abc",
        seller_id="seller_wallet_xyz",
        amount_paid_units=4000,
        listed_price_units=4000,
        tx_hash=tx_hash,
        network=NETWORK_BASE_SEPOLIA,
        token=USDC_BASE_SEPOLIA,
        task_id="task_session_99",
        latency_ms=450.2,
        output_valid=True,
    )

    result = await reconciler.reconcile_payment(payload)
    rec = result.ledger_record
    assert rec.request_id == payload.request_id
    assert rec.service_id == payload.service_id
    assert rec.buyer_id == payload.buyer_id
    assert rec.seller_id == payload.seller_id
    assert rec.task_id == payload.task_id
    assert rec.tx_hash == payload.tx_hash
    assert rec.network == payload.network
    assert rec.token == payload.token
    assert rec.amount_paid_units == 4000
    assert rec.amount_paid == "0.004000"
    assert rec.listed_price_units == 4000
    assert rec.listed_price == "0.004000"
    assert rec.latency_ms == 450.2
    assert rec.status == LedgerStatus.PAID


@pytest.mark.asyncio
async def test_seller_reputation_metrics_update_correctly():
    """5. Seller reputation metrics update correctly."""
    service_id = "test_rep_service_01"

    # Baseline before calls
    rep_before = reconciler.reputation_calc.calculate_for_service(service_id)
    assert rep_before.total_calls == 0
    assert rep_before.successful_calls == 0

    # 1st call: PAID
    await reconciler.reconcile_payment(
        PaymentReconciliationInput(
            request_id="req_rep_001",
            service_id=service_id,
            buyer_id="buyer_01",
            seller_id="seller_01",
            amount_paid_units=2000,
            listed_price_units=2000,
            tx_hash="0x" + "e" * 64,
            latency_ms=100.0,
        )
    )

    rep1 = reconciler.reputation_calc.calculate_for_service(service_id)
    assert rep1.total_calls == 1
    assert rep1.successful_calls == 1
    assert rep1.success_rate == 1.0
    assert rep1.total_volume_units == 2000
    assert rep1.total_volume_usdc == "0.002000"
    assert rep1.median_latency_ms == 100.0
    assert rep1.reputation_score == 100.0

    # 2nd call: PAID
    await reconciler.reconcile_payment(
        PaymentReconciliationInput(
            request_id="req_rep_002",
            service_id=service_id,
            buyer_id="buyer_01",
            seller_id="seller_01",
            amount_paid_units=3000,
            listed_price_units=3000,
            tx_hash="0x" + "f" * 64,
            latency_ms=200.0,
        )
    )

    rep2 = reconciler.reputation_calc.calculate_for_service(service_id)
    assert rep2.total_calls == 2
    assert rep2.successful_calls == 2
    assert rep2.success_rate == 1.0
    assert rep2.total_volume_units == 5000
    assert rep2.total_volume_usdc == "0.005000"
    assert rep2.median_latency_ms == 150.0  # Median of 100 and 200


@pytest.mark.asyncio
async def test_failed_and_pending_payments_do_not_count_as_successful():
    """6. Failed and pending payments do not count as successful."""
    service_id = "test_fail_service_01"

    # Case A: Pending settlement without proof
    pending_payload = PaymentReconciliationInput(
        request_id="req_pending_001",
        service_id=service_id,
        buyer_id="buyer_01",
        seller_id="seller_01",
        amount_paid_units=2000,
        listed_price_units=2000,
        # No tx_hash, proof_header, or receipt
    )

    # Unverified settlement without strict flag returns pending result
    res_pending = await reconciler.reconcile_payment(pending_payload, strict=False)
    assert res_pending.reconciled is False
    assert res_pending.status != LedgerStatus.PAID

    # Under strict mode, raises SettlementUnverifiedError
    with pytest.raises(SettlementUnverifiedError):
        await reconciler.reconcile_payment(pending_payload, strict=True)

    # Case B: Confirmed failed execution
    failed_payload = PaymentReconciliationInput(
        request_id="req_failed_001",
        service_id=service_id,
        buyer_id="buyer_01",
        seller_id="seller_01",
        amount_paid_units=2000,
        listed_price_units=2000,
        error_reason="Provider crashed with 500 Internal Error before settlement",
    )
    res_failed = await reconciler.reconcile_payment(failed_payload)
    assert res_failed.reconciled is True
    assert res_failed.status == LedgerStatus.FAILED_AND_NOT_CHARGED

    # Verify reputation does NOT count failed payment as successful
    rep = reconciler.reputation_calc.calculate_for_service(service_id)
    assert rep.total_calls == 1
    assert rep.successful_calls == 0
    assert rep.failure_counts == 1
    assert rep.success_rate == 0.0
    assert rep.total_volume_units == 0


@pytest.mark.asyncio
async def test_reputation_update_failure_retryable_recovery():
    """7. A reputation-update failure can be retried without duplicating the ledger entry."""
    service_id = "test_retry_rep_service_01"
    req_id = "req_rep_fail_retry_001"
    tx_hash = "0x" + "1" * 64

    payload = PaymentReconciliationInput(
        request_id=req_id,
        service_id=service_id,
        buyer_id="buyer_01",
        seller_id="seller_01",
        amount_paid_units=2000,
        listed_price_units=2000,
        tx_hash=tx_hash,
    )

    # Simulate database / network failure during reputation update
    with patch.object(
        reconciler.reputation_calc,
        "update_for_service",
        side_effect=RuntimeError("Simulated DB lock timeout")
    ):
        result = await reconciler.reconcile_payment(payload)

    # Ledger entry was committed successfully
    assert result.reconciled is True
    assert result.status == LedgerStatus.PAID
    assert result.ledger_record is not None
    assert result.reputation_repair_needed is True
    assert service_id in reconciler.get_pending_repairs()

    # Ledger record exists in repository
    assert ledger_repo.get_record(req_id) is not None

    # Now execute the retryable recovery mechanism
    repaired_metrics = reconciler.repair_reputation(service_id)
    assert repaired_metrics.service_id == service_id
    assert repaired_metrics.successful_calls == 1
    assert service_id not in reconciler.get_pending_repairs()

    # Ensure ledger entry was NOT duplicated upon recovery
    records = ledger_repo.list_records(service_id=service_id)
    assert len(records) == 1
    assert records[0].request_id == req_id


@pytest.mark.asyncio
async def test_inconsistent_payment_and_ledger_data_detected():
    """8. Inconsistent payment and ledger data is detected and handled safely."""
    req_id = "req_inconsistency_test_001"
    tx_hash = "0x" + "2" * 64

    # Seed initial reconciled record
    await reconciler.reconcile_payment(
        PaymentReconciliationInput(
            request_id=req_id,
            service_id="data_001",
            buyer_id="buyer_alice",
            seller_id="seller_bob",
            amount_paid_units=2000,
            listed_price_units=2000,
            tx_hash=tx_hash,
        )
    )

    # 1. Service ID conflict
    with pytest.raises(LedgerInconsistencyError) as exc_service:
        await reconciler.reconcile_payment(
            PaymentReconciliationInput(
                request_id=req_id,
                service_id="inference_001",  # Inconsistent!
                buyer_id="buyer_alice",
                seller_id="seller_bob",
                amount_paid_units=2000,
                listed_price_units=2000,
                tx_hash=tx_hash,
            )
        )
    assert "Service ID mismatch" in str(exc_service.value)

    # 2. Buyer ID conflict
    with pytest.raises(LedgerInconsistencyError) as exc_buyer:
        await reconciler.reconcile_payment(
            PaymentReconciliationInput(
                request_id=req_id,
                service_id="data_001",
                buyer_id="buyer_charlie",  # Inconsistent!
                seller_id="seller_bob",
                amount_paid_units=2000,
                listed_price_units=2000,
                tx_hash=tx_hash,
            )
        )
    assert "Buyer ID mismatch" in str(exc_buyer.value)

    # 3. Amount paid conflict
    with pytest.raises(LedgerInconsistencyError) as exc_amount:
        await reconciler.reconcile_payment(
            PaymentReconciliationInput(
                request_id=req_id,
                service_id="data_001",
                buyer_id="buyer_alice",
                seller_id="seller_bob",
                amount_paid_units=5000,  # Inconsistent!
                listed_price_units=2000,
                tx_hash=tx_hash,
            )
        )
    assert "Amount mismatch" in str(exc_amount.value)

    # 4. Transaction hash conflict
    with pytest.raises(LedgerInconsistencyError) as exc_hash:
        await reconciler.reconcile_payment(
            PaymentReconciliationInput(
                request_id=req_id,
                service_id="data_001",
                buyer_id="buyer_alice",
                seller_id="seller_bob",
                amount_paid_units=2000,
                listed_price_units=2000,
                tx_hash="0x" + "9" * 64,  # Conflicting hash!
            )
        )
    assert "Transaction hash conflict" in str(exc_hash.value)


def test_reconciliation_api_endpoints(client):
    """Test REST API endpoints for reconciliation and reputation recovery."""
    req_id = "req_api_reconcile_001"
    tx_hash = "0x" + "3" * 64

    # 1. Reconcile via POST /api/v1/ledger/reconcile
    resp = client.post(
        "/api/v1/ledger/reconcile",
        json={
            "request_id": req_id,
            "service_id": "data_001",
            "buyer_id": "buyer_api_01",
            "seller_id": "seller_api_01",
            "amount_paid_units": 2000,
            "listed_price_units": 2000,
            "tx_hash": tx_hash,
            "network": NETWORK_BASE_SEPOLIA,
            "token": USDC_BASE_SEPOLIA,
        }
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["reconciled"] is True
    assert data["status"] == "paid"

    # 2. Query ledger via GET /api/v1/ledger/{req_id}
    rec_resp = client.get(f"/api/v1/ledger/{req_id}")
    assert rec_resp.status_code == status.HTTP_200_OK
    assert rec_resp.json()["request_id"] == req_id
    assert rec_resp.json()["status"] == "paid"
    assert rec_resp.json()["amount_paid_units"] == 2000

    # 3. Query pending repairs via GET /api/v1/reputation/pending-repairs
    repairs_resp = client.get("/api/v1/reputation/pending-repairs")
    assert repairs_resp.status_code == status.HTTP_200_OK
    assert isinstance(repairs_resp.json(), list)

    # 4. Trigger recovery via POST /api/v1/reputation/repair/data_001
    repair_post = client.post("/api/v1/reputation/repair/data_001")
    assert repair_post.status_code == status.HTTP_200_OK
    assert repair_post.json()["service_id"] == "data_001"
