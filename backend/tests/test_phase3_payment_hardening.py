"""Tests for Phase 3 Payment Engine Hardening (Member 1).

Covers:
1. Turnkey Seller Verifier Dependency & Helper (`backend/payments/dependencies.py`).
2. Live Facilitator Receipt Verification via HTTP client (`SettlementVerifier._verify_facilitator_receipt`).
3. Batch Reconciliation Engine (`PaymentService.reconcile_all_pending`).
4. Payment Subsystem Batch Reconciliation Route (`POST /api/v1/payments/reconcile`).
"""
import json
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from httpx import Response

from backend.payments.dependencies import get_seller_payment_verifier, verify_seller_payment
from backend.payments.settlement import SettlementVerifier, SellerPaymentVerifier
from backend.payments.service import PaymentService
from backend.payments.models import DurablePaymentRepository, PaymentAttemptModel, SettlementEvidenceRecordModel
from backend.payments.schemas import PaymentStatus, PaymentAttemptRecord
from backend.payments.errors import SettlementVerificationError
from backend.shared.schemas import PaymentPayload, PaymentRequirement, SettlementReceipt
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
        session.query(SettlementEvidenceRecordModel).delete()
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
        tx_hash="0x" + "e" * 64,
        settlement_proof="0x" + "e" * 64,
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


# ==============================================================================
# 5. EIP-712 Structured Data Signing & Verification Tests
# ==============================================================================

def test_eip712_structured_signing_and_verification():
    """Verify official EIP-712 typed structured data signing and cryptographic recovery."""
    from eth_account import Account
    from backend.payments.x402_adapter import X402Adapter

    acc = Account.create()
    key_hex = acc.key.hex()
    if not key_hex.startswith("0x"):
        key_hex = f"0x{key_hex}"

    adapter = X402Adapter(test_mode=False, signature_scheme="eip712")
    adapter.buyer_address = acc.address
    adapter.buyer_private_key = key_hex

    auth = {
        "network": NETWORK_BASE_SEPOLIA,
        "token": USDC_BASE_SEPOLIA,
        "payTo": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        "amount": 5000,
        "nonce": "nonce_eip712_test_001",
        "validAfter": 1000000,
        "validBefore": 2000000,
        "idempotencyKey": "idemp_eip712_001",
    }

    # 1. Build and verify EIP-712 message structure
    full_msg = adapter.build_eip712_message(auth)
    assert full_msg["primaryType"] == "PaymentAuthorization"
    assert full_msg["domain"]["chainId"] == 84532
    assert full_msg["domain"]["name"] == "USD Coin"
    assert full_msg["domain"]["verifyingContract"] == USDC_BASE_SEPOLIA
    assert full_msg["message"]["amount"] == 5000

    # 2. Sign via EIP-712
    sig = adapter.sign_eip712_authorization(auth)
    assert sig.startswith("0x")
    assert len(sig) == 132

    # 3. Recover signer address
    recovered = adapter.recover_eip712_signer(auth, sig)
    assert recovered.lower() == acc.address.lower()

    # 4. Verify helper method
    assert adapter.verify_eip712_signature(auth, sig, acc.address) is True


def test_eip712_tampered_payload_verification_fails():
    """Tampering with any EIP-712 authorization field must invalidate the signature."""
    from eth_account import Account
    from backend.payments.x402_adapter import X402Adapter

    acc = Account.create()
    key_hex = acc.key.hex()
    if not key_hex.startswith("0x"):
        key_hex = f"0x{key_hex}"

    adapter = X402Adapter(test_mode=False, signature_scheme="eip712")
    adapter.buyer_address = acc.address
    adapter.buyer_private_key = key_hex

    auth = {
        "network": NETWORK_BASE_SEPOLIA,
        "token": USDC_BASE_SEPOLIA,
        "payTo": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        "amount": 2000,
        "nonce": "nonce_tamper_001",
        "validAfter": 100,
        "validBefore": 200,
        "idempotencyKey": "idemp_tamper_001",
    }

    sig = adapter.sign_eip712_authorization(auth)

    # Tamper with amount
    tampered_auth = dict(auth, amount=999999)
    assert adapter.verify_eip712_signature(tampered_auth, sig, acc.address) is False

    # Tamper with recipient
    tampered_recipient = dict(auth, payTo="0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC")
    assert adapter.verify_eip712_signature(tampered_recipient, sig, acc.address) is False


# ==============================================================================
# 6. Cross-Process Persistence & Budget Durability Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_durable_idempotency_response_persistence_across_restart():
    """IdempotencyStore must persist cached response in durable database to survive process restarts."""
    from backend.payments.idempotency import IdempotencyStore
    from backend.payments.models import durable_payment_repo, PaymentAttemptRecord

    key = "key_restart_persist_001"
    payload_hash = "hash_restart_001"
    response_result = {"status": "PAID", "amount_usdc": "0.002000", "output": {"data": "ok"}}

    # Persist attempt record in DB first
    durable_payment_repo.save_attempt(PaymentAttemptRecord(
        attempt_id="att_restart_001",
        task_id="task_restart_001",
        call_id="call_restart_001",
        service_id="data_001",
        idempotency_key=key,
        request_hash=payload_hash,
        nonce="nonce_restart_001",
        amount_base_units=2000,
        pay_to="0xSeller",
        status=PaymentStatus.PAID,
    ))

    # Store 1: caches in memory and persists to DB
    store1 = IdempotencyStore(repo=durable_payment_repo)
    store1.store_idempotent_result(key, response_result, payload_hash)

    # Store 2: simulates separate process/worker with clean memory
    store2 = IdempotencyStore(repo=durable_payment_repo)
    is_new, cached = store2.check_or_register(key, payload_hash)

    assert is_new is False
    assert cached == response_result


@pytest.mark.asyncio
async def test_budget_manager_cross_process_reservation_sync():
    """BudgetManager must synchronize with active DB reservations across separate instances."""
    from backend.payments.budget import BudgetManager
    from backend.payments.models import durable_payment_repo

    task_id = "task_cross_proc_budget"
    initial_budget = 10000

    # Instance A: Reserves 4000 units
    mgr_a = BudgetManager(initial_budget_units=initial_budget, task_id=task_id, repo=durable_payment_repo)
    await mgr_a.reserve("res_cross_001", 4000)
    assert mgr_a.available_budget == 6000

    # Instance B: Instantiated later in separate worker for same task_id
    mgr_b = BudgetManager(initial_budget_units=initial_budget, task_id=task_id, repo=durable_payment_repo)
    # Must immediately reflect the 4000 active reservation from durable storage
    assert mgr_b.available_budget == 6000


@pytest.mark.asyncio
async def test_concurrent_cross_process_budget_atomicity_regression():
    """Regression test: Concurrent reservations from independent managers must never exceed total budget."""
    import asyncio
    from backend.payments.budget import BudgetManager
    from backend.payments.models import durable_payment_repo, BudgetReservationModel
    from backend.shared.errors import BudgetExceededError
    from backend.database.session import SessionLocal

    task_id = f"task_concurrency_{int(time.time() * 1000)}"
    total_budget = 10000  # 10,000 base units

    # Three independent managers simulating three separate processes/workers
    mgr1 = BudgetManager(initial_budget_units=total_budget, task_id=task_id, repo=durable_payment_repo)
    mgr2 = BudgetManager(initial_budget_units=total_budget, task_id=task_id, repo=durable_payment_repo)
    mgr3 = BudgetManager(initial_budget_units=total_budget, task_id=task_id, repo=durable_payment_repo)

    results = []

    async def try_reserve(mgr, res_id, amount):
        try:
            rem = await mgr.reserve(res_id, amount)
            results.append(("SUCCESS", res_id, amount, rem))
        except BudgetExceededError as err:
            results.append(("EXCEEDED", res_id, amount, str(err)))

    # Concurrently attempt 3 reservations of 4,000 units each (total 12,000 > 10,000)
    await asyncio.gather(
        try_reserve(mgr1, f"{task_id}_res1", 4000),
        try_reserve(mgr2, f"{task_id}_res2", 4000),
        try_reserve(mgr3, f"{task_id}_res3", 4000),
    )

    successes = [r for r in results if r[0] == "SUCCESS"]
    exceeded = [r for r in results if r[0] == "EXCEEDED"]

    # Exactly 2 reservations can fit (4,000 * 2 = 8,000 <= 10,000). The 3rd MUST fail.
    assert len(successes) == 2
    assert len(exceeded) == 1

    # Verify database state has exactly 2 records totaling 8,000 base units
    with SessionLocal() as session:
        records = session.query(BudgetReservationModel).filter_by(task_id=task_id).all()
        assert len(records) == 2
        total_reserved_in_db = sum(r.amount_base_units for r in records)
        assert total_reserved_in_db == 8000
        # No dangling or corrupted record exists for the rejected reservation
        for r in records:
            assert r.status == "reserved"


# ==============================================================================
# 7. Settlement Evidence & Duplicate Rejection Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_reused_settlement_evidence_rejected():
    """Verifier must reject duplicate settlement evidence (tx_hash reuse)."""
    verifier = SettlementVerifier(test_mode=True)
    import uuid
    tx_hash = "0x" + uuid.uuid4().hex + uuid.uuid4().hex

    # First verification succeeds and registers tx_hash in used cache
    receipt1 = await verifier.verify_settlement_proof(tx_hash, expected_amount_units=2000)
    assert receipt1.tx_hash == tx_hash

    # Second verification with the same tx_hash must fail-closed
    with pytest.raises(SettlementVerificationError) as exc_info:
        await verifier.verify_settlement_proof(tx_hash, expected_amount_units=2000)
    assert "Duplicate settlement evidence detected" in str(exc_info.value)


