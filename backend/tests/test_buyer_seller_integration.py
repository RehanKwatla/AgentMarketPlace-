"""[TEST SUITE] Member 1 Stage D — End-to-End Buyer/Seller Integration Tests.

NOTE: All tests in this module use deterministic fixtures, in-process ASGI transports,
and simulated cryptographic evidence. MOCK-BASED TESTS: THEY DO NOT PROVE REAL BLOCKCHAIN SETTLEMENT.
No live transactions are broadcast to Base Sepolia during these tests.
"""
import asyncio
from datetime import datetime, timezone
import json
from typing import Any, Dict, Optional
import uuid
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.shared.constants import (
    NETWORK_BASE_SEPOLIA,
    USDC_BASE_SEPOLIA,
    LedgerStatus,
    base_units_to_usdc,
    usdc_to_base_units,
)
from backend.shared.schemas import (
    PaymentRequirement,
    PaymentPayload,
    SettlementReceipt,
    ServiceDefinition,
    ServiceCategory,
    TaskRequest,
)
from backend.registry.service_catalog import catalog
from backend.buyer.buyer_agent import BuyerAgent
from backend.payments.budget import BudgetManager
from backend.payments.idempotency import IdempotencyStore, compute_payload_hash
from backend.payments.policy import PaymentPolicyVerifier
from backend.payments.settlement import SettlementVerifier, SellerPaymentVerifier
from backend.payments.x402_adapter import X402Adapter
from backend.payments.service import PaymentService
from backend.payments.schemas import PaymentStatus, PaidCallResult, PaymentAttemptRecord
from backend.payments.models import DurablePaymentRepository, PaymentAttemptModel
from backend.payments.errors import (
    BudgetExceededError,
    IdempotencyConflictError,
    SettlementTimeoutError,
    SettlementVerificationError,
)
from backend.database.session import SessionLocal

VALID_DATA_OUTPUT = {
    "symbol": "BTC",
    "price": 68500.0,
    "volume_24h": 1500000.0,
    "timestamp": "2026-10-16T12:00:00Z",
}

VALID_ETH_OUTPUT = {
    "symbol": "ETH",
    "price": 2750.0,
    "volume_24h": 1200000.0,
    "timestamp": "2026-10-16T12:00:00Z",
}


@pytest.fixture
def integration_repo():
    """Provides a clean repository instance connected to the test database."""
    return DurablePaymentRepository(session_factory=SessionLocal)


@pytest.fixture
def isolated_payment_service(integration_repo):
    """PaymentService with dedicated stores and test mode enabled."""
    store = IdempotencyStore()
    policy = PaymentPolicyVerifier()
    settlement = SettlementVerifier(test_mode=True)
    adapter = X402Adapter(policy_verifier=policy, test_mode=True)
    svc = PaymentService(
        policy_verifier=policy,
        settlement_verifier=settlement,
        adapter=adapter,
        store=store,
        durable_repo=integration_repo,
    )
    return svc


@pytest.fixture
def test_buyer_agent(isolated_payment_service):
    """BuyerAgent wired with the isolated PaymentService."""
    return BuyerAgent(payment_service=isolated_payment_service)


# ---------------------------------------------------------------------------
# Test 1: Buyer request to seller execution through the payment service
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_1_buyer_request_to_seller_execution_through_payment_service(test_buyer_agent, isolated_payment_service):
    """[MOCK-BASED] Verify BuyerAgent end-to-end task execution calls seller via PaymentService."""
    task_req = TaskRequest(
        task="Collect crypto market data and summarize",
        budget_usdc="0.05",
    )

    response = await test_buyer_agent.execute_task(task_req)

    assert response.status == "completed"
    assert len(response.executions) >= 1
    first_step = response.executions[0]
    assert first_step.status == LedgerStatus.PAID
    assert float(first_step.price_paid_usdc) == 0.002
    assert first_step.output is not None
    assert first_step.request_id.startswith("req_") or first_step.request_id.startswith("call_")


