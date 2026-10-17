"""Tests for Person A Phase 2 (Lifecycle & Diagnostics) and Phase 3 (Budget Enforcement & Explainable Selection)."""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, patch
import httpx

from backend.shared.constants import (
    NETWORK_BASE_SEPOLIA,
    USDC_BASE_SEPOLIA,
    LedgerStatus,
    ServiceCategory,
    base_units_to_usdc,
    usdc_to_base_units,
)
from backend.shared.config import get_settings
from backend.shared.schemas import (
    PaymentRequirement,
    PaymentPayload,
    SettlementReceipt,
)
from backend.payments.budget import BudgetManager
from backend.payments.interfaces import BuyerPaymentClientInterface
from backend.buyer.schemas import (
    CallStatus,
    TaskCreationRequest,
    TaskDetailResponse,
    TaskResultResponse,
    TaskStatus,
)
from backend.buyer.service import BuyerService
from backend.buyer.plan_validator import PlannedCall
from backend.registry.service import registry_service

settings = get_settings()


class MockLifecyclePaymentClient(BuyerPaymentClientInterface):
    """Configurable mock for Member 1 payment engine testing lifecycle states without real payments."""

    def __init__(
        self,
        fail_payload: bool = False,
        insufficient_funds: bool = False,
        ambiguous_settlement: bool = False,
        valid_tx_hash: str = "0x" + "7" * 64
    ):
        self.fail_payload = fail_payload
        self.insufficient_funds = insufficient_funds
        self.ambiguous_settlement = ambiguous_settlement
        self.valid_tx_hash = valid_tx_hash
        self.created_payloads = []
        self.verified_settlements = []

    async def create_payment_payload(
        self,
        requirement: PaymentRequirement,
        idempotency_key: str
    ) -> PaymentPayload:
        self.created_payloads.append((requirement, idempotency_key))
        if self.insufficient_funds:
            raise ValueError("Buyer wallet has insufficient USDC balance")
        if self.fail_payload:
            raise RuntimeError("Cryptographic signing failed")

        return PaymentPayload(
            authorization={
                "network": requirement.network,
                "token": requirement.token,
                "amount": requirement.amount,
                "payTo": requirement.payTo,
                "nonce": requirement.nonce,
                "idempotency_key": idempotency_key
            },
            signature="0xmock_signature_phase2",
            buyer_address="0x1111111111111111111111111111111111111111"
        )

    async def verify_settlement(
        self,
        receipt_header: str | None
    ) -> SettlementReceipt:
        self.verified_settlements.append(receipt_header)
        if self.ambiguous_settlement or not receipt_header:
            return SettlementReceipt(tx_hash=None, facilitator_receipt_id=None, settled_amount_units=0)

        return SettlementReceipt(
            tx_hash=self.valid_tx_hash,
            facilitator_receipt_id="fac_rec_999",
            settled_amount_units=2000
        )


# ==============================================================================
# PHASE 2 TESTS: TRANSACTION LIFECYCLE AND FAILURE DIAGNOSTICS
# ==============================================================================

@pytest.mark.asyncio
async def test_phase2_policy_verification_failure_diagnostic():
    """Policy violation: Seller requires payment to unverified recipient or wrong token."""
    mock_payment = MockLifecyclePaymentClient()
    service = BuyerService(payment_client=mock_payment)

    # Mock seller returning 402 with wrong token (counterfeit token address)
    fake_token = "0x9999999999999999999999999999999999999999"
    bad_requirement = {
        "service_id": "data_001",
        "network": NETWORK_BASE_SEPOLIA,
        "token": fake_token,
        "amount": "2000",
        "payTo": settings.data_seller_pay_to,
        "nonce": "nonce_123"
    }

    mock_resp_402 = httpx.Response(
        status_code=402,
        headers={"X-402-Requirement": json.dumps(bad_requirement)},
        content=b"Payment Required"
    )

    budget_mgr = BudgetManager(initial_budget_units=10000)
    planned = PlannedCall(
        step_id=1,
        service_id="data_001",
        category="data",
        estimated_price_units=2000,
        input_payload={"symbol": "ETH"},
        allow_fallback=False
    )

    with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_resp_402)):
        record = await service._execute_call(
            task_id="task_diag_pol",
            planned=planned,
            budget_mgr=budget_mgr,
            upstream_calls={},
            fallbacks=[],
            warnings=[]
        )

    # Diagnostics verification
    assert record.status == CallStatus.REFUSED
    assert record.error_code == "POLICY_VIOLATION"
    assert record.failure_stage == "policy_verification"
    assert "policy" in record.user_message.lower()
    assert record.is_settlement_confirmed is False
    assert record.transaction_hash is None
    # Budget was released back
    assert budget_mgr.available_budget == 10000