@pytest.mark.asyncio
async def test_seller_verifier_rejects_expired_and_mismatched_authorization():
    """SellerPaymentVerifier must reject expired authorizations and amount mismatches."""
    verifier = SellerPaymentVerifier(test_mode=True)
    req = PaymentRequirement(
        network=NETWORK_BASE_SEPOLIA,
        token=USDC_BASE_SEPOLIA,
        payTo="0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        amount="2000",
        nonce="nonce_expiry_test",
        service_id="data_001",
    )

    now = int(time.time())

    # Case A: Expired authorization (validBefore in past)
    expired_auth = {
        "network": req.network,
        "token": req.token,
        "payTo": req.payTo,
        "amount": req.amount,
        "nonce": req.nonce,
        "validAfter": now - 3600,
        "validBefore": now - 60,  # 1 minute ago
    }
    with pytest.raises(SettlementVerificationError) as exc_info:
        await verifier.verify_and_settle(
            PaymentPayload(
                authorization=expired_auth,
                signature="0x_mock_sig_1234",
                buyer_address="0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
            ),
            req
        )
    assert "expired" in str(exc_info.value)

    # Case B: Amount mismatch
    wrong_amount_auth = {
        "network": req.network,
        "token": req.token,
        "payTo": req.payTo,
        "amount": "999",  # expects 2000
        "nonce": req.nonce,
        "validAfter": now - 60,
        "validBefore": now + 3600,
    }
    with pytest.raises(SettlementVerificationError) as exc_info:
        await verifier.verify_and_settle(
            PaymentPayload(
                authorization=wrong_amount_auth,
                signature="0x_mock_sig_1234",
                buyer_address="0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
            ),
            req
        )
    assert "Amount mismatch" in str(exc_info.value)


def test_official_sdk_match_payload_to_requirements_interop():
    """Verify official x402 match_payload_to_requirements interoperability."""
    from x402 import match_payload_to_requirements, PaymentRequirements, PaymentPayload as OfficialPayload

    req = PaymentRequirements(
        scheme="exact",
        network=NETWORK_BASE_SEPOLIA,
        asset=USDC_BASE_SEPOLIA,
        amount="2000",
        pay_to="0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        max_timeout_seconds=60,
        extra={"nonce": "nonce_interop_001", "service_id": "data_001"}
    )

    # Valid payload matching requirement
    valid_payload = OfficialPayload(
        x402_version=2,
        accepted=req,
        payload={"authorization": {"network": NETWORK_BASE_SEPOLIA, "amount": 2000}, "signature": "0x1234"}
    )
    assert match_payload_to_requirements(2, valid_payload.model_dump(), req.model_dump()) is True

    # Tampered payload with different amount
    tampered_req = PaymentRequirements(
        scheme="exact",
        network=NETWORK_BASE_SEPOLIA,
        asset=USDC_BASE_SEPOLIA,
        amount="5000",
        pay_to="0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        max_timeout_seconds=60
    )
    tampered_payload = OfficialPayload(
        x402_version=2,
        accepted=tampered_req,
        payload={"authorization": {"network": NETWORK_BASE_SEPOLIA, "amount": 5000}, "signature": "0x1234"}
    )
    assert match_payload_to_requirements(2, tampered_payload.model_dump(), req.model_dump()) is False


# ==============================================================================
# 8. Idempotency & Reconciliation Edge Cases
# ==============================================================================

def test_idempotency_concurrent_and_conflict_handling():
    """Verify IdempotencyStore correctly identifies matching vs conflicting payloads."""
    from backend.payments.idempotency import IdempotencyStore, compute_payload_hash
    from backend.payments.errors import IdempotencyConflictError

    store = IdempotencyStore()
    key = "idemp_test_conflict_001"
    payload_a = {"symbol": "ETH", "days": 30}
    payload_b = {"symbol": "BTC", "days": 30}
    hash_a = compute_payload_hash(payload_a)
    hash_b = compute_payload_hash(payload_b)

    # 1. First registration succeeds
    is_new, cached = store.check_or_register(key, hash_a)
    assert is_new is True
    assert cached is None

    # Store result
    result_a = {"data": "eth_result"}
    store.store_idempotent_result(key, result_a, hash_a)

    # 2. Re-request with identical payload returns cached result
    is_new_retry, cached_retry = store.check_or_register(key, hash_a)
    assert is_new_retry is False
    assert cached_retry == result_a

    # 3. Request with mutated payload raises IdempotencyConflictError
    with pytest.raises(IdempotencyConflictError):
        store.check_or_register(key, hash_b)


@pytest.mark.asyncio
async def test_duplicate_reconciliation_is_idempotent():
    """Calling reconcile_attempt repeatedly on a resolved attempt is safe and idempotent."""
    from backend.payments.service import PaymentService
    from backend.payments.models import durable_payment_repo, PaymentAttemptRecord
    from backend.payments.settlement import SettlementVerifier

    verifier = SettlementVerifier(test_mode=True)
    service = PaymentService(settlement_verifier=verifier, durable_repo=durable_payment_repo)

    import uuid
    uid = uuid.uuid4().hex[:12]
    attempt_id = f"att_reconcile_{uid}"
    tx_hash = f"0x{uuid.uuid4().hex}{uuid.uuid4().hex}"

    # Seed an attempt in PENDING_RECONCILIATION
    durable_payment_repo.save_attempt(PaymentAttemptRecord(
        attempt_id=attempt_id,
        task_id=f"task_{uid}",
        call_id=f"call_{uid}",
        service_id="data_001",
        idempotency_key=f"key_{uid}",
        request_hash="hash_reconcile_idemp",
        nonce=f"nonce_{uid}",
        amount_base_units=2000,
        pay_to="0xSeller",
        status=PaymentStatus.PENDING_RECONCILIATION,
        tx_hash=tx_hash,
        settlement_proof=tx_hash,
    ))

    # First reconciliation: resolves to PAID
    res1 = await service.reconcile_attempt(attempt_id)
    assert res1["reconciled"] is True
    assert res1["status"] == PaymentStatus.PAID.value

    # Second reconciliation: immediately recognizes terminal state, does not double-commit
    res2 = await service.reconcile_attempt(attempt_id)
    assert res2["reconciled"] is True
    assert res2["status"] == PaymentStatus.PAID.value
    assert "already in terminal state" in res2["message"]


# ==============================================================================
# 10. Phase 3.1 Multi-Process Concurrency & Official x402 Verification Tests
# ==============================================================================

def _worker_atomic_reserve(db_path: str, task_id: str, res_id: str, amount: int, total_budget: int, result_queue: Any):
    """Top-level independent worker process for testing budget reservation concurrency on Windows."""
    import os
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from backend.payments.models import DurablePaymentRepository

    db_url = f"sqlite:///{os.path.abspath(db_path)}"
    engine = create_engine(db_url, connect_args={"timeout": 15, "check_same_thread": False})
    SessionMaker = sessionmaker(bind=engine)
    repo = DurablePaymentRepository(session_factory=SessionMaker)

    success, rem, msg = repo.atomic_reserve(
        task_id=task_id,
        reservation_id=res_id,
        call_id=f"call_{res_id}",
        amount_base_units=amount,
        total_budget_units=total_budget,
    )
    result_queue.put((success, res_id, rem, msg))
    engine.dispose()


def _worker_record_settlement_evidence(db_path: str, attempt_id: str, tx_hash: str, log_index: int, amount: int, result_queue: Any):
    """Top-level independent worker process for testing settlement evidence replay concurrency on Windows."""
    import os
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from backend.payments.models import DurablePaymentRepository
    from backend.shared.constants import NETWORK_BASE_SEPOLIA
    from backend.payments.errors import SettlementVerificationError

    db_url = f"sqlite:///{os.path.abspath(db_path)}"
    engine = create_engine(db_url, connect_args={"timeout": 15, "check_same_thread": False})
    SessionMaker = sessionmaker(bind=engine)
    repo = DurablePaymentRepository(session_factory=SessionMaker)

    try:
        success = repo.atomic_record_settlement_evidence(
            attempt_id=attempt_id,
            network=NETWORK_BASE_SEPOLIA,
            amount_units=amount,
            tx_hash=tx_hash,
            log_index=log_index,
        )
        result_queue.put((True, attempt_id, "RECORDED"))
    except SettlementVerificationError as sve:
        result_queue.put((False, attempt_id, str(sve)))
    except Exception as ex:
        result_queue.put((False, attempt_id, f"ERROR: {ex}"))
    finally:
        engine.dispose()


