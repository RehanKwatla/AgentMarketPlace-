"""Integration tests proving Buyer Orchestration integration with Member 1 Payment and Member 4 Ledger interfaces."""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from backend.shared.constants import (
    NETWORK_BASE_SEPOLIA,
    USDC_BASE_SEPOLIA,
    LedgerStatus,
    ServiceCategory,
)
from backend.shared.config import get_settings

settings = get_settings()
from backend.shared.schemas import (
    PaymentRequirement,
    PaymentPayload,
    SettlementReceipt,
)
from backend.payments.budget import BudgetManager
from backend.payments.interfaces import BuyerPaymentClientInterface
from backend.ledger.models import ledger_repo
from backend.buyer.schemas import (
    CallStatus,
    TaskCreationRequest,
    TaskStatus,
)
from backend.buyer.service import BuyerService
from backend.buyer.plan_validator import PlannedCall


class MockMember1PaymentClient(BuyerPaymentClientInterface):
    """Mock of Member 1's BuyerPaymentClientInterface to verify call routing and trace."""

    def __init__(self):
        self.payload_calls = []
        self.settlement_calls = []
        self.fail_payload = False
        self.ambiguous_settlement = False

    async def create_payment_payload(
        self,
        requirement: PaymentRequirement,
        idempotency_key: str
    ) -> PaymentPayload:
        self.payload_calls.append({"requirement": requirement, "idempotency_key": idempotency_key})
        if self.fail_payload:
            raise ValueError("Member 1 payment payload creation rejected: Insufficient funds")

        return PaymentPayload(
            authorization={
                "network": requirement.network,
                "token": requirement.token,
                "amount": requirement.amount,
                "payTo": requirement.payTo,
                "nonce": requirement.nonce,
                "idempotency_key": idempotency_key
            },
            signature="0xmock_member1_sig",
            buyer_address="0x1000000000000000000000000000000000000001"
        )

    async def verify_settlement(
        self,
        receipt_header: str | None
    ) -> SettlementReceipt:
        self.settlement_calls.append(receipt_header)
        if self.ambiguous_settlement or not receipt_header:
            return SettlementReceipt(tx_hash=None, facilitator_receipt_id=None, settled_amount_units=0)

        return SettlementReceipt(
            tx_hash=receipt_header if receipt_header.startswith("0x") else None,
            facilitator_receipt_id=receipt_header if not receipt_header.startswith("0x") else None,
            settled_amount_units=2000
        )


@pytest.mark.asyncio
async def test_every_paid_call_routes_through_member1_payment_client():
    """Verify that every paid invocation delegates payload creation and settlement verification to Member 1."""
    mock_payment = MockMember1PaymentClient()
    service = BuyerService(payment_client=mock_payment)

    request = TaskCreationRequest(
        task="Collect crypto market data and summarize",
        budget_usdc="0.050000",
        execute_now=False
    )
    task_record = service.create_task(request)
    result = await service.execute_task(task_record.task_id)

    assert result.status in ["completed", "completed_with_warnings"]
    # Check that Member 1's interface was invoked
    assert len(mock_payment.payload_calls) >= 1
    assert len(mock_payment.settlement_calls) >= 1

    # Check payload parameters
    first_req = mock_payment.payload_calls[0]["requirement"]
    assert first_req.network == NETWORK_BASE_SEPOLIA
    assert first_req.token == USDC_BASE_SEPOLIA
    assert mock_payment.payload_calls[0]["idempotency_key"].startswith(f"idem_{task_record.task_id}")


@pytest.mark.asyncio
async def test_concurrent_calls_respect_budget_without_overdraw():
    """Test 3 concurrent calls executing in parallel without overdrawing budget."""
    budget_mgr = BudgetManager(initial_budget_units=6000)

    # 3 calls requesting 2000 units concurrently (exact sum = 6000)
    res1, res2, res3 = await asyncio.gather(
        budget_mgr.reserve("res_1", 2000),
        budget_mgr.reserve("res_2", 2000),
        budget_mgr.reserve("res_3", 2000),
    )
    assert budget_mgr.available_budget == 0

    # 4th concurrent call requesting 2000 units must fail atomically
    from backend.shared.errors import BudgetExceededError
    with pytest.raises(BudgetExceededError):
        await budget_mgr.reserve("res_4", 2000)

    # Clean commit
    await budget_mgr.commit("res_1", 2000)
    await budget_mgr.commit("res_2", 2000)
    await budget_mgr.commit("res_3", 2000)
    assert budget_mgr.available_budget == 0