# ---------------------------------------------------------------------------
# Test 2: Successful verifier result with structured settlement evidence
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_2_successful_verifier_result_with_structured_settlement_evidence(isolated_payment_service, integration_repo):
    """[MOCK-BASED] Verify structured settlement evidence produces PAID state and persists to database."""
    service = catalog.get_service("data_001")
    task_id = f"task_structured_{uuid.uuid4().hex[:8]}"
    call_id = "step_1"
    idemp_key = f"idemp_{task_id}_{call_id}"
    budget_mgr = isolated_payment_service.get_or_create_task_budget(task_id, 100_000)

    # Mock adapter to return structured receipt and compliant catalog output
    with patch.object(
        isolated_payment_service.adapter,
        "execute_paid_request",
        new=AsyncMock(return_value=(200, VALID_DATA_OUTPUT, "receipt_structured_valid_001"))
    ):
        result = await isolated_payment_service.execute_paid_call(
            task_id=task_id,
            call_id=call_id,
            service_id=service.service_id,
            input_payload={"symbol": "BTC"},
            idempotency_key=idemp_key,
            task_budget_manager=budget_mgr,
        )

    assert result.status == PaymentStatus.PAID
    assert result.amount_base_units == 2000
    assert result.amount_usdc == "0.002"
    assert result.seller_output["price"] == 68500.0
    assert result.settlement_proof == "receipt_structured_valid_001"

    # Assert durable payment state in database
    db_attempt = integration_repo.get_attempt_by_id(result.request_id)
    assert db_attempt is not None
    assert db_attempt.status == "paid"
    assert db_attempt.amount_units == 2000


# ---------------------------------------------------------------------------
# Test 3: Seller rejects a request before payment (e.g. validation error)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_3_seller_rejects_request_before_payment(isolated_payment_service):
    """[MOCK-BASED] Verify seller rejection before payment releases budget and returns FAILED_AND_NOT_CHARGED."""
    service = catalog.get_service("data_001")
    task_id = "task_seller_reject_001"
    call_id = "step_1"
    idemp_key = f"idemp_{task_id}_{call_id}"
    budget_mgr = isolated_payment_service.get_or_create_task_budget(task_id, 100_000)

    # Simulate seller rejecting request with HTTP 422 before 402 challenge
    with patch.object(
        isolated_payment_service.adapter,
        "execute_paid_request",
        new=AsyncMock(return_value=(422, {"detail": "Unprocessable entity"}, None))
    ):
        result = await isolated_payment_service.execute_paid_call(
            task_id=task_id,
            call_id=call_id,
            service_id=service.service_id,
            input_payload={"invalid_field": 123},
            idempotency_key=idemp_key,
            task_budget_manager=budget_mgr,
        )

    assert result.status == PaymentStatus.FAILED_AND_NOT_CHARGED
    assert result.error_code == "HTTP_422"
    # Budget was completely released
    assert budget_mgr.available_budget == 100_000
    assert budget_mgr.total_spent == 0


# ---------------------------------------------------------------------------
# Test 4: Invalid or missing payment proof
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_4_invalid_or_missing_payment_proof(isolated_payment_service, integration_repo):
    """[MOCK-BASED] Verify missing payment proof in 200 OK transitions to PENDING_RECONCILIATION."""
    service = catalog.get_service("data_001")
    task_id = "task_missing_proof_001"
    call_id = "step_1"
    idemp_key = f"idemp_{task_id}_{call_id}"
    budget_mgr = isolated_payment_service.get_or_create_task_budget(task_id, 100_000)

    # Seller returns 200 OK but completely omits settlement proof header
    with patch.object(
        isolated_payment_service.adapter,
        "execute_paid_request",
        new=AsyncMock(return_value=(200, VALID_DATA_OUTPUT, None))
    ):
        result = await isolated_payment_service.execute_paid_call(
            task_id=task_id,
            call_id=call_id,
            service_id=service.service_id,
            input_payload={"symbol": "BTC"},
            idempotency_key=idemp_key,
            task_budget_manager=budget_mgr,
        )

    # Missing proof must NEVER become PAID; must transition to PENDING_RECONCILIATION
    assert result.status == PaymentStatus.PENDING_RECONCILIATION
    assert result.error_code == "SETTLEMENT_UNVERIFIED"

    # Budget reservation remains held in suspense (not released, not committed)
    assert budget_mgr.available_budget == 98_000
    assert budget_mgr.total_spent == 0

    # Durable DB state must be pending reconciliation
    db_attempt = integration_repo.get_attempt_by_id(result.request_id)
    assert db_attempt is not None
    assert db_attempt.status == "pending reconciliation"