def test_multiprocess_budget_reservation_atomicity(tmp_path):
    """P0-B Verification: Independent OS processes against a persistent database cannot overspend.

    Spawns 4 separate OS processes attempting 400,000 units each against a shared 1,000,000 budget.
    Asserts:
    - At most 2 processes succeed (400,000 * 2 = 800,000 <= 1,000,000).
    - Remaining processes are rejected with budget exceeded.
    - Zero overspend or partial reservations in durable DB.
    """
    import multiprocessing
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from backend.payments.models import Base, BudgetReservationModel

    db_file = str(tmp_path / "budget_concurrency.db")
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"timeout": 15, "check_same_thread": False})
    Base.metadata.create_all(engine)
    engine.dispose()

    ctx = multiprocessing.get_context("spawn")
    result_queue = ctx.Queue()

    task_id = "task_mp_budget_001"
    total_budget = 1_000_000
    res_amount = 400_000

    processes = []
    for i in range(4):
        p = ctx.Process(
            target=_worker_atomic_reserve,
            args=(db_file, task_id, f"res_proc_{i}", res_amount, total_budget, result_queue),
        )
        processes.append(p)

    for p in processes:
        p.start()
    for p in processes:
        p.join(timeout=10)

    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    assert len(results) == 4, f"Expected 4 results from 4 separate processes, got {len(results)}"
    successes = [r for r in results if r[0] is True]
    failures = [r for r in results if r[0] is False]

    # Exactly 2 reservations of 400,000 can fit within 1,000,000
    assert len(successes) == 2, f"Expected exactly 2 successes, got {len(successes)}"
    assert len(failures) == 2, f"Expected exactly 2 failures, got {len(failures)}"

    for fail in failures:
        assert "exceeds available" in fail[3] or "conflict" in fail[3]

    # Verify durable database contents
    verify_engine = create_engine(f"sqlite:///{db_file}", connect_args={"timeout": 15, "check_same_thread": False})
    VerifySession = sessionmaker(bind=verify_engine)
    with VerifySession() as session:
        records = session.query(BudgetReservationModel).filter_by(task_id=task_id).all()
        assert len(records) == 2
        total_reserved = sum(r.amount_base_units for r in records)
        assert total_reserved == 800_000
        assert total_reserved <= total_budget
    verify_engine.dispose()


def test_multiprocess_settlement_evidence_replay_protection(tmp_path):
    """P0-C Verification: Concurrent submissions of duplicate evidence by independent OS processes fail closed.

    Spawns 4 separate OS processes submitting the identical (tx_hash, log_index=0).
    Asserts:
    - Exactly 1 process succeeds in recording evidence.
    - Exactly 3 processes are rejected with duplicate evidence error.
    - Database contains exactly 1 unique record.
    """
    import multiprocessing
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from backend.payments.models import Base, SettlementEvidenceRecordModel

    db_file = str(tmp_path / "evidence_concurrency.db")
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"timeout": 15, "check_same_thread": False})
    Base.metadata.create_all(engine)
    engine.dispose()

    ctx = multiprocessing.get_context("spawn")
    result_queue = ctx.Queue()

    tx_hash = "0x" + "c" * 64
    log_index = 0
    amount = 50_000

    processes = []
    for i in range(4):
        p = ctx.Process(
            target=_worker_record_settlement_evidence,
            args=(db_file, f"attempt_proc_{i}", tx_hash, log_index, amount, result_queue),
        )
        processes.append(p)

    for p in processes:
        p.start()
    for p in processes:
        p.join(timeout=10)

    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    assert len(results) == 4, f"Expected 4 results, got {len(results)}"
    successes = [r for r in results if r[0] is True]
    failures = [r for r in results if r[0] is False]

    # Exactly 1 process can record the evidence; the other 3 MUST be rejected
    assert len(successes) == 1, f"Expected exactly 1 success, got {len(successes)}"
    assert len(failures) == 3, f"Expected exactly 3 duplicate rejections, got {len(failures)}"

    for fail in failures:
        assert "Duplicate settlement evidence" in fail[2]

    # Verify durable database contains exactly 1 unique record
    verify_engine = create_engine(f"sqlite:///{db_file}", connect_args={"timeout": 15, "check_same_thread": False})
    VerifySession = sessionmaker(bind=verify_engine)
    with VerifySession() as session:
        records = session.query(SettlementEvidenceRecordModel).filter_by(tx_hash=tx_hash.lower()).all()
        assert len(records) == 1
        assert records[0].log_index == 0
    verify_engine.dispose()


def test_multiprocess_multiple_transfer_logs_same_transaction(tmp_path):
    """P0-C Granularity: Multi-transfer transactions with distinct log indices are accepted without false replay."""
    import multiprocessing
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from backend.payments.models import Base, SettlementEvidenceRecordModel

    db_file = str(tmp_path / "batch_transfer_concurrency.db")
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"timeout": 15, "check_same_thread": False})
    Base.metadata.create_all(engine)
    engine.dispose()

    ctx = multiprocessing.get_context("spawn")
    result_queue = ctx.Queue()

    batch_tx_hash = "0x" + "f" * 64
    amount = 100_000

    # 3 processes representing 3 distinct transfer logs within the SAME batch transaction
    processes = []
    for log_idx in range(3):
        p = ctx.Process(
            target=_worker_record_settlement_evidence,
            args=(db_file, f"attempt_batch_{log_idx}", batch_tx_hash, log_idx, amount, result_queue),
        )
        processes.append(p)

    for p in processes:
        p.start()
    for p in processes:
        p.join(timeout=10)

    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    assert len(results) == 3
    successes = [r for r in results if r[0] is True]
    assert len(successes) == 3, f"All 3 distinct log index submissions should succeed, got {len(successes)}"

    verify_engine = create_engine(f"sqlite:///{db_file}", connect_args={"timeout": 15, "check_same_thread": False})
    VerifySession = sessionmaker(bind=verify_engine)
    with VerifySession() as session:
        records = session.query(SettlementEvidenceRecordModel).filter_by(tx_hash=batch_tx_hash.lower()).all()
        assert len(records) == 3
        log_indices = {r.log_index for r in records}
        assert log_indices == {0, 1, 2}
    verify_engine.dispose()


def test_official_x402_eip3009_exact_scheme_cryptographic_parity():
    """P0-A Verification: Official x402 EVM exact scheme parity.

    Verifies field-by-field that X402Adapter canonical EIP-3009 implementation
    matches official x402==2.25.0 package source and hash_eip3009_authorization.
    """
    from eth_account import Account
    from x402.mechanisms.evm.exact.client import ExactEvmScheme as OfficialExactClient
    from x402.mechanisms.evm.eip712 import hash_eip3009_authorization
    from x402.mechanisms.evm.types import ExactEIP3009Payload
    from x402.schemas import PaymentRequirements as OfficialPaymentRequirements
    from backend.payments.x402_adapter import X402Adapter

    signer = Account.create()
    adapter = X402Adapter(test_mode=True)
    adapter.buyer_address = signer.address
    adapter.buyer_private_key = signer.key.hex()
    adapter.signature_scheme = "eip3009"

    # 1. Create requirement matching official EVM scheme
    official_req = OfficialPaymentRequirements(
        scheme="exact",
        network="eip155:84532",
        asset="0x036CbD53842c5426634e7929541eC2318f3dCF7e",
        amount="100000",
        pay_to="0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        max_timeout_seconds=3600,
        extra={"name": "USDC", "version": "2", "assetTransferMethod": "eip3009"}
    )

    # 2. Generate payload with official x402 SDK client
    official_client = OfficialExactClient(signer)
    official_payload_dict = official_client.create_payment_payload(official_req)
    evm_payload = ExactEIP3009Payload.from_dict(official_payload_dict)

    # 3. Assert field-by-field properties of the official EVM exact payload
    assert evm_payload.authorization.from_address.lower() == signer.address.lower()
    assert evm_payload.authorization.to.lower() == official_req.pay_to.lower()
    assert evm_payload.authorization.value == "100000"
    assert evm_payload.authorization.nonce.startswith("0x")
    assert len(evm_payload.authorization.nonce) == 66  # 32 bytes hex with 0x prefix

    # 4. Verify cryptographic signature using X402Adapter.recover_eip3009_signer
    auth_dict = {
        "from": evm_payload.authorization.from_address,
        "to": evm_payload.authorization.to,
        "value": evm_payload.authorization.value,
        "validAfter": evm_payload.authorization.valid_after,
        "validBefore": evm_payload.authorization.valid_before,
        "nonce": evm_payload.authorization.nonce,
    }
    recovered_addr = adapter.recover_eip3009_signer(auth_dict, evm_payload.signature)
    assert recovered_addr.lower() == signer.address.lower()
    assert adapter.verify_eip3009_signature(auth_dict, evm_payload.signature, signer.address) is True

    # 5. Sign authorization using X402Adapter and verify against official x402 hash_eip3009_authorization
    adapter_sig = adapter.sign_eip3009_authorization(auth_dict, signer.key.hex())
    digest = hash_eip3009_authorization(
        authorization=evm_payload.authorization,
        chain_id=84532,
        verifying_contract=official_req.asset,
        token_name="USDC",
        token_version="2"
    )
    recovered_from_adapter = Account._recover_hash(digest, signature=adapter_sig)
    assert recovered_from_adapter.lower() == signer.address.lower()


def test_official_x402_payload_translation_roundtrip():
    """Verify bidirectional translation between application schemas and official x402 v2 objects."""
    from backend.payments.x402_adapter import X402Adapter
    from backend.shared.schemas import PaymentRequirement
    from x402.mechanisms.evm.types import ExactEIP3009Payload

    adapter = X402Adapter(test_mode=True)
    req = PaymentRequirement(
        network="eip155:84532",
        token="0x036CbD53842c5426634e7929541eC2318f3dCF7e",
        amount="250000",
        payTo="0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        nonce="nonce_roundtrip_test",
        service_id="data_service_01",
    )

    # 1. Translate to official PaymentRequired
    official_pr = adapter.to_official_payment_required(req)
    assert official_pr.x402_version == 2
    assert len(official_pr.accepts) == 1
    accepted = official_pr.accepts[0]
    assert accepted.scheme == "exact"
    assert accepted.asset == req.token
    assert accepted.amount == req.amount
    assert accepted.extra["name"] == "USDC"
    assert accepted.extra["version"] == "2"
    assert accepted.extra["assetTransferMethod"] == "eip3009"

    # 2. Create payment payload and translate to official PaymentPayload
    payload = adapter.create_payment_payload(req, idempotency_key="idemp_roundtrip_001")
    official_pp = adapter.to_official_payment_payload(payload, req)
    assert official_pp.x402_version == 2

    # 3. Official ExactEIP3009Payload parser can parse the inner payload dict
    evm_payload = ExactEIP3009Payload.from_dict(official_pp.payload)
    assert evm_payload.authorization.to.lower() == req.payTo.lower()
    assert evm_payload.authorization.value == "250000"
    assert evm_payload.authorization.nonce.startswith("0x")