@pytest.mark.asyncio
async def test_phase2_insufficient_funds_diagnostic():
    """Insufficient funds in buyer wallet: Detected and reported with safe code."""
    mock_payment = MockLifecyclePaymentClient(insufficient_funds=True)
    service = BuyerService(payment_client=mock_payment)

    valid_requirement = {
        "service_id": "data_001",
        "network": NETWORK_BASE_SEPOLIA,
        "token": USDC_BASE_SEPOLIA,
        "amount": "2000",
        "payTo": settings.data_seller_pay_to,
        "nonce": "nonce_123"
    }

    mock_resp_402 = httpx.Response(
        status_code=402,
        headers={"X-402-Requirement": json.dumps(valid_requirement)},
        content=b"Payment Required"
    )

    budget_mgr = BudgetManager(initial_budget_units=10000)
    planned = PlannedCall(
        step_id=1,
        service_id="data_001",
        category="data",
        estimated_price_units=2000,
        input_payload={"symbol": "ETH"},
        allow_fallback=False
    )

    with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_resp_402)):
        record = await service._execute_call(
            task_id="task_diag_funds",
            planned=planned,
            budget_mgr=budget_mgr,
            upstream_calls={},
            fallbacks=[],
            warnings=[]
        )

    assert record.status == CallStatus.FAILED_AND_NOT_CHARGED
    assert record.error_code == "INSUFFICIENT_FUNDS"
    assert record.failure_stage == "payment_authorization"
    assert "insufficient" in record.user_message.lower()
    assert record.is_settlement_confirmed is False
    assert record.transaction_hash is None
    assert budget_mgr.available_budget == 10000


@pytest.mark.asyncio
async def test_phase2_seller_execution_failure_after_payment():
    """Seller execution failure: Seller returns HTTP 500 after payment payload dispatched."""
    mock_payment = MockLifecyclePaymentClient()
    service = BuyerService(payment_client=mock_payment)

    valid_requirement = {
        "service_id": "data_001",
        "network": NETWORK_BASE_SEPOLIA,
        "token": USDC_BASE_SEPOLIA,
        "amount": "2000",
        "payTo": settings.data_seller_pay_to,
        "nonce": "nonce_123"
    }

    resp_402 = httpx.Response(
        status_code=402,
        headers={"X-402-Requirement": json.dumps(valid_requirement)},
        content=b"Payment Required"
    )
    resp_500 = httpx.Response(
        status_code=500,
        content=b"Internal server error while fetching price from oracle"
    )

    budget_mgr = BudgetManager(initial_budget_units=10000)
    planned = PlannedCall(
        step_id=1,
        service_id="data_001",
        category="data",
        estimated_price_units=2000,
        input_payload={"symbol": "ETH"},
        allow_fallback=False
    )

    with patch("httpx.AsyncClient.post", AsyncMock(side_effect=[resp_402, resp_500])):
        record = await service._execute_call(
            task_id="task_diag_seller_err",
            planned=planned,
            budget_mgr=budget_mgr,
            upstream_calls={},
            fallbacks=[],
            warnings=[]
        )

    assert record.status == CallStatus.FAILED_AND_NOT_CHARGED
    assert record.error_code == "SELLER_EXECUTION_ERROR"
    assert record.failure_stage == "seller_execution"
    assert "execution error" in record.user_message.lower()
    assert record.is_settlement_confirmed is False
    assert record.payment_attempt_id is not None
    assert record.transaction_hash is None


