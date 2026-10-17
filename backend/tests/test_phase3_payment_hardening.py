"""Tests for Phase 3 Payment Engine Hardening (Member 1).

Covers:
1. Turnkey Seller Verifier Dependency & Helper (`backend/payments/dependencies.py`).
2. Live Facilitator Receipt Verification via HTTP client (`SettlementVerifier._verify_facilitator_receipt`).
3. Batch Reconciliation Engine (`PaymentService.reconcile_all_pending`).
4. Payment Subsystem Batch Reconciliation Route (`POST /api/v1/payments/reconcile`).
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from httpx import Response

from backend.payments.dependencies import get_seller_payment_verifier, verify_seller_payment
from backend.payments.settlement import SettlementVerifier, SellerPaymentVerifier
from backend.payments.service import PaymentService
from backend.payments.models import DurablePaymentRepository, PaymentAttemptModel
from backend.payments.schemas import PaymentStatus, PaymentAttemptRecord
from backend.payments.errors import SettlementVerificationError
from backend.shared.schemas import PaymentPayload, SettlementReceipt
from backend.shared.constants import NETWORK_BASE_SEPOLIA, USDC_BASE_SEPOLIA
from backend.database.session import SessionLocal, Base, engine


# ==============================================================================
# 1. Turnkey Seller Verifier Helper Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_verify_seller_payment_none_payload_returns_none():
    """Missing or empty X-402-Payment-Payload header must return None so route issues 402 challenge."""
    result = await verify_seller_payment(
        service_id="data_001",
        amount_units=2000,
        pay_to="0xSellerAddress",
        payment_payload_header=None,
    )
    assert result is None

    result_empty = await verify_seller_payment(
        service_id="data_001",
        amount_units=2000,
        pay_to="0xSellerAddress",
        payment_payload_header="",
    )
    assert result_empty is None


@pytest.mark.asyncio
async def test_verify_seller_payment_malformed_json_raises_402():
    """Malformed payment payload header must fail-closed with HTTP 402."""
    with pytest.raises(HTTPException) as exc_info:
        await verify_seller_payment(
            service_id="data_001",
            amount_units=2000,
            pay_to="0xSellerAddress",
            payment_payload_header="invalid_non_json_string",
        )
    assert exc_info.value.status_code == 402
    assert "Invalid x402 payment payload format" in exc_info.value.detail


@pytest.mark.asyncio
async def test_verify_seller_payment_valid_payload_returns_proof():
    """Valid payment payload verified by SellerPaymentVerifier must return settlement proof string."""
    mock_verifier = MagicMock(spec=SellerPaymentVerifier)
    mock_verifier.issue_challenge.return_value = MagicMock()
    mock_verifier.verify_and_settle = AsyncMock(
        return_value=SettlementReceipt(
            tx_hash=None,
            facilitator_receipt_id="rec_verified_123456",
            settled_amount_units=2000,
        )
    )

    valid_payload_dict = {
        "authorization": {"network": NETWORK_BASE_SEPOLIA, "amount": 2000},
        "signature": "0x1234567890abcdef",
        "buyer_address": "0xBuyerAddress",
    }

    proof = await verify_seller_payment(
        service_id="data_001",
        amount_units=2000,
        pay_to="0xSellerAddress",
        payment_payload_header=json.dumps(valid_payload_dict),
        verifier=mock_verifier,
    )

    assert proof == "rec_verified_123456"
    mock_verifier.verify_and_settle.assert_called_once()


@pytest.mark.asyncio
async def test_verify_seller_payment_verification_rejection_raises_402():
    """Rejected settlement verification must fail-closed with HTTP 402."""
    mock_verifier = MagicMock(spec=SellerPaymentVerifier)
    mock_verifier.issue_challenge.return_value = MagicMock()
    mock_verifier.verify_and_settle = AsyncMock(
        side_effect=SettlementVerificationError("Invalid transaction signature or unauthorized payer.")
    )

    valid_payload_dict = {
        "authorization": {"network": NETWORK_BASE_SEPOLIA, "amount": 2000},
        "signature": "0x1234567890abcdef",
        "buyer_address": "0xBuyerAddress",
    }

    with pytest.raises(HTTPException) as exc_info:
        await verify_seller_payment(
            service_id="data_001",
            amount_units=2000,
            pay_to="0xSellerAddress",
            payment_payload_header=json.dumps(valid_payload_dict),
            verifier=mock_verifier,
        )

    assert exc_info.value.status_code == 402
    assert "Payment settlement verification rejected" in exc_info.value.detail


# ==============================================================================
# 2. Live Facilitator Receipt Verification Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_facilitator_receipt_verification_test_mode():
    """In test mode, valid length receipt IDs pass without HTTP query."""
    verifier = SettlementVerifier(test_mode=True)
    is_valid, receipt_id = await verifier._verify_facilitator_receipt("rec_test_1234")
    assert is_valid is True
    assert receipt_id == "rec_test_1234"

    is_valid, _ = await verifier._verify_facilitator_receipt("short")
    assert is_valid is False


@pytest.mark.asyncio
async def test_facilitator_receipt_verification_live_mode_success():
    """Live mode queries facilitator endpoint and succeeds when status is confirmed/settled."""
    verifier = SettlementVerifier(
        facilitator_url="https://x402.example.com/api",
        test_mode=False,
    )

    mock_response = Response(
        status_code=200,
        content=json.dumps({"status": "confirmed", "receipt_id": "rec_live_abc123"}).encode("utf-8"),
        request=MagicMock(),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        is_valid, receipt_id = await verifier._verify_facilitator_receipt("rec_live_abc123")
        assert is_valid is True
        assert receipt_id == "rec_live_abc123"
        mock_get.assert_called_once_with("https://x402.example.com/api/receipts/rec_live_abc123")


@pytest.mark.asyncio
async def test_facilitator_receipt_verification_live_mode_pending_or_failed():
    """Live mode returns False if status is non-settled or facilitator returns 404/500/timeout."""
    verifier = SettlementVerifier(
        facilitator_url="https://x402.example.com/api",
        test_mode=False,
    )

    # Subcase A: 200 OK but status is "pending"
    mock_resp_pending = Response(
        status_code=200,
        content=json.dumps({"status": "pending"}).encode("utf-8"),
        request=MagicMock(),
    )
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp_pending
        is_valid, _ = await verifier._verify_facilitator_receipt("rec_pending_123")
        assert is_valid is False

    # Subcase B: HTTP 404 Not Found
    mock_resp_404 = Response(status_code=404, request=MagicMock())
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp_404
        is_valid, _ = await verifier._verify_facilitator_receipt("rec_missing_123")
        assert is_valid is False

    # Subcase C: Network error / Timeout
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, side_effect=Exception("Connection timed out")):
        is_valid, _ = await verifier._verify_facilitator_receipt("rec_err_123")
        assert is_valid is False


# ==============================================================================
# 3. Batch Reconciliation Engine Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_reconcile_all_pending_batches_in_memory_and_durable():
    """reconcile_all_pending iterates all unresolved suspense attempts across memory and database."""
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        session.query(PaymentAttemptModel).delete()
        session.commit()

    repo = DurablePaymentRepository(session_factory=SessionLocal)
    service = PaymentService(durable_repo=repo)
    service.settlement_verifier = SettlementVerifier(test_mode=True)

    # 1. Setup in-memory suspense attempt
    att1 = PaymentAttemptRecord(
        attempt_id="att_batch_001",
        task_id="task_batch_1",
        call_id="call_batch_1",
        service_id="data_001",
        idempotency_key="key_batch_001",
        request_hash="hash_001",
        nonce="nonce_batch_001",
        amount_base_units=2000,
        pay_to="0xSellerData",
        status=PaymentStatus.PENDING_RECONCILIATION,
        tx_hash="0x" + "a" * 64,
        settlement_proof="0x" + "a" * 64,
    )
    service._pending_reconciliations["att_batch_001"] = att1
    repo.save_attempt(att1)

    # 2. Setup durable DB-only suspense attempt
    att2 = PaymentAttemptRecord(
        attempt_id="att_batch_002",
        task_id="task_batch_2",
        call_id="call_batch_2",
        service_id="scraping_001",
        idempotency_key="key_batch_002",
        request_hash="hash_002",
        nonce="nonce_batch_002",
        amount_base_units=3000,
        pay_to="0xSellerScraping",
        status=PaymentStatus.PENDING_RECONCILIATION,
        tx_hash="0x" + "b" * 64,
        settlement_proof="0x" + "b" * 64,
    )
    repo.save_attempt(att2)

    # Execute batch reconciliation
    results = await service.reconcile_all_pending()

    assert len(results) == 2
    for r in results:
        assert r["reconciled"] is True
        assert r["status"] == PaymentStatus.PAID.value

    # Verify both attempts updated in DB
    db_att1 = repo.get_attempt_by_id("att_batch_001")
    db_att2 = repo.get_attempt_by_id("att_batch_002")
    assert db_att1.status == PaymentStatus.PAID.value
    assert db_att2.status == PaymentStatus.PAID.value


# ==============================================================================
# 4. Batch Reconciliation API Route Tests
# ==============================================================================

def test_reconcile_batch_route(client):
    """POST /api/v1/payments/reconcile triggers batch reconciliation and returns summary."""
    from backend.payments.service import payment_service

    # Inject a test suspense attempt into global payment_service
    test_attempt = PaymentAttemptRecord(
        attempt_id="att_route_reconcile_test",
        task_id="task_route_test",
        call_id="call_route_test",
        service_id="data_001",
        idempotency_key="key_route_reconcile",
        request_hash="hash_route",
        nonce="nonce_route_reconcile",
        amount_base_units=2000,
        pay_to="0xSeller",
        status=PaymentStatus.PENDING_RECONCILIATION,
        tx_hash="0x" + "c" * 64,
        settlement_proof="0x" + "c" * 64,
    )
    payment_service._pending_reconciliations["att_route_reconcile_test"] = test_attempt

    resp = client.post("/api/v1/payments/reconcile")
    assert resp.status_code == 200
    data = resp.json()
    assert "reconciled_attempts" in data
    assert "total" in data
    assert any(r["attempt_id"] == "att_route_reconcile_test" for r in data["reconciled_attempts"])