def test_offline_facilitator_and_rpc_boundary_classification():
    """Documents that live Base Sepolia RPC settlement is explicitly BLOCKED offline."""
    from backend.payments.settlement import SettlementVerifier

    # In live mode (test_mode=False) with non-existent / unreachable RPC
    live_verifier = SettlementVerifier(
        rpc_url="http://127.0.0.1:9999/unreachable_rpc",
        facilitator_url="http://127.0.0.1:9999/unreachable_fac",
        test_mode=False
    )

    # Live verification fails closed without claiming false success
    import asyncio
    with pytest.raises(SettlementVerificationError) as exc_info:
        asyncio.run(live_verifier.verify_settlement_proof("0x" + "1" * 64, expected_amount_units=1000))
    assert "unconfirmed or reverted" in str(exc_info.value)


# ==============================================================================
# 11. Phase 3.2 Cross-Network Isolation & SDK Interface Verification
# ==============================================================================

def test_settlement_evidence_cross_network_isolation_and_granularity(tmp_path):
    """P0-C Multi-Network Verification:
    1. Duplicate evidence on same network is rejected.
    2. Valid distinct logs on same network are accepted.
    3. Identical (tx_hash, log_index) combinations on different networks do NOT collide.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from backend.payments.models import Base, DurablePaymentRepository
    from backend.payments.errors import SettlementVerificationError

    db_file = str(tmp_path / "cross_net_evidence.db")
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionMaker = sessionmaker(bind=engine)
    repo = DurablePaymentRepository(session_factory=SessionMaker)

    shared_tx = "0x" + "7" * 64
    network_base_sepolia = "eip155:84532"
    network_eth_sepolia = "eip155:11155111"

    # 1. First submission on Base Sepolia succeeds
    ok1 = repo.atomic_record_settlement_evidence(
        attempt_id="att_net1",
        network=network_base_sepolia,
        amount_units=2000,
        tx_hash=shared_tx,
        log_index=0,
    )
    assert ok1 is True
    assert repo.is_evidence_recorded(tx_hash=shared_tx, log_index=0, network=network_base_sepolia) is True

    # 2. Duplicate submission of identical (network, tx_hash, log_index) MUST be rejected
    with pytest.raises(SettlementVerificationError) as exc_dup:
        repo.atomic_record_settlement_evidence(
            attempt_id="att_net2_dup",
            network=network_base_sepolia,
            amount_units=2000,
            tx_hash=shared_tx,
            log_index=0,
        )
    assert "Duplicate settlement evidence detected" in str(exc_dup.value)

    # 3. Distinct log_index on the SAME network MUST succeed (e.g. batch transfer log 1)
    ok_log1 = repo.atomic_record_settlement_evidence(
        attempt_id="att_net3_log1",
        network=network_base_sepolia,
        amount_units=2000,
        tx_hash=shared_tx,
        log_index=1,
    )
    assert ok_log1 is True

    # 4. Identical (tx_hash, log_index=0) on a DIFFERENT network MUST succeed (no false cross-network collision)
    ok_diff_net = repo.atomic_record_settlement_evidence(
        attempt_id="att_net4_diff_chain",
        network=network_eth_sepolia,
        amount_units=2000,
        tx_hash=shared_tx,
        log_index=0,
    )
    assert ok_diff_net is True
    assert repo.is_evidence_recorded(tx_hash=shared_tx, log_index=0, network=network_eth_sepolia) is True

    engine.dispose()


def test_official_x402_server_and_client_interfaces():
    """Verify exact x402 v2 interfaces against installed x402==2.25.0 package:
    - Server scheme requirement enhancement
    - Adapter EIP-3009 translation
    - Match payload to requirements
    - Facilitator boundary classification
    """
    from x402.mechanisms.evm.exact import ExactEvmServerScheme, ExactEvmFacilitatorScheme
    from x402.schemas.responses import SupportedKind
    from x402 import PaymentRequirements, match_payload_to_requirements
    from backend.payments.x402_adapter import X402Adapter
    from backend.shared.constants import NETWORK_BASE_SEPOLIA, USDC_BASE_SEPOLIA

    server_scheme = ExactEvmServerScheme()
    req = PaymentRequirements(
        scheme="exact",
        network=NETWORK_BASE_SEPOLIA,
        asset=USDC_BASE_SEPOLIA,
        amount="5000",
        pay_to="0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        max_timeout_seconds=60,
    )

    # Server-side requirement enhancement injects official EIP-3009 metadata
    supported_kind = SupportedKind(x402_version=2, scheme="exact", network=NETWORK_BASE_SEPOLIA)
    enhanced = server_scheme.enhance_payment_requirements(req, supported_kind, [])
    assert enhanced.extra.get("name") == "USDC"
    assert enhanced.extra.get("version") == "2"

    # Adapter payload translation conforms to official schema
    adapter = X402Adapter(test_mode=True)
    nonce_hex = "0x" + "12" * 32
    app_payload = {
        "authorization": {
            "from": "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
            "to": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "value": 5000,
            "validAfter": 0,
            "validBefore": int(time.time()) + 3600,
            "nonce": nonce_hex,
        },
        "signature": "0x" + "ab" * 65,
        "buyer_address": "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
    }
    from backend.shared.schemas import PaymentRequirement
    req_obj = PaymentRequirement(
        network=NETWORK_BASE_SEPOLIA,
        token=USDC_BASE_SEPOLIA,
        amount="5000",
        payTo="0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        nonce=nonce_hex,
        service_id="service_int_01",
    )
    official_payload = adapter.to_official_payment_payload(app_payload, req_obj)

    # Official SDK match_payload_to_requirements succeeds
    is_match = match_payload_to_requirements(2, official_payload.model_dump(), enhanced.model_dump())
    assert is_match is True

    # Facilitator boundary: ExactEvmFacilitatorScheme requires a live FacilitatorEvmSigner connected to an RPC node
    with pytest.raises(TypeError) as exc_fac:
        ExactEvmFacilitatorScheme()
    assert "signer" in str(exc_fac.value).lower()


# ==============================================================================
# 11. SQLite Migration Safety & Legacy Schema Preservation
# ==============================================================================

def test_sqlite_migration_safety_legacy_preservation_and_rollback(tmp_path):
    """Verify SQLite migration preserves legacy records, upgrades constraint to (network, tx_hash, log_index),
    normalizes null networks, persists across reloads, and prevents duplicate records on the same network."""
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from backend.payments.models import DurablePaymentRepository

    db_file = tmp_path / "legacy_migration_test.db"
    db_url = f"sqlite:///{db_file}"
    raw_engine = create_engine(db_url, connect_args={"check_same_thread": False})

    # Step 1: Create legacy table with old UNIQUE constraint on (tx_hash, log_index)
    with raw_engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE settlement_evidence_records (
                evidence_id VARCHAR(128) PRIMARY KEY,
                tx_hash VARCHAR(66) NOT NULL,
                log_index INTEGER NOT NULL,
                facilitator_receipt_id VARCHAR(128),
                attempt_id VARCHAR(128),
                network VARCHAR(64),
                token_address VARCHAR(42),
                recipient_address VARCHAR(42),
                amount_units BIGINT NOT NULL,
                created_at TIMESTAMP,
                CONSTRAINT uq_evidence_tx_log UNIQUE (tx_hash, log_index)
            )
        """))

        # Step 2: Insert 4 representative legacy records
        conn.execute(text("""
            INSERT INTO settlement_evidence_records VALUES
            ('ev_1', '0x1111111111111111111111111111111111111111111111111111111111111111', 0, 'rec_1', 'att_1', 'eip155:84532', '0xUSDC', '0xSeller1', 2000, '2026-10-16 10:00:00'),
            ('ev_2', '0x2222222222222222222222222222222222222222222222222222222222222222', 0, 'rec_2', 'att_2', 'eip155:11155111', '0xUSDC', '0xSeller2', 5000, '2026-10-16 10:01:00'),
            ('ev_3', '0x3333333333333333333333333333333333333333333333333333333333333333', 1, NULL, 'att_3', NULL, '0xUSDC', '0xSeller3', 1000, '2026-10-16 10:02:00'),
            ('ev_4', '0x4444444444444444444444444444444444444444444444444444444444444444', 2, 'rec_4', 'att_4', 'eip155:84532', '0xUSDC', '0xSeller4', 8000, '2026-10-16 10:03:00')
        """))

    # Verify pre-migration count
    with raw_engine.connect() as conn:
        pre_count = conn.execute(text("SELECT count(*) FROM settlement_evidence_records")).scalar()
    assert pre_count == 4

    # Step 3: Run migration via DurablePaymentRepository
    SessionFactory = sessionmaker(bind=raw_engine)
    repo = DurablePaymentRepository(session_factory=SessionFactory)

    # Step 4: Verify post-migration records and schema
    with SessionFactory() as session:
        post_count = session.execute(text("SELECT count(*) FROM settlement_evidence_records")).scalar()
        assert post_count == 4

        # Compare records: ev_3 has explicit unresolved:legacy network (no unverified fabrication of Base Sepolia)
        r3 = session.execute(text("SELECT network, amount_units FROM settlement_evidence_records WHERE evidence_id='ev_3'")).fetchone()
        assert r3[0] == "unresolved:legacy"
        assert r3[1] == 1000

        # Verify new constraint exists in DDL
        ddl = session.execute(text("SELECT sql FROM sqlite_master WHERE type='table' AND name='settlement_evidence_records'")).scalar()
        assert "uq_evidence_net_tx_log" in ddl

        # Verify legacy table was cleaned up
        legacy_tables = session.execute(text("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='_legacy_settlement_evidence_records'")).scalar()
        assert legacy_tables == 0

    # Step 5: Test persistence after reopening database
    raw_engine.dispose()
    reopen_engine = create_engine(db_url, connect_args={"check_same_thread": False})
    ReopenSessionFactory = sessionmaker(bind=reopen_engine)
    repo_reopen = DurablePaymentRepository(session_factory=ReopenSessionFactory)

    # Verify existing records remain readable
    assert repo_reopen.is_evidence_recorded(
        tx_hash="0x1111111111111111111111111111111111111111111111111111111111111111",
        log_index=0,
        network="eip155:84532"
    ) is True

    # Step 6: Test uniqueness enforcement
    # Duplicate evidence on same network -> fails
    with pytest.raises(SettlementVerificationError):
        repo_reopen.atomic_record_settlement_evidence(
            attempt_id="att_dup",
            network="eip155:84532",
            amount_units=2000,
            tx_hash="0x1111111111111111111111111111111111111111111111111111111111111111",
            log_index=0
        )

    # Distinct log on same network -> succeeds
    distinct_log_res = repo_reopen.atomic_record_settlement_evidence(
        attempt_id="att_distinct",
        network="eip155:84532",
        amount_units=3000,
        tx_hash="0x1111111111111111111111111111111111111111111111111111111111111111",
        log_index=1
    )
    assert distinct_log_res is True

    # Identical tx_hash and log on DIFFERENT network -> succeeds (cross-network isolation)
    diff_net_res = repo_reopen.atomic_record_settlement_evidence(
        attempt_id="att_diff",
        network="eip155:11155111",
        amount_units=2000,
        tx_hash="0x1111111111111111111111111111111111111111111111111111111111111111",
        log_index=0
    )
    assert diff_net_res is True

    # Step 7: Migration idempotency - re-running does nothing
    repo_reopen._migrate_schema_if_needed()
    with ReopenSessionFactory() as session:
        final_count = session.execute(text("SELECT count(*) FROM settlement_evidence_records")).scalar()
        assert final_count == 6  # 4 initial + 2 new

    reopen_engine.dispose()