# ---------------------------------------------------------------------------
# Test 5: Verifier returns None
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_5_verifier_returns_none(isolated_payment_service, integration_repo):
    """[MOCK-BASED] When settlement verifier returns None, attempt transitions to PENDING_RECONCILIATION."""
    service = catalog.get_service("data_001")
    task_id = "task_verifier_none_001"
    call_id = "step_1"
    idemp_key = f"idemp_{task_id}_{call_id}"
    budget_mgr = isolated_payment_service.get_or_create_task_budget(task_id, 100_000)

    with patch.object(
        isolated_payment_service.adapter,
        "execute_paid_request",
        new=AsyncMock(return_value=(200, VALID_DATA_OUTPUT, "receipt_unknown_001"))
    ), patch.object(
        isolated_payment_service.settlement_verifier,
        "verify_settlement_proof",
        new=AsyncMock(return_value=None)
    ):
        result = await isolated_payment_service.execute_paid_call(
            task_id=task_id,
            call_id=call_id,
            service_id=service.service_id,
            input_payload={"symbol": "BTC"},
            idempotency_key=idemp_key,
            task_budget_manager=budget_mgr,
        )

    assert result.status == PaymentStatus.PENDING_RECONCILIATION
    assert result.error_code == "SETTLEMENT_UNVERIFIED"
    assert budget_mgr.available_budget == 98_000
    assert budget_mgr.total_spent == 0


# ---------------------------------------------------------------------------
# Test 6: Verifier raises a timeout or RPC exception
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_6_verifier_raises_timeout_or_rpc_exception(isolated_payment_service, integration_repo):
    """[MOCK-BASED] When verifier raises timeout/RPC exception, attempt transitions to PENDING_RECONCILIATION."""
    service = catalog.get_service("data_001")
    task_id = "task_verifier_rpc_err_001"
    call_id = "step_1"
    idemp_key = f"idemp_{task_id}_{call_id}"
    budget_mgr = isolated_payment_service.get_or_create_task_budget(task_id, 100_000)

    with patch.object(
        isolated_payment_service.adapter,
        "execute_paid_request",
        new=AsyncMock(return_value=(200, VALID_DATA_OUTPUT, "receipt_rpc_timeout_001"))
    ), patch.object(
        isolated_payment_service.settlement_verifier,
        "verify_settlement_proof",
        new=AsyncMock(side_effect=SettlementTimeoutError("RPC endpoint timed out during verification"))
    ):
        result = await isolated_payment_service.execute_paid_call(
            task_id=task_id,
            call_id=call_id,
            service_id=service.service_id,
            input_payload={"symbol": "BTC"},
            idempotency_key=idemp_key,
            task_budget_manager=budget_mgr,
        )

    assert result.status == PaymentStatus.PENDING_RECONCILIATION
    assert budget_mgr.available_budget == 98_000
    assert budget_mgr.total_spent == 0


# ---------------------------------------------------------------------------
# Test 7: Malformed evidence or mismatched payer, recipient, amount, token, or network
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_7_malformed_evidence_or_mismatches_rejected():
    """[MOCK-BASED] SellerPaymentVerifier rejects mismatched network, token, recipient, and amount."""
    verifier = SellerPaymentVerifier(test_mode=True)
    req = verifier.issue_challenge(
        service_id="data_001",
        amount_units=2000,
        pay_to="0x0000000000000000000000000000000000000001",
    )

    # Mismatched network
    payload_bad_net = PaymentPayload(
        x402_version="2.0",
        scheme="exact",
        network="eip155:1",  # Mainnet instead of Base Sepolia
        token=USDC_BASE_SEPOLIA,
        buyer_address="0x0000000000000000000000000000000000000002",
        authorization={"network": "eip155:1", "token": USDC_BASE_SEPOLIA, "payTo": req.payTo},
        signature="0x_mock_sig",
    )
    with pytest.raises(SettlementVerificationError, match="Network mismatch"):
        await verifier.verify_and_settle(payload_bad_net, req)

    # Mismatched recipient
    payload_bad_recip = PaymentPayload(
        x402_version="2.0",
        scheme="exact",
        network=NETWORK_BASE_SEPOLIA,
        token=USDC_BASE_SEPOLIA,
        buyer_address="0x0000000000000000000000000000000000000002",
        authorization={"network": NETWORK_BASE_SEPOLIA, "token": USDC_BASE_SEPOLIA, "payTo": "0xWrongRecipient"},
        signature="0x_mock_sig",
    )
    with pytest.raises(SettlementVerificationError, match="Recipient mismatch"):
        await verifier.verify_and_settle(payload_bad_recip, req)