@pytest.mark.asyncio
async def test_uncertain_settlement_on_missing_proof_transitions_to_pending_reconciliation():
    """Test that HTTP 200 without verified settlement proof transitions to pending reconciliation and holds budget."""
    mock_payment = MockMember1PaymentClient()
    mock_payment.ambiguous_settlement = True  # Simulates missing / unverified on-chain settlement
    service = BuyerService(payment_client=mock_payment)

    request = TaskCreationRequest(
        task="Collect crypto market data and summarize",
        budget_usdc="0.050000",
        execute_now=False
    )
    task_record = service.create_task(request)
    result = await service.execute_task(task_record.task_id)

    # Must transition to pending_reconciliation
    assert result.status == TaskStatus.PENDING_RECONCILIATION.value
    recon_calls = [c for c in result.calls if c.status == CallStatus.PENDING_RECONCILIATION]
    assert len(recon_calls) >= 1
    assert "uncertain" in recon_calls[0].error.lower()


@pytest.mark.asyncio
async def test_timeout_after_payment_dispatched_transitions_to_pending_reconciliation():
    """Test that a network timeout after sending payment payload is treated as uncertain and never blindly retried."""
    mock_payment = MockMember1PaymentClient()
    service = BuyerService(payment_client=mock_payment)

    # Force timeout in httpx client during paid post
    original_client = service._execute_call

    call_plan = PlannedCall(
        step_id=1,
        category="data",
        service_id="data_001",
        input_payload={"symbol": "ETH"},
        estimated_price_units=2000,
        depends_on=[]
    )
    budget_mgr = BudgetManager(initial_budget_units=10000)

    with patch("httpx.AsyncClient.post", side_effect=[
        # 1. 402 challenge response
        MagicMock(
            status_code=402,
            headers={
                "X-402-Requirement": json.dumps({
                    "version": "2.0",
                    "network": NETWORK_BASE_SEPOLIA,
                    "token": USDC_BASE_SEPOLIA,
                    "amount": "2000",
                    "payTo": settings.data_seller_pay_to,
                    "nonce": "test_nonce_timeout",
                    "service_id": "data_001"
                })
            }
        ),
        # 2. Timeout after payment payload was dispatched
        Exception("ReadTimeout: Network dropped after payload sent")
    ]):
        record = await service._execute_call(
            task_id="task_timeout_test",
            planned=call_plan,
            budget_mgr=budget_mgr,
            upstream_calls={},
            fallbacks=[],
            warnings=[]
        )

        # Must be pending reconciliation, not failed and not charged!
        assert record.status == CallStatus.PENDING_RECONCILIATION
        assert "timeout" in record.error.lower() or "uncertain" in record.error.lower()
        # Budget reservation was NOT released back to available!
        assert budget_mgr.available_budget == 8000  # 10000 - 2000 held


@pytest.mark.asyncio
async def test_member4_ledger_persistence_records_all_calls():
    """Verify that all executed calls are persisted into Member 4's ledger repository."""
    mock_payment = MockMember1PaymentClient()
    service = BuyerService(payment_client=mock_payment)

    initial_count = ledger_repo.count()
    request = TaskCreationRequest(
        task="Collect crypto market data and summarize",
        budget_usdc="0.050000",
        execute_now=True
    )
    result = await service.submit_and_execute_task(request)
    assert result.status in ["completed", "completed_with_warnings"]

    # Member 4's ledger repository should have new records
    new_count = ledger_repo.count()
    assert new_count > initial_count

    # Check that ledger record has status and valid identifiers
    records = ledger_repo.list_records(limit=10)
    assert len(records) > 0
    assert records[0].status in [LedgerStatus.PAID, LedgerStatus.PAID_OUTPUT_REJECTED]
    assert records[0].service_id in ["data_001", "inference_001", "scraping_001"]


@pytest.mark.asyncio
async def test_call_flow_trace_planning_and_validation_precede_payment():
    """Demonstrate call-flow trace proving that planning and plan validation strictly precede any payment."""
    trace = []

    class TracingPaymentClient(BuyerPaymentClientInterface):
        async def create_payment_payload(self, req, key):
            trace.append("MEMBER1_CREATE_PAYMENT_PAYLOAD")
            return PaymentPayload(
                authorization={"network": req.network, "token": req.token, "amount": req.amount, "payTo": req.payTo, "nonce": req.nonce},
                signature="0xtrace",
                buyer_address="0x1000000000000000000000000000000000000001"
            )

        async def verify_settlement(self, header):
            trace.append("MEMBER1_VERIFY_SETTLEMENT")
            return SettlementReceipt(tx_hash="0xtrace_tx", settled_amount_units=2000)

    service = BuyerService(payment_client=TracingPaymentClient())

    # Submitting over-budget task: plan validation fails immediately
    trace.append("START_TASK_SUBMISSION")
    request = TaskCreationRequest(
        task="Collect crypto market data and summarize",
        max_budget_atomic=500,  # Below service price 2000
        execute_now=True
    )
    result = await service.submit_and_execute_task(request)
    trace.append("TASK_REFUSED_BY_PLANNER")

    assert result.status == "refused"
    # Member 1 payment client was NEVER invoked because plan validation failed first!
    assert "MEMBER1_CREATE_PAYMENT_PAYLOAD" not in trace
    assert "MEMBER1_VERIFY_SETTLEMENT" not in trace
    assert trace == ["START_TASK_SUBMISSION", "TASK_REFUSED_BY_PLANNER"]