@pytest.mark.asyncio
async def test_phase2_pending_ambiguous_settlement_does_not_retry_or_release():
    """HTTP 200 without settlement proof: Must enter PENDING_RECONCILIATION without blind retry or release."""
    mock_payment = MockLifecyclePaymentClient(ambiguous_settlement=True)
    service = BuyerService(payment_client=mock_payment)

    valid_requirement = {
        "service_id": "data_001",
        "network": NETWORK_BASE_SEPOLIA,
        "token": USDC_BASE_SEPOLIA,
        "amount": "2000",
        "payTo": settings.data_seller_pay_to,
        "nonce": "nonce_123"
    }

    resp_402 = httpx.Response(
        status_code=402,
        headers={"X-402-Requirement": json.dumps(valid_requirement)},
        content=b"Payment Required"
    )
    # HTTP 200 with data, but NO settlement proof header
    resp_200_no_proof = httpx.Response(
        status_code=200,
        headers={"content-type": "application/json"},
        json={"symbol": "ETH", "price": 3200.0, "volume_24h": 10000000.0, "timestamp": "2026-10-17T00:00:00Z"}
    )

    budget_mgr = BudgetManager(initial_budget_units=10000)
    planned = PlannedCall(
        step_id=1,
        service_id="data_001",
        category="data",
        estimated_price_units=2000,
        input_payload={"symbol": "ETH"},
        allow_fallback=False
    )

    with patch("httpx.AsyncClient.post", AsyncMock(side_effect=[resp_402, resp_200_no_proof])):
        record = await service._execute_call(
            task_id="task_diag_ambig",
            planned=planned,
            budget_mgr=budget_mgr,
            upstream_calls={},
            fallbacks=[],
            warnings=[]
        )

    # Check that HTTP 200 was NOT treated as proof of settlement
    assert record.status == CallStatus.PENDING_RECONCILIATION
    assert record.is_settlement_confirmed is False
    assert record.transaction_hash is None
    assert record.amount_paid_usdc == "0.000000"
    assert record.error_code == "SETTLEMENT_PENDING_RECONCILIATION"
    assert record.failure_stage == "settlement_verification"
    assert record.payment_attempt_id is not None
    # Crucial: Budget reservation is NOT released to prevent double-spending!
    assert budget_mgr.reserved_budget == 2000
    assert budget_mgr.available_budget == 8000


@pytest.mark.asyncio
async def test_phase2_confirmed_settlement_exposes_proof():
    """Confirmed settlement: Successfully verifies receipt and exposes tx_hash, network, attempt ID."""
    expected_tx = "0x" + "a" * 64
    mock_payment = MockLifecyclePaymentClient(valid_tx_hash=expected_tx)
    service = BuyerService(payment_client=mock_payment)

    valid_requirement = {
        "service_id": "data_001",
        "network": NETWORK_BASE_SEPOLIA,
        "token": USDC_BASE_SEPOLIA,
        "amount": "2000",
        "payTo": settings.data_seller_pay_to,
        "nonce": "nonce_123"
    }

    resp_402 = httpx.Response(
        status_code=402,
        headers={"X-402-Requirement": json.dumps(valid_requirement)},
        content=b"Payment Required"
    )
    resp_200 = httpx.Response(
        status_code=200,
        headers={
            "content-type": "application/json",
            "X-402-Settlement-Proof": expected_tx
        },
        json={"symbol": "ETH", "price": 3200.0, "volume_24h": 10000000.0, "timestamp": "2026-10-17T00:00:00Z"}
    )

    budget_mgr = BudgetManager(initial_budget_units=10000)
    planned = PlannedCall(
        step_id=1,
        service_id="data_001",
        category="data",
        estimated_price_units=2000,
        input_payload={"symbol": "ETH"},
        allow_fallback=False
    )

    with patch("httpx.AsyncClient.post", AsyncMock(side_effect=[resp_402, resp_200])):
        record = await service._execute_call(
            task_id="task_diag_confirmed",
            planned=planned,
            budget_mgr=budget_mgr,
            upstream_calls={},
            fallbacks=[],
            warnings=[]
        )

    assert record.status == CallStatus.SUCCEEDED
    assert record.is_settlement_confirmed is True
    assert record.transaction_hash == expected_tx
    assert usdc_to_base_units(record.amount_paid_usdc) == 2000
    assert record.network == NETWORK_BASE_SEPOLIA
    assert record.payment_attempt_id is not None
    assert record.ledger_reference == record.call_id
    assert budget_mgr.total_spent == 2000