# ---------------------------------------------------------------------------
# Test 8: Seller output rejected after confirmed settlement
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_8_seller_output_rejected_after_confirmed_settlement(isolated_payment_service):
    """[MOCK-BASED] If settlement confirms but output fails catalog schema, status is PAID_OUTPUT_REJECTED."""
    service = catalog.get_service("data_001")
    task_id = "task_output_rejected_001"
    call_id = "step_1"
    idemp_key = f"idemp_{task_id}_{call_id}"
    budget_mgr = isolated_payment_service.get_or_create_task_budget(task_id, 100_000)

    # Missing required field 'price' according to data_001 schema
    with patch.object(
        isolated_payment_service.adapter,
        "execute_paid_request",
        new=AsyncMock(return_value=(200, {"symbol": "ETH", "corrupted": True}, "receipt_valid_schema_fail"))
    ):
        result = await isolated_payment_service.execute_paid_call(
            task_id=task_id,
            call_id=call_id,
            service_id=service.service_id,
            input_payload={"symbol": "ETH"},
            idempotency_key=idemp_key,
            task_budget_manager=budget_mgr,
        )

    assert result.status == PaymentStatus.PAID_OUTPUT_REJECTED
    assert result.error_code == "OUTPUT_SCHEMA_INVALID"
    # Money was committed because seller was settled
    assert budget_mgr.total_spent == 2000
    assert budget_mgr.available_budget == 98_000


# ---------------------------------------------------------------------------
# Test 9: Replayed idempotency key
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_9_replayed_idempotency_key(isolated_payment_service):
    """[MOCK-BASED] Replaying identical idempotency key returns cached result without second call."""
    service = catalog.get_service("data_001")
    task_id = "task_idemp_replay_001"
    call_id = "step_1"
    idemp_key = f"idemp_{task_id}_{call_id}"
    budget_mgr = isolated_payment_service.get_or_create_task_budget(task_id, 100_000)

    adapter_mock = AsyncMock(return_value=(200, VALID_ETH_OUTPUT, "receipt_idemp_001"))
    with patch.object(isolated_payment_service.adapter, "execute_paid_request", new=adapter_mock):
        result1 = await isolated_payment_service.execute_paid_call(
            task_id=task_id,
            call_id=call_id,
            service_id=service.service_id,
            input_payload={"symbol": "ETH"},
            idempotency_key=idemp_key,
            task_budget_manager=budget_mgr,
        )
        assert result1.status == PaymentStatus.PAID
        assert adapter_mock.call_count == 1

        # Second call with identical payload & key
        result2 = await isolated_payment_service.execute_paid_call(
            task_id=task_id,
            call_id=call_id,
            service_id=service.service_id,
            input_payload={"symbol": "ETH"},
            idempotency_key=idemp_key,
            task_budget_manager=budget_mgr,
        )
        assert result2.status == PaymentStatus.PAID
        assert result2.request_id == result1.request_id
        # Adapter was NOT called again
        assert adapter_mock.call_count == 1