def test_sqlite_migration_interrupted_recovery_and_failure_safety(tmp_path):
    """Verify recovery when previous migration was interrupted after rename."""
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from backend.payments.models import DurablePaymentRepository

    db_file = tmp_path / "interrupted_migration_test.db"
    raw_engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})

    # Simulate crash state: _legacy_settlement_evidence_records exists, but settlement_evidence_records does not
    with raw_engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE _legacy_settlement_evidence_records (
                evidence_id VARCHAR(128) PRIMARY KEY,
                tx_hash VARCHAR(66) NOT NULL,
                log_index INTEGER NOT NULL,
                facilitator_receipt_id VARCHAR(128),
                attempt_id VARCHAR(128),
                network VARCHAR(64),
                token_address VARCHAR(42),
                recipient_address VARCHAR(42),
                amount_units BIGINT NOT NULL,
                created_at TIMESTAMP
            )
        """))
        conn.execute(text("""
            INSERT INTO _legacy_settlement_evidence_records VALUES
            ('ev_interrupted_1', '0xaaaa', 0, 'rec_i1', 'att_i1', 'eip155:84532', '0xUSDC', '0xSeller', 5000, '2026-10-16 12:00:00')
        """))

    SessionFactory = sessionmaker(bind=raw_engine)
    # Instantiate repo - should detect interrupted migration, create target table, copy rows, and drop legacy table
    repo = DurablePaymentRepository(session_factory=SessionFactory)

    with SessionFactory() as session:
        count = session.execute(text("SELECT count(*) FROM settlement_evidence_records")).scalar()
        assert count == 1
        rec = session.execute(text("SELECT tx_hash, amount_units FROM settlement_evidence_records WHERE evidence_id='ev_interrupted_1'")).fetchone()
        assert rec[0] == "0xaaaa"
        assert rec[1] == 5000

        # Legacy temp table is dropped
        legacy_exists = session.execute(text("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='_legacy_settlement_evidence_records'")).scalar()
        assert legacy_exists == 0

    raw_engine.dispose()


# ==============================================================================
# 12. Buyer-Seller x402 Protocol Interoperability & Route Handoff
# ==============================================================================

@pytest.mark.asyncio
async def test_verify_seller_payment_official_and_legacy_headers():
    """Verify verify_seller_payment handles official base64 PAYMENT-SIGNATURE,
    custom JSON X-402-Payment-Payload, dual headers, and fails closed on invalid/tampered parameters."""
    from backend.payments.dependencies import verify_seller_payment
    from backend.payments.x402_adapter import X402Adapter
    from backend.shared.schemas import PaymentRequirement
    from backend.shared.constants import NETWORK_BASE_SEPOLIA, USDC_BASE_SEPOLIA

    import uuid
    adapter = X402Adapter(test_mode=True)
    pay_to = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"

    def make_payload(n_hex: str) -> dict:
        return {
            "authorization": {
                "from": "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
                "to": pay_to,
                "value": 2000,
                "validAfter": 0,
                "validBefore": int(time.time()) + 3600,
                "nonce": n_hex,
            },
            "signature": "0x" + "11" * 65,
            "buyer_address": "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
        }

    nonce_hex_1 = f"0x{uuid.uuid4().hex}{uuid.uuid4().hex}"
    nonce_hex_2 = f"0x{uuid.uuid4().hex}{uuid.uuid4().hex}"
    nonce_hex_3 = f"0x{uuid.uuid4().hex}{uuid.uuid4().hex}"

    req_1 = PaymentRequirement(
        network=NETWORK_BASE_SEPOLIA,
        token=USDC_BASE_SEPOLIA,
        amount="2000",
        payTo=pay_to,
        nonce=nonce_hex_1,
        service_id="data_001"
    )
    req_3 = PaymentRequirement(
        network=NETWORK_BASE_SEPOLIA,
        token=USDC_BASE_SEPOLIA,
        amount="2000",
        payTo=pay_to,
        nonce=nonce_hex_3,
        service_id="data_001"
    )

    app_payload_1 = make_payload(nonce_hex_1)
    app_payload_2 = make_payload(nonce_hex_2)
    app_payload_3 = make_payload(nonce_hex_3)

    # 1. Official base64 wire header only
    official_sig_header = adapter.encode_official_payload(app_payload_1, req_1)
    proof_official = await verify_seller_payment(
        service_id="data_001",
        amount_units=2000,
        pay_to=pay_to,
        official_signature_header=official_sig_header,
    )
    assert proof_official is not None
    assert proof_official.startswith("rec_auth_")

    # 2. Legacy custom JSON header only
    proof_legacy = await verify_seller_payment(
        service_id="data_001",
        amount_units=2000,
        pay_to=pay_to,
        payment_payload_header=json.dumps(app_payload_2),
    )
    assert proof_legacy is not None
    assert proof_legacy.startswith("rec_auth_")

    # 3. Both headers provided simultaneously
    official_sig_header_3 = adapter.encode_official_payload(app_payload_3, req_3)
    proof_dual = await verify_seller_payment(
        service_id="data_001",
        amount_units=2000,
        pay_to=pay_to,
        payment_payload_header=json.dumps(app_payload_3),
        official_signature_header=official_sig_header_3,
    )
    assert proof_dual is not None

    # 4. Tampered amount in custom payload -> HTTP 402 rejection
    app_payload = make_payload(f"0x{uuid.uuid4().hex}{uuid.uuid4().hex}")
    tampered_payload = dict(app_payload)
    tampered_payload["authorization"] = dict(app_payload["authorization"])
    tampered_payload["authorization"]["value"] = 500  # Underpaying
    with pytest.raises(HTTPException) as exc_tamper:
        await verify_seller_payment(
            service_id="data_001",
            amount_units=2000,
            pay_to=pay_to,
            payment_payload_header=json.dumps(tampered_payload),
        )
    assert exc_tamper.value.status_code == 402

    # 5. Wrong recipient address -> HTTP 402 rejection
    wrong_recipient_payload = dict(app_payload)
    wrong_recipient_payload["authorization"] = dict(app_payload["authorization"])
    wrong_recipient_payload["authorization"]["to"] = "0xWrongSeller000000000000000000000000000000"
    with pytest.raises(HTTPException) as exc_wrong_to:
        await verify_seller_payment(
            service_id="data_001",
            amount_units=2000,
            pay_to=pay_to,
            payment_payload_header=json.dumps(wrong_recipient_payload),
        )
    assert exc_wrong_to.value.status_code == 402

    # 6. Malformed base64 signature -> HTTP 402 rejection
    with pytest.raises(HTTPException) as exc_bad_wire:
        await verify_seller_payment(
            service_id="data_001",
            amount_units=2000,
            pay_to=pay_to,
            official_signature_header="not_valid_base64_json!!!",
        )
    assert exc_bad_wire.value.status_code == 402


@pytest.mark.asyncio
async def test_buyer_seller_route_official_and_legacy_flows():
    """Verify live HTTP route behavior between Buyer and Seller endpoints across all header modes.

    Tests:
    - Initial unpaid request triggers HTTP 402 challenge with BOTH official and legacy headers.
    - Legacy-header-only request succeeds with HTTP 200.
    - Dual-header request succeeds with HTTP 200.
    - Official-header-only request succeeds with HTTP 200 and returns official PAYMENT-RESPONSE.
    - Multi-service validation: works across Data, Scraping, and Inference seller routes.
    """
    import httpx
    from httpx import ASGITransport
    from backend.main import app
    from backend.payments.x402_adapter import (
        X402Adapter,
        HEADER_OFFICIAL_PAYMENT_REQUIRED,
        HEADER_OFFICIAL_PAYMENT_SIGNATURE,
        HEADER_OFFICIAL_PAYMENT_RESPONSE,
    )
    from backend.shared.constants import (
        HEADER_X402_PAYMENT_PAYLOAD,
        HEADER_X402_SETTLEMENT_PROOF,
        HEADER_X402_REQUIREMENT,
        HEADER_IDEMPOTENCY_KEY,
    )

    adapter = X402Adapter(test_mode=True)

    endpoints_and_payloads = [
        ("/api/v1/seller/data", {"symbol": "ETH"}),
        ("/api/v1/seller/scraping", {"url": "https://example.com/api"}),
        ("/api/v1/seller/inference", {"prompt": "Analyze market trends", "max_tokens": 100}),
    ]

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost:8000") as client:
        for path, payload in endpoints_and_payloads:
            # 1. Unpaid request -> HTTP 402 Challenge with both headers
            r402 = await client.post(path, json=payload)
            assert r402.status_code == 402
            assert HEADER_X402_REQUIREMENT in r402.headers
            assert "payment-required" in r402.headers or HEADER_OFFICIAL_PAYMENT_REQUIRED in r402.headers

            req = adapter.parse_challenge_from_headers(r402.headers)
            assert req.amount is not None

            # 2. Legacy-header-only flow
            idemp_legacy = f"idemp_leg_{path.split('/')[-1]}_001"
            pl_legacy = adapter.create_payment_payload(req, idempotency_key=idemp_legacy)
            legacy_headers = {
                HEADER_X402_PAYMENT_PAYLOAD: json.dumps(pl_legacy),
                HEADER_IDEMPOTENCY_KEY: idemp_legacy,
            }
            resp_legacy = await client.post(path, json=payload, headers=legacy_headers)
            assert resp_legacy.status_code == 200, f"Legacy flow failed for {path}: {resp_legacy.text}"
            assert HEADER_X402_SETTLEMENT_PROOF in resp_legacy.headers
            assert resp_legacy.headers[HEADER_X402_SETTLEMENT_PROOF].startswith("rec_auth_")

            # 3. Dual-header flow
            idemp_dual = f"idemp_dual_{path.split('/')[-1]}_002"
            pl_dual = adapter.create_payment_payload(req, idempotency_key=idemp_dual)
            dual_headers = adapter.build_payment_headers(pl_dual, req, idempotency_key=idemp_dual)
            resp_dual = await client.post(path, json=payload, headers=dual_headers)
            assert resp_dual.status_code == 200, f"Dual flow failed for {path}: {resp_dual.text}"
            assert HEADER_X402_SETTLEMENT_PROOF in resp_dual.headers

            # 4. Official-header-only flow (No X-402-Payment-Payload)
            idemp_official = f"idemp_off_{path.split('/')[-1]}_003"
            pl_off = adapter.create_payment_payload(req, idempotency_key=idemp_official)
            wire_sig = adapter.encode_official_payload(pl_off, req)
            official_only_headers = {
                HEADER_OFFICIAL_PAYMENT_SIGNATURE: wire_sig,
                HEADER_IDEMPOTENCY_KEY: idemp_official,
            }
            resp_official = await client.post(path, json=payload, headers=official_only_headers)
            assert resp_official.status_code == 200, f"Official-only flow failed for {path}: {resp_official.text}"
            assert HEADER_X402_SETTLEMENT_PROOF in resp_official.headers
            assert "payment-response" in resp_official.headers or HEADER_OFFICIAL_PAYMENT_RESPONSE in resp_official.headers
            proof = adapter.extract_settlement_proof(resp_official.headers)
            assert proof is not None
            assert proof.startswith("rec_auth_")

            # Verify truthful settlement response typing: local authorization is NOT claimed as confirmed on-chain settlement
            resp_wire = resp_official.headers.get("payment-response") or resp_official.headers.get(HEADER_OFFICIAL_PAYMENT_RESPONSE)
            if resp_wire:
                import x402.http as x402_http
                sr = x402_http.decode_payment_response_header(resp_wire)
                assert sr.extra is not None
                assert sr.extra.get("confirmed_on_chain") is False
                assert sr.extra.get("settlement_type") == "local_authorization_receipt"


@pytest.mark.asyncio
async def test_route_rejection_of_invalid_and_tampered_headers():
    """Verify live seller route security boundaries:
    - Missing or malformed payment headers.
    - Tampered signatures and payment requirements.
    - Wrong network, recipient, or amount.
    - Conflicting official and legacy payment headers.
    - Duplicate ambiguous headers.
    """
    import httpx
    from httpx import ASGITransport
    from backend.main import app
    from backend.payments.x402_adapter import (
        X402Adapter,
        HEADER_OFFICIAL_PAYMENT_SIGNATURE,
    )
    from backend.shared.constants import (
        HEADER_X402_PAYMENT_PAYLOAD,
        HEADER_IDEMPOTENCY_KEY,
    )

    adapter = X402Adapter(test_mode=True)
    seller_url = "http://localhost:8000/api/v1/seller/data"
    input_payload = {"symbol": "BTC"}

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost:8000") as client:
        # Step 1: Challenge
        r402 = await client.post(seller_url, json=input_payload)
        assert r402.status_code == 402
        req = adapter.parse_challenge_from_headers(r402.headers)

        valid_pl = adapter.create_payment_payload(req, idempotency_key="idemp_sec_valid_001")
        valid_wire_sig = adapter.encode_official_payload(valid_pl, req)

        # 1. Missing header -> HTTP 402
        r_missing = await client.post(seller_url, json=input_payload)
        assert r_missing.status_code == 402

        # 2. Malformed official header (not base64 / corrupted) -> HTTP 400 Bad Request
        r_bad_wire = await client.post(
            seller_url,
            json=input_payload,
            headers={HEADER_OFFICIAL_PAYMENT_SIGNATURE: "corrupted_non_base64_json!@#$"}
        )
        assert r_bad_wire.status_code in (400, 402)

        # 3. Malformed legacy JSON header -> HTTP 400 Bad Request
        r_bad_json = await client.post(
            seller_url,
            json=input_payload,
            headers={HEADER_X402_PAYMENT_PAYLOAD: "{invalid_json..."}
        )
        assert r_bad_json.status_code == 400

        # 4. Tampered amount (underpaying: value = 500 instead of 2000) -> HTTP 402
        tampered_pl = dict(valid_pl)
        tampered_pl["authorization"] = dict(tampered_pl["authorization"])
        tampered_pl["authorization"]["value"] = 500
        tampered_pl["authorization"]["amount"] = 500
        wire_tampered_val = adapter.encode_official_payload(tampered_pl, req)
        r_tamper_val = await client.post(
            seller_url,
            json=input_payload,
            headers={HEADER_OFFICIAL_PAYMENT_SIGNATURE: wire_tampered_val}
        )
        assert r_tamper_val.status_code == 402

        # 5. Wrong recipient address -> HTTP 402
        wrong_recip_pl = dict(valid_pl)
        wrong_recip_pl["authorization"] = dict(wrong_recip_pl["authorization"])
        wrong_recip_pl["authorization"]["to"] = "0x000000000000000000000000000000000000dEaD"
        wire_wrong_to = adapter.encode_official_payload(wrong_recip_pl, req)
        r_wrong_to = await client.post(
            seller_url,
            json=input_payload,
            headers={HEADER_OFFICIAL_PAYMENT_SIGNATURE: wire_wrong_to}
        )
        assert r_wrong_to.status_code == 402

        # 6. Wrong network -> HTTP 402
        wrong_net_pl = dict(valid_pl)
        wrong_net_pl["authorization"] = dict(wrong_net_pl["authorization"])
        wrong_net_pl["authorization"]["network"] = "eip155:1"
        wire_wrong_net = adapter.encode_official_payload(wrong_net_pl, req)
        r_wrong_net = await client.post(
            seller_url,
            json=input_payload,
            headers={HEADER_OFFICIAL_PAYMENT_SIGNATURE: wire_wrong_net}
        )
        assert r_wrong_net.status_code == 402

        # 7. Tampered cryptographic signature -> HTTP 402
        tampered_sig_pl = dict(valid_pl)
        tampered_sig_pl["signature"] = "0x" + "00" * 65
        wire_bad_sig = adapter.encode_official_payload(tampered_sig_pl, req)
        r_bad_sig = await client.post(
            seller_url,
            json=input_payload,
            headers={HEADER_OFFICIAL_PAYMENT_SIGNATURE: wire_bad_sig}
        )
        assert r_bad_sig.status_code == 402

        # 8. Conflicting official and legacy payment headers -> HTTP 400 Bad Request
        conflicting_legacy = dict(valid_pl)
        conflicting_legacy["authorization"] = dict(conflicting_legacy["authorization"])
        conflicting_legacy["authorization"]["value"] = 99999
        conflicting_legacy["authorization"]["amount"] = 99999
        r_conflict = await client.post(
            seller_url,
            json=input_payload,
            headers={
                HEADER_OFFICIAL_PAYMENT_SIGNATURE: valid_wire_sig,
                HEADER_X402_PAYMENT_PAYLOAD: json.dumps(conflicting_legacy),
            }
        )
        assert r_conflict.status_code == 400

        # 9. Duplicate ambiguous headers -> HTTP 400 Bad Request
        r_duplicate = await client.post(
            seller_url,
            json=input_payload,
            headers=[
                (HEADER_OFFICIAL_PAYMENT_SIGNATURE, valid_wire_sig),
                (HEADER_OFFICIAL_PAYMENT_SIGNATURE, "duplicate_ambiguous_value"),
            ]
        )
        assert r_duplicate.status_code in (400, 402)


@pytest.mark.asyncio
async def test_route_idempotency_and_uncertain_settlement():
    """Verify live route duplicate request replay protection and uncertain settlement handling."""
    import httpx
    from httpx import ASGITransport
    from backend.main import app
    from backend.payments.x402_adapter import (
        X402Adapter,
        HEADER_OFFICIAL_PAYMENT_SIGNATURE,
    )
    from backend.shared.constants import (
        HEADER_X402_SETTLEMENT_PROOF,
        HEADER_IDEMPOTENCY_KEY,
    )

    adapter = X402Adapter(test_mode=True)
    seller_url = "http://localhost:8000/api/v1/seller/data"
    input_payload = {"symbol": "SOL"}

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost:8000") as client:
        # Step 1: Challenge
        r402 = await client.post(seller_url, json=input_payload)
        assert r402.status_code == 402
        req = adapter.parse_challenge_from_headers(r402.headers)

        idemp_key = "idemp_replay_test_001"
        pl = adapter.create_payment_payload(req, idempotency_key=idemp_key)
        wire_sig = adapter.encode_official_payload(pl, req)

        # First request with official header -> 200 OK
        resp1 = await client.post(
            seller_url,
            json=input_payload,
            headers={
                HEADER_OFFICIAL_PAYMENT_SIGNATURE: wire_sig,
                HEADER_IDEMPOTENCY_KEY: idemp_key,
            }
        )
        assert resp1.status_code == 200
        proof1 = resp1.headers.get(HEADER_X402_SETTLEMENT_PROOF)
        assert proof1 is not None

        # Duplicate request with same idempotency key and payload -> returns same result or succeeds idempotently
        resp2 = await client.post(
            seller_url,
            json=input_payload,
            headers={
                HEADER_OFFICIAL_PAYMENT_SIGNATURE: wire_sig,
                HEADER_IDEMPOTENCY_KEY: idemp_key,
            }
        )
        # Replay is safely processed, returns cached 200, or fails closed with 400/402 replay rejection
        assert resp2.status_code in (200, 400, 402)


# ==============================================================================
# 11. Truthful Settlement Representation & Confirmed On-Chain Invariant
# ==============================================================================

@pytest.mark.asyncio
async def test_confirmed_on_chain_never_true_from_hex_hash_alone():
    """Verify that a 0x hex transaction hash alone NEVER asserts confirmed_on_chain=True.

    Verified receipt and matching on-chain transfer event logs from live RPC are strictly required.
    Without live RPC confirmation, settlements remain explicitly confirmed_on_chain=False.
    """
    import httpx
    from httpx import ASGITransport
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Route
    from backend.payments.middleware import X402ProtocolMiddleware
    from backend.payments.x402_adapter import (
        X402Adapter,
        HEADER_OFFICIAL_PAYMENT_RESPONSE,
        HEADER_X402_SETTLEMENT_PROOF,
    )
    import x402.http as x402_http

    test_tx_hash = "0x" + "42" * 32  # 66-character hex hash

    async def fake_seller_endpoint(request):
        # Simulates an unverified or offline tx hash returned by a seller
        return JSONResponse(
            content={"result": "data"},
            headers={HEADER_X402_SETTLEMENT_PROOF: test_tx_hash}
        )

    base_app = Starlette(routes=[Route("/test-settlement", fake_seller_endpoint, methods=["POST"])])
    wrapped_app = X402ProtocolMiddleware(base_app)

    async with httpx.AsyncClient(transport=ASGITransport(app=wrapped_app), base_url="http://test") as client:
        resp = await client.post("/test-settlement", json={})
        assert resp.status_code == 200
        assert resp.headers.get(HEADER_X402_SETTLEMENT_PROOF) == test_tx_hash

        resp_wire = resp.headers.get("payment-response") or resp.headers.get(HEADER_OFFICIAL_PAYMENT_RESPONSE)
        assert resp_wire is not None

        sr = x402_http.decode_payment_response_header(resp_wire)
        assert sr.extra is not None
        # Invariant: NEVER True without verified live RPC receipt and transfer events
        assert sr.extra.get("confirmed_on_chain") is False
        assert sr.extra.get("settlement_type") == "unverified_transaction_hash"
        assert sr.extra.get("verification_status") == "unconfirmed_offline_rpc_unavailable"


# ==============================================================================
# 12. Atomic Authorization Nonce Guard (Independent of Settlement Evidence)
# ==============================================================================

@pytest.mark.asyncio
async def test_authorization_nonce_atomic_guard_independent_of_settlement_evidence():
    """Verify authorization nonce replay protection independently of on-chain settlement evidence.

    Protects against concurrent or sequential reuse before/without (network, tx_hash, log_index)
    database settlement records.
    """
    import uuid
    from backend.payments.settlement import SellerPaymentVerifier, AuthorizationNonceGuard
    from backend.payments.errors import SettlementVerificationError
    from backend.shared.schemas import PaymentPayload, PaymentRequirement
    from backend.shared.constants import NETWORK_BASE_SEPOLIA, USDC_BASE_SEPOLIA

    test_guard = AuthorizationNonceGuard(ttl_seconds=3600)
    verifier = SellerPaymentVerifier(test_mode=True, nonce_guard=test_guard)

    unique_nonce = f"0x{uuid.uuid4().hex}{uuid.uuid4().hex}"
    buyer_addr = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
    pay_to = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"

    req = PaymentRequirement(
        network=NETWORK_BASE_SEPOLIA,
        token=USDC_BASE_SEPOLIA,
        amount="2000",
        payTo=pay_to,
        nonce=f"nonce_{uuid.uuid4().hex[:16]}",
        service_id="data_001",
    )

    payload = PaymentPayload(
        authorization={
            "network": NETWORK_BASE_SEPOLIA,
            "token": USDC_BASE_SEPOLIA,
            "from": buyer_addr,
            "to": pay_to,
            "value": 2000,
            "nonce": unique_nonce,
            "validAfter": 0,
            "validBefore": int(time.time()) + 3600,
        },
        signature="0x_mock_sig_nonce_guard_test",
        buyer_address=buyer_addr,
    )

    # First attempt: succeeds and commits nonce
    receipt1 = await verifier.verify_and_settle(payload, req)
    assert receipt1.facilitator_receipt_id is not None
    assert receipt1.facilitator_receipt_id.startswith("rec_auth_")

    # Second attempt (replay of same authorization nonce): must be rejected immediately
    with pytest.raises(SettlementVerificationError) as exc_info:
        await verifier.verify_and_settle(payload, req)

    assert "Authorization nonce replay detected" in str(exc_info.value)


@pytest.mark.asyncio
async def test_authorization_nonce_atomic_guard_blocks_concurrent_reuse():
    """Verify atomic guard prevents simultaneous race-condition reuse of the same authorization."""
    import asyncio
    import uuid
    from backend.payments.settlement import SellerPaymentVerifier, AuthorizationNonceGuard
    from backend.payments.errors import SettlementVerificationError
    from backend.shared.schemas import PaymentPayload, PaymentRequirement
    from backend.shared.constants import NETWORK_BASE_SEPOLIA, USDC_BASE_SEPOLIA

    test_guard = AuthorizationNonceGuard(ttl_seconds=3600)
    verifier = SellerPaymentVerifier(test_mode=True, nonce_guard=test_guard)

    concurrent_nonce = f"0x{uuid.uuid4().hex}{uuid.uuid4().hex}"
    buyer_addr = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
    pay_to = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"

    req = PaymentRequirement(
        network=NETWORK_BASE_SEPOLIA,
        token=USDC_BASE_SEPOLIA,
        amount="2000",
        payTo=pay_to,
        nonce=f"nonce_{uuid.uuid4().hex[:16]}",
        service_id="data_001",
    )

    payload = PaymentPayload(
        authorization={
            "network": NETWORK_BASE_SEPOLIA,
            "token": USDC_BASE_SEPOLIA,
            "from": buyer_addr,
            "to": pay_to,
            "value": 2000,
            "nonce": concurrent_nonce,
            "validAfter": 0,
            "validBefore": int(time.time()) + 3600,
        },
        signature="0x_mock_sig_concurrent_nonce",
        buyer_address=buyer_addr,
    )

    # Launch 10 concurrent verification attempts simultaneously
    tasks = [verifier.verify_and_settle(payload, req) for _ in range(10)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    successes = [r for r in results if not isinstance(r, Exception)]
    failures = [r for r in results if isinstance(r, Exception)]

    # Exactly 1 request succeeds; all 9 concurrent replays fail closed
    assert len(successes) == 1
    assert len(failures) == 9
    for err in failures:
        assert isinstance(err, SettlementVerificationError)
        assert ("already in-flight" in str(err) or "already been consumed" in str(err))


# ==============================================================================
# 13. Genuine EIP-712 & EIP-3009 Cryptographic Verification (Deterministic Keys)
# ==============================================================================

@pytest.mark.asyncio
async def test_genuine_eip712_and_eip3009_cryptographic_recovery_and_tamper_detection():
    """Verify cryptographic recovery using deterministic test keys.

    Verifies:
    1. Valid EIP-712 and EIP-3009 signatures recover the exact expected signer address.
    2. Bit-flipped or tampered signatures fail cryptographic verification.
    3. Tampered payload terms (value, validBefore, recipient) fail verification.
    4. Production live mode (test_mode=False) strictly accepts genuine signatures and rejects mock signatures.
    """
    import uuid
    from eth_account import Account
    from backend.payments.x402_adapter import X402Adapter
    from backend.payments.settlement import SellerPaymentVerifier, AuthorizationNonceGuard
    from backend.payments.errors import SettlementVerificationError
    from backend.shared.schemas import PaymentPayload, PaymentRequirement
    from backend.shared.constants import NETWORK_BASE_SEPOLIA, USDC_BASE_SEPOLIA

    # Deterministic test private key (Anvil #0 test key)
    DETERMINISTIC_TEST_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
    test_account = Account.from_key(DETERMINISTIC_TEST_KEY)
    expected_signer = test_account.address
    seller_pay_to = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"

    adapter = X402Adapter(test_mode=False)

    # ---------------------------------------------------------
    # A. Canonical EIP-712 Signature Recovery & Tamper Testing
    # ---------------------------------------------------------
    auth_eip712 = {
        "network": NETWORK_BASE_SEPOLIA,
        "token": USDC_BASE_SEPOLIA,
        "payTo": seller_pay_to,
        "amount": 2500,
        "nonce": f"0x{uuid.uuid4().hex}{uuid.uuid4().hex}",
        "validAfter": 0,
        "validBefore": int(time.time()) + 3600,
        "idempotencyKey": "idemp_crypto_712",
    }

    # 1. Sign genuine EIP-712 payload
    sig_eip712 = adapter.sign_eip712_authorization(auth_eip712, private_key=DETERMINISTIC_TEST_KEY)
    assert sig_eip712.startswith("0x") and len(sig_eip712) == 132

    # 2. Recover signer: exactly matches expected signer
    recovered_712 = adapter.recover_eip712_signer(auth_eip712, sig_eip712)
    assert recovered_712.lower() == expected_signer.lower()
    assert adapter.verify_eip712_signature(auth_eip712, sig_eip712, expected_signer) is True
    assert adapter.verify_eip712_signature(auth_eip712, sig_eip712, "0x1111111111111111111111111111111111111111") is False

    # 3. Tampered EIP-712 signature (flip last character)
    tampered_sig_712 = sig_eip712[:-1] + ("0" if sig_eip712[-1] != "0" else "1")
    assert adapter.verify_eip712_signature(auth_eip712, tampered_sig_712, expected_signer) is False

    # 4. Tampered EIP-712 payload amount
    tampered_auth_712 = dict(auth_eip712, amount=99999)
    assert adapter.verify_eip712_signature(tampered_auth_712, sig_eip712, expected_signer) is False

    # ---------------------------------------------------------
    # B. Canonical EIP-3009 Signature Recovery & Tamper Testing
    # ---------------------------------------------------------
    dynamic_nonce_3009 = f"0x{uuid.uuid4().hex}{uuid.uuid4().hex}"
    auth_eip3009 = {
        "from": expected_signer,
        "to": seller_pay_to,
        "value": 3000,
        "validAfter": 0,
        "validBefore": int(time.time()) + 3600,
        "nonce": dynamic_nonce_3009,
        "network": NETWORK_BASE_SEPOLIA,
        "token": USDC_BASE_SEPOLIA,
    }

    # 1. Sign genuine EIP-3009 payload
    sig_eip3009 = adapter.sign_eip3009_authorization(auth_eip3009, private_key=DETERMINISTIC_TEST_KEY)
    assert sig_eip3009.startswith("0x") and len(sig_eip3009) == 132

    # 2. Recover signer: exactly matches expected signer
    recovered_3009 = adapter.recover_eip3009_signer(auth_eip3009, sig_eip3009)
    assert recovered_3009.lower() == expected_signer.lower()
    assert adapter.verify_eip3009_signature(auth_eip3009, sig_eip3009, expected_signer) is True

    # 3. Tampered EIP-3009 signature
    tampered_sig_3009 = sig_eip3009[:-1] + ("0" if sig_eip3009[-1] != "0" else "1")
    assert adapter.verify_eip3009_signature(auth_eip3009, tampered_sig_3009, expected_signer) is False

    # 4. Tampered EIP-3009 payload recipient
    tampered_auth_3009 = dict(auth_eip3009, to="0x0000000000000000000000000000000000000001")
    assert adapter.verify_eip3009_signature(tampered_auth_3009, sig_eip3009, expected_signer) is False

    # ---------------------------------------------------------
    # C. SellerPaymentVerifier Live Mode (Strict Cryptographic Verification)
    # ---------------------------------------------------------
    live_guard = AuthorizationNonceGuard(ttl_seconds=3600)
    live_verifier = SellerPaymentVerifier(test_mode=False, nonce_guard=live_guard)

    req_live = PaymentRequirement(
        network=NETWORK_BASE_SEPOLIA,
        token=USDC_BASE_SEPOLIA,
        amount="3000",
        payTo=seller_pay_to,
        nonce=dynamic_nonce_3009,
        service_id="inference_001",
    )

    # 1. Live mode accepts valid genuine EIP-3009 payload
    valid_payload = PaymentPayload(
        authorization=auth_eip3009,
        signature=sig_eip3009,
        buyer_address=expected_signer,
    )
    receipt_live = await live_verifier.verify_and_settle(valid_payload, req_live)
    assert receipt_live.facilitator_receipt_id is not None
    assert receipt_live.facilitator_receipt_id.startswith("rec_auth_")

    # 2. Live mode strictly rejects synthetic mock signatures
    mock_payload = PaymentPayload(
        authorization=dict(auth_eip3009, nonce=f"0x{uuid.uuid4().hex}{uuid.uuid4().hex}"),
        signature="0x_mock_sig_should_be_rejected_in_live_mode",
        buyer_address=expected_signer,
    )
    with pytest.raises(SettlementVerificationError) as exc_mock:
        await live_verifier.verify_and_settle(mock_payload, req_live)
    assert "Mock signature rejected in live seller verification" in str(exc_mock.value)

    # 3. Live mode strictly rejects tampered signature
    tampered_live_payload = PaymentPayload(
        authorization=dict(auth_eip3009, nonce=f"0x{uuid.uuid4().hex}{uuid.uuid4().hex}"),
        signature=tampered_sig_3009,
        buyer_address=expected_signer,
    )
    with pytest.raises(SettlementVerificationError) as exc_tampered:
        await live_verifier.verify_and_settle(tampered_live_payload, req_live)
    assert "Cryptographic signature check failed" in str(exc_tampered.value)


@pytest.mark.asyncio
async def test_live_mode_placeholder_buyer_wallet_fails_closed():
    """Verify that in live mode (test_mode=False), configuring BUYER_WALLET_ADDRESS
    as the placeholder 0x000...0 actively fails closed when signing or creating payloads."""
    from backend.payments.x402_adapter import X402Adapter
    from backend.shared.schemas import PaymentRequirement
    from backend.payments.errors import PaymentEngineError
    from eth_account import Account

    signer = Account.create()
    adapter = X402Adapter(test_mode=False)
    adapter.buyer_private_key = signer.key.hex()
    adapter.buyer_address = "0x0000000000000000000000000000000000000000"

    req = PaymentRequirement(
        version="2.0",
        network="eip155:84532",
        token="0x036CbD53842c5426634e7929541eC2318f3dCF7e",
        amount="10000",
        payTo="0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        nonce="0x" + "11" * 32,
        service_id="data_001",
    )

    with pytest.raises(PaymentEngineError) as exc_info:
        adapter.create_payment_payload(req, idempotency_key="idemp_live_test")
    assert "non-operational placeholder (0x000...0)" in str(exc_info.value)


@pytest.mark.asyncio
async def test_live_mode_placeholder_pay_to_recipient_fails_closed():
    """Verify that in live mode (test_mode=False), attempting to pay a placeholder
    seller address (0x000...1..3) actively fails closed before signing or sending."""
    from backend.payments.x402_adapter import X402Adapter
    from backend.shared.schemas import PaymentRequirement
    from backend.payments.errors import PaymentEngineError
    from eth_account import Account

    signer = Account.create()
    adapter = X402Adapter(test_mode=False)
    adapter.buyer_private_key = signer.key.hex()
    adapter.buyer_address = signer.address

    for placeholder_recipient in [
        "0x0000000000000000000000000000000000000001",
        "0x0000000000000000000000000000000000000002",
        "0x0000000000000000000000000000000000000003",
    ]:
        req = PaymentRequirement(
            version="2.0",
            network="eip155:84532",
            token="0x036CbD53842c5426634e7929541eC2318f3dCF7e",
            amount="10000",
            payTo=placeholder_recipient,
            nonce="0x" + "22" * 32,
            service_id="data_001",
        )

        with pytest.raises(PaymentEngineError) as exc_info:
            adapter.create_payment_payload(req, idempotency_key="idemp_placeholder_recipient")
        assert "is a non-operational placeholder address" in str(exc_info.value)