@pytest.mark.asyncio
async def test_phase2_paid_call_output_rejected_no_false_refund():
    """Paid call whose output is rejected: Payment settled, but output fails schema validation."""
    expected_tx = "0x" + "b" * 64
    mock_payment = MockLifecyclePaymentClient(valid_tx_hash=expected_tx)
    service = BuyerService(payment_client=mock_payment)

    valid_requirement = {
        "service_id": "data_001",
        "network": NETWORK_BASE_SEPOLIA,
        "token": USDC_BASE_SEPOLIA,
        "amount": "2000",
        "payTo": settings.data_seller_pay_to,
        "nonce": "nonce_123"
    }

    resp_402 = httpx.Response(
        status_code=402,
        headers={"X-402-Requirement": json.dumps(valid_requirement)},
        content=b"Payment Required"
    )
    # Returns 200 with settlement proof, BUT invalid output schema (missing required fields symbol, price)
    resp_200_bad_schema = httpx.Response(
        status_code=200,
        headers={
            "content-type": "application/json",
            "X-402-Settlement-Proof": expected_tx
        },
        json={"error_custom": "not what the schema asked for"}
    )

    budget_mgr = BudgetManager(initial_budget_units=10000)
    planned = PlannedCall(
        step_id=1,
        service_id="data_001",
        category="data",
        estimated_price_units=2000,
        input_payload={"symbol": "ETH"},
        allow_fallback=False
    )

    with patch("httpx.AsyncClient.post", AsyncMock(side_effect=[resp_402, resp_200_bad_schema])):
        record = await service._execute_call(
            task_id="task_diag_rejected",
            planned=planned,
            budget_mgr=budget_mgr,
            upstream_calls={},
            fallbacks=[],
            warnings=[]
        )

    # Settled payment was committed, output was rejected
    assert record.status == CallStatus.PAID_OUTPUT_REJECTED
    assert record.is_settlement_confirmed is True
    assert record.transaction_hash == expected_tx
    assert usdc_to_base_units(record.amount_paid_usdc) == 2000
    assert record.error_code == "OUTPUT_VALIDATION_FAILED"
    assert record.failure_stage == "output_validation"
    assert budget_mgr.total_spent == 2000


# ==============================================================================
# PHASE 3 TESTS: BUYER BUDGET AND SERVICE SELECTION
# ==============================================================================

def test_phase3_invalid_budget_rejected_server_side():
    """Negative, zero, or non-numeric budgets must be rejected by TaskCreationRequest."""
    from pydantic import ValidationError

    # Negative budget
    with pytest.raises(ValidationError) as exc:
        TaskCreationRequest(task="Test task", budget_usdc="-0.010000")
    assert "positive" in str(exc.value).lower()

    # Zero budget
    with pytest.raises(ValidationError) as exc:
        TaskCreationRequest(task="Test task", budget_usdc="0.000000")
    assert "positive" in str(exc.value).lower()

    # Non-numeric string
    with pytest.raises(ValidationError) as exc:
        TaskCreationRequest(task="Test task", budget_usdc="not_a_number")
    assert "valid" in str(exc.value).lower()