# ---------------------------------------------------------------------------
# Test 10: Concurrent duplicate paid-call attempts
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_10_concurrent_duplicate_paid_call_attempts(isolated_payment_service):
    """[MOCK-BASED] Concurrent duplicate paid-call attempts with mutated payload raise conflict."""
    service = catalog.get_service("data_001")
    task_id = "task_concurrent_001"
    idemp_key = f"idemp_{task_id}_step_1"
    budget_mgr = isolated_payment_service.get_or_create_task_budget(task_id, 100_000)

    # First call completes
    with patch.object(
        isolated_payment_service.adapter,
        "execute_paid_request",
        new=AsyncMock(return_value=(200, VALID_ETH_OUTPUT, "receipt_conc_001"))
    ):
        res1 = await isolated_payment_service.execute_paid_call(
            task_id=task_id,
            call_id="call_1",
            service_id=service.service_id,
            input_payload={"symbol": "ETH"},
            idempotency_key=idemp_key,
            task_budget_manager=budget_mgr,
        )
        assert res1.status == PaymentStatus.PAID

    # Duplicate call with mutated payload raises IDEMPOTENCY_CONFLICT
    res2 = await isolated_payment_service.execute_paid_call(
        task_id=task_id,
        call_id="call_2",
        service_id=service.service_id,
        input_payload={"symbol": "BTC"},  # Mutated payload
        idempotency_key=idemp_key,
        task_budget_manager=budget_mgr,
    )
    assert res2.status == PaymentStatus.REFUSED
    assert res2.error_code == "IDEMPOTENCY_CONFLICT"


# ---------------------------------------------------------------------------
# Test 11: Ambiguous settlement transitions to pending reconciliation
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_11_ambiguous_settlement_transitions_to_pending_reconciliation(isolated_payment_service, integration_repo):
    """[MOCK-BASED] Network timeout during execution leaves budget in suspense and durable attempt pending."""
    service = catalog.get_service("data_001")
    task_id = "task_timeout_ambig_001"
    call_id = "step_1"
    idemp_key = f"idemp_{task_id}_{call_id}"
    budget_mgr = isolated_payment_service.get_or_create_task_budget(task_id, 100_000)

    with patch.object(
        isolated_payment_service.adapter,
        "execute_paid_request",
        new=AsyncMock(side_effect=SettlementTimeoutError("Adapter gateway timeout waiting for settlement confirmation"))
    ):
        result = await isolated_payment_service.execute_paid_call(
            task_id=task_id,
            call_id=call_id,
            service_id=service.service_id,
            input_payload={"symbol": "ETH"},
            idempotency_key=idemp_key,
            task_budget_manager=budget_mgr,
        )

    assert result.status == PaymentStatus.PENDING_RECONCILIATION
    assert result.error_code == "SETTLEMENT_TIMEOUT"
    # Budget reservation is held in suspense (not released)
    assert budget_mgr.available_budget == 98_000
    assert budget_mgr.total_spent == 0

    # Durable DB record
    db_attempt = integration_repo.get_attempt_by_id(result.request_id)
    assert db_attempt is not None
    assert db_attempt.status == "pending reconciliation"


# ---------------------------------------------------------------------------
# Test 12: Database restart and recovery of pending attempts
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_12_database_restart_and_recovery_of_pending_attempts(integration_repo):
    """[MOCK-BASED] Recover pending attempt across process restart and reconcile via endpoint."""
    attempt_id = "req_restart_recovery_001"
    task_id = "task_restart_001"
    idemp_key = "idemp_restart_recovery_001"
    service_id = "data_001"

    # Persist pending attempt in database as if process terminated
    integration_repo.save_attempt(PaymentAttemptRecord(
        attempt_id=attempt_id,
        task_id=task_id,
        call_id="step_1",
        service_id=service_id,
        idempotency_key=idemp_key,
        request_hash="hash_restart_001",
        amount_base_units=2000,
        pay_to="0x0000000000000000000000000000000000000001",
        status=PaymentStatus.PENDING_RECONCILIATION,
        settlement_proof="receipt_restart_valid_001",
    ))

    # Initialize brand new service instance simulating process restart
    policy = PaymentPolicyVerifier()
    settlement = SettlementVerifier(test_mode=True)
    adapter = X402Adapter(policy_verifier=policy, test_mode=True)
    new_service = PaymentService(
        policy_verifier=policy,
        settlement_verifier=settlement,
        adapter=adapter,
        store=IdempotencyStore(),
        durable_repo=integration_repo,
    )

    # 1. Recover pending attempts from DB
    pending = new_service.get_pending_reconciliations()
    assert attempt_id in pending
    assert pending[attempt_id].status == PaymentStatus.PENDING_RECONCILIATION

    # 2. Authoritative reconciliation confirms settlement
    outcome = await new_service.reconcile_attempt(attempt_id)
    assert outcome["reconciled"] is True
    assert outcome["status"] == "paid"

    # 3. Assert DB record updated to 'paid'
    db_attempt = integration_repo.get_attempt_by_id(attempt_id)
    assert db_attempt.status == "paid"


# ---------------------------------------------------------------------------
# Test 13: Budget reservation and release behavior for each lifecycle outcome
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_13_budget_reservation_and_release_for_all_outcomes(isolated_payment_service):
    """[MOCK-BASED] Explicitly test budget behavior across all five lifecycle states."""
    service = catalog.get_service("data_001")
    cost = service.price_base_units  # 2000

    # 1. Outcome: PAID (reserved -> committed)
    b1 = BudgetManager(initial_budget_units=10_000)
    with patch.object(isolated_payment_service.adapter, "execute_paid_request", new=AsyncMock(return_value=(200, VALID_ETH_OUTPUT, "receipt_1"))):
        r1 = await isolated_payment_service.execute_paid_call(
            task_id="t1", call_id="c1", service_id=service.service_id, input_payload={"symbol": "ETH"},
            idempotency_key="k1", task_budget_manager=b1,
        )
    assert r1.status == PaymentStatus.PAID
    assert b1.available_budget == 8_000
    assert b1.total_spent == 2_000

    # 2. Outcome: PAID_OUTPUT_REJECTED (reserved -> committed)
    b2 = BudgetManager(initial_budget_units=10_000)
    with patch.object(isolated_payment_service.adapter, "execute_paid_request", new=AsyncMock(return_value=(200, {"bad": "schema"}, "receipt_2"))):
        r2 = await isolated_payment_service.execute_paid_call(
            task_id="t2", call_id="c2", service_id=service.service_id, input_payload={"symbol": "ETH"},
            idempotency_key="k2", task_budget_manager=b2,
        )
    assert r2.status == PaymentStatus.PAID_OUTPUT_REJECTED
    assert b2.available_budget == 8_000
    assert b2.total_spent == 2_000

    # 3. Outcome: REFUSED (budget insufficient -> no charge)
    b3 = BudgetManager(initial_budget_units=1_000)  # less than 2000
    r3 = await isolated_payment_service.execute_paid_call(
        task_id="t3", call_id="c3", service_id=service.service_id, input_payload={"symbol": "ETH"},
        idempotency_key="k3", task_budget_manager=b3,
    )
    assert r3.status == PaymentStatus.REFUSED
    assert b3.available_budget == 1_000
    assert b3.total_spent == 0

    # 4. Outcome: FAILED_AND_NOT_CHARGED (seller returned 500 -> reservation released)
    b4 = BudgetManager(initial_budget_units=10_000)
    with patch.object(isolated_payment_service.adapter, "execute_paid_request", new=AsyncMock(return_value=(500, {"error": "crash"}, None))):
        r4 = await isolated_payment_service.execute_paid_call(
            task_id="t4", call_id="c4", service_id=service.service_id, input_payload={"symbol": "ETH"},
            idempotency_key="k4", task_budget_manager=b4,
        )
    assert r4.status == PaymentStatus.FAILED_AND_NOT_CHARGED
    assert b4.available_budget == 10_000
    assert b4.total_spent == 0

    # 5. Outcome: PENDING_RECONCILIATION (timeout -> held in suspense)
    b5 = BudgetManager(initial_budget_units=10_000)
    with patch.object(isolated_payment_service.adapter, "execute_paid_request", new=AsyncMock(side_effect=SettlementTimeoutError("timeout"))):
        r5 = await isolated_payment_service.execute_paid_call(
            task_id="t5", call_id="c5", service_id=service.service_id, input_payload={"symbol": "ETH"},
            idempotency_key="k5", task_budget_manager=b5,
        )
    assert r5.status == PaymentStatus.PENDING_RECONCILIATION
    # Suspense: funds reserved, not available, but not committed
    assert b5.available_budget == 8_000
    assert b5.total_spent == 0