def test_phase3_budget_exceeding_server_limit_rejected():
    """Budget exceeding server limit (buyer_max_budget_usdc) is rejected server-side."""
    from pydantic import ValidationError

    # Server limit defaults to 1.000000 USDC
    with pytest.raises(ValidationError) as exc:
        TaskCreationRequest(task="Large expensive task", budget_usdc="50.000000")
    assert "exceeds" in str(exc.value).lower() and "server limit" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_phase3_task_exceeding_budget_rejected_before_payment():
    """Task requiring services whose cost exceeds budget is refused during planning without payment authorization."""
    mock_payment = MockLifecyclePaymentClient()
    service = BuyerService(payment_client=mock_payment)

    # Budget 0.001000 USDC (1000 units), but data_001 costs 2000 units
    request = TaskCreationRequest(
        task="Lookup ETH price",
        budget_usdc="0.001000",
        execute_now=True
    )

    task_record = await service.submit_and_execute_task(request)

    assert task_record.status == TaskStatus.REFUSED.value
    assert task_record.failure_code == "INSUFFICIENT_BUDGET"
    assert task_record.failure_stage == "planning"
    assert task_record.spent_usdc == "0.000000"
    # Zero payment payloads were generated!
    assert len(mock_payment.created_payloads) == 0


@pytest.mark.asyncio
async def test_phase3_multi_call_plan_exceeding_budget_rejected():
    """Multi-call plan whose combined cost exceeds budget is rejected before execution."""
    mock_payment = MockLifecyclePaymentClient()
    service = BuyerService(payment_client=mock_payment)

    # Multi-hop prompt requires data (2000) + scrape (3000) + inference (5000) = 10000 units = 0.010000 USDC
    # Allocate only 0.004000 USDC (4000 units)
    request = TaskCreationRequest(
        task="Fetch ETH price, scrape ethereum.org, and synthesize a deep analytical summary",
        budget_usdc="0.004000",
        execute_now=True
    )

    task_record = await service.submit_and_execute_task(request)

    assert task_record.status == TaskStatus.REFUSED.value
    assert task_record.failure_code == "INSUFFICIENT_BUDGET"
    assert task_record.failure_stage == "planning"
    assert task_record.spent_usdc == "0.000000"
    assert len(mock_payment.created_payloads) == 0


@pytest.mark.asyncio
async def test_phase3_duplicate_task_submission_idempotency():
    """Submitting duplicate task with same idempotency_key returns identical task record without re-execution."""
    mock_payment = MockLifecyclePaymentClient()
    service = BuyerService(payment_client=mock_payment)
    idem_key = "client_task_submission_key_001"

    request1 = TaskCreationRequest(
        task="Lookup ETH price",
        budget_usdc="0.020000",
        idempotency_key=idem_key,
        execute_now=False
    )
    task1 = await service.submit_and_execute_task(request1)

    request2 = TaskCreationRequest(
        task="Lookup ETH price",
        budget_usdc="0.020000",
        idempotency_key=idem_key,
        execute_now=False
    )
    task2 = await service.submit_and_execute_task(request2)

    assert task1.task_id == task2.task_id
    assert task2.idempotency_key == idem_key


@pytest.mark.asyncio
async def test_phase3_explainable_service_selection_no_invented_scores():
    """Explainable service selection must use actual selection data without fabricating scores."""
    from backend.buyer.planner import TaskPlanner

    planner = TaskPlanner()
    request = TaskCreationRequest(
        task="Lookup ETH price and market data",
        budget_usdc="0.050000"
    )

    plan = planner.create_plan(request)
    assert len(plan.calls) >= 1

    first_call = plan.calls[0]
    # Check that selection details exist
    assert first_call.selection_details is not None
    sel_data = first_call.selection_details

    # Factual fields present
    assert "requested_capability" in sel_data
    assert "selected_service" in sel_data
    assert "price_used_usdc" in sel_data
    assert "budget_compatible" in sel_data
    assert sel_data["budget_compatible"] is True

    # Alternatives were evaluated
    assert "evaluated_alternatives" in sel_data
    assert isinstance(sel_data["evaluated_alternatives"], list)

    # Check that NO fabricated scores (such as capability_score, ranking_number) are present
    assert "capability_score" not in sel_data
    assert "ranking_score" not in sel_data
    assert "invented_score" not in sel_data
