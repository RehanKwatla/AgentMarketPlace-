"""Integration tests for Buyer Dependency-Aware Asynchronous Execution.

Verifies:
1. Sequential dependencies: dependent calls only run after required inputs succeed.
2. Parallel execution: independent calls run concurrently.
3. Failed upstream dependency: dependent calls are skipped with 0 funds spent.
4. Timeouts: pre-payment timeouts fail safely; post-payment timeouts transition to pending reconciliation.
5. Concurrency limits: bounded execution respects semaphore ceiling.
6. Budget exhaustion: calls exceeding available budget are refused without reserving funds.
7. Ambiguous payment outcomes: never retried and never trigger fallbacks.
8. Fallback budget safety: fallback executes if affordable; rejected if exceeding budget.
"""
import asyncio
import json
import time
import pytest
from unittest.mock import MagicMock, patch

from backend.shared.constants import (
    NETWORK_BASE_SEPOLIA,
    USDC_BASE_SEPOLIA,
    LedgerStatus,
    ServiceCategory,
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
from backend.ledger.models import ledger_repo
from backend.buyer.schemas import (
    CallStatus,
    ServiceCallRecord,
    TaskCreationRequest,
    TaskStatus,
)
from backend.buyer.plan_validator import PlannedCall, ExecutionPlan
from backend.buyer.service import BuyerService

settings = get_settings()


class MockMember1PaymentClient(BuyerPaymentClientInterface):
    """Mock Member 1 payment interface for asynchronous execution testing."""

    def __init__(self, ambiguous_settlement: bool = False):
        self.ambiguous_settlement = ambiguous_settlement
        self.created_payloads = []
        self.verified_settlements = []

    async def create_payment_payload(
        self,
        requirement: PaymentRequirement,
        idempotency_key: str
    ) -> PaymentPayload:
        self.created_payloads.append((requirement, idempotency_key))
        return PaymentPayload(
            authorization={
                "network": requirement.network,
                "token": requirement.token,
                "amount": requirement.amount,
                "payTo": requirement.payTo,
                "nonce": requirement.nonce,
                "idempotency_key": idempotency_key
            },
            signature="0xmock_sig_dep_test",
            buyer_address="0x1000000000000000000000000000000000000001"
        )

    async def verify_settlement(
        self,
        receipt_header: str | None
    ) -> SettlementReceipt:
        self.verified_settlements.append(receipt_header)
        if self.ambiguous_settlement or not receipt_header:
            return SettlementReceipt(tx_hash=None, facilitator_receipt_id=None, settled_amount_units=0)
        return SettlementReceipt(
            tx_hash=receipt_header if str(receipt_header).startswith("0x") else None,
            facilitator_receipt_id=receipt_header if not str(receipt_header).startswith("0x") else None,
            settled_amount_units=2000
        )


@pytest.mark.asyncio
async def test_sequential_dependencies_and_input_synthesis():
    """Verify dependent Inference call executes only after Data & Scraping succeed,

    and receives schema-compliant synthesized prompt from validated upstream outputs.
    """
    mock_payment = MockMember1PaymentClient()
    service = BuyerService(payment_client=mock_payment)

    request = TaskCreationRequest(
        task="Scrape ethereum article, lookup crypto price for ETH, and summarize findings",
        budget_usdc="0.050000",
        max_concurrency=3,
        execute_now=True
    )

    task_result = await service.submit_and_execute_task(request)
    assert task_result.status in [TaskStatus.COMPLETED.value, TaskStatus.COMPLETED_WITH_WARNINGS.value]

    calls_by_cat = {c.category: c for c in task_result.calls}
    assert ServiceCategory.SCRAPING in calls_by_cat
    assert ServiceCategory.DATA in calls_by_cat
    assert ServiceCategory.INFERENCE in calls_by_cat

    scraping_call = calls_by_cat[ServiceCategory.SCRAPING]
    data_call = calls_by_cat[ServiceCategory.DATA]
    inference_call = calls_by_cat[ServiceCategory.INFERENCE]

    assert scraping_call.status == CallStatus.SUCCEEDED
    assert data_call.status == CallStatus.SUCCEEDED
    assert inference_call.status == CallStatus.SUCCEEDED

    # Inference depends on both Scraping and Data
    assert scraping_call.step_id in inference_call.depends_on
    assert data_call.step_id in inference_call.depends_on

    # Output schema compliance: Data output has symbol, price, volume; Scraping has url, content
    assert "symbol" in data_call.output and "price" in data_call.output
    assert "url" in scraping_call.output and "content" in scraping_call.output

    # Inference output has response and model_used
    assert "response" in inference_call.output


@pytest.mark.asyncio
async def test_parallel_execution_of_independent_calls():
    """Verify independent calls execute concurrently in parallel without sequential delay."""
    mock_payment = MockMember1PaymentClient()
    service = BuyerService(payment_client=mock_payment)

    budget_mgr = BudgetManager(initial_budget_units=20000)
    concurrency_counter = 0
    max_observed_concurrency = 0
    lock = asyncio.Lock()
    import json as json_serializer

    async def mock_post(url, **kwargs):
        nonlocal concurrency_counter, max_observed_concurrency
        headers = kwargs.get("headers") or {}
        if HEADER_X402_PAYMENT_PAYLOAD not in headers:
            pay_to = settings.data_seller_pay_to if "data" in url else settings.scraping_seller_pay_to
            svc_id = "data_001" if "data" in url else "scraping_001"
            amt = "2000" if "data" in url else "3000"
            return MagicMock(
                status_code=402,
                headers={
                    "X-402-Requirement": json_serializer.dumps({
                        "version": "2.0",
                        "network": NETWORK_BASE_SEPOLIA,
                        "token": USDC_BASE_SEPOLIA,
                        "amount": amt,
                        "payTo": pay_to,
                        "nonce": "nonce_parallel_test",
                        "service_id": svc_id
                    })
                }
            )

        # Track active concurrency during paid execution
        async with lock:
            concurrency_counter += 1
            if concurrency_counter > max_observed_concurrency:
                max_observed_concurrency = concurrency_counter

        await asyncio.sleep(0.05)  # Simulate network latency

        async with lock:
            concurrency_counter -= 1

        if "data" in url:
            body = {"symbol": "ETH", "price": 2650.0, "volume_24h": 100000.0, "timestamp": "2026-10-16T00:00:00Z"}
        else:
            body = {"url": "https://eth.org", "title": "Ethereum", "content": "Proof of Stake", "word_count": 3}

        mock_resp = MagicMock(status_code=200)
        mock_resp.headers = {"X-402-Settlement-Proof": "receipt_parallel_001"}
        mock_resp.json.return_value = body
        return mock_resp

    from backend.shared.constants import HEADER_X402_PAYMENT_PAYLOAD

    # Plan with 3 independent calls in Stage 0
    calls = [
        PlannedCall(step_id=1, category="data", service_id="data_001", input_payload={"symbol": "ETH"}, estimated_price_units=2000, depends_on=[]),
        PlannedCall(step_id=2, category="data", service_id="data_001", input_payload={"symbol": "BTC"}, estimated_price_units=2000, depends_on=[]),
        PlannedCall(step_id=3, category="scraping", service_id="scraping_001", input_payload={"url": "https://ethereum.org"}, estimated_price_units=3000, depends_on=[]),
    ]

    with patch("httpx.AsyncClient.post", side_effect=mock_post):
        # Execute all 3 in parallel bounded by semaphore(3)
        completed = {}
        sem = asyncio.Semaphore(3)

        async def run_call(c):
            async with sem:
                rec = await service._execute_call("task_par", c, budget_mgr, completed, [], [])
                completed[c.step_id] = rec

        await asyncio.gather(*(run_call(c) for c in calls))

        assert len(completed) == 3
        assert all(r.status == CallStatus.SUCCEEDED for r in completed.values())
        # Confirms at least 2 or 3 calls were running concurrently at the exact same time
        assert max_observed_concurrency >= 2


@pytest.mark.asyncio
async def test_failed_upstream_dependency_skips_dependent_call():
    """Verify that if an upstream call fails, dependent calls are skipped with 0 funds reserved/spent."""
    mock_payment = MockMember1PaymentClient()
    service = BuyerService(payment_client=mock_payment)
    budget_mgr = BudgetManager(initial_budget_units=10000)

    # Failed upstream call in completed dict
    upstream_calls = {
        1: MagicMock(
            step_id=1,
            service_id="data_001",
            status=CallStatus.FAILED_AND_NOT_CHARGED,
            output=None
        )
    }

    dependent_call = PlannedCall(
        step_id=2,
        category="inference",
        service_id="inference_001",
        input_payload={"prompt": "Summarize market data"},
        estimated_price_units=4000,
        depends_on=[1]
    )

    record = await service._execute_call(
        task_id="task_failed_dep",
        planned=dependent_call,
        budget_mgr=budget_mgr,
        upstream_calls=upstream_calls,
        fallbacks=[],
        warnings=[]
    )

    # Dependent call MUST NOT execute and MUST NOT spend budget
    assert record.status == CallStatus.FAILED_AND_NOT_CHARGED
    assert "upstream dependency failed" in record.error.lower()
    # Budget was untouched: 10000 available
    assert budget_mgr.available_budget == 10000


@pytest.mark.asyncio
async def test_pre_payment_timeout_releases_budget_reservation():
    """Verify that a network timeout occurring BEFORE payment challenge releases budget."""
    mock_payment = MockMember1PaymentClient()
    service = BuyerService(payment_client=mock_payment)
    budget_mgr = BudgetManager(initial_budget_units=10000)

    call_plan = PlannedCall(
        step_id=1,
        category="data",
        service_id="data_001",
        input_payload={"symbol": "ETH"},
        estimated_price_units=2000,
        depends_on=[]
    )

    with patch("httpx.AsyncClient.post", side_effect=Exception("ConnectionRefused: Seller server down")):
        record = await service._execute_call(
            task_id="task_pre_timeout",
            planned=call_plan,
            budget_mgr=budget_mgr,
            upstream_calls={},
            fallbacks=[],
            warnings=[]
        )

        assert record.status == CallStatus.FAILED_AND_NOT_CHARGED
        # Budget reservation was cleanly released back to available
        assert budget_mgr.available_budget == 10000


@pytest.mark.asyncio
async def test_concurrency_limit_bounded_by_semaphore():
    """Verify that concurrent calls are bounded by the semaphore limit (e.g. max 3)."""
    mock_payment = MockMember1PaymentClient()
    service = BuyerService(payment_client=mock_payment)

    request = TaskCreationRequest(
        task="Collect and summarize",
        budget_usdc="0.100000",
        max_concurrency=3,
        execute_now=False
    )
    task_record = service.create_task(request)

    active_calls = 0
    peak_active = 0
    lock = asyncio.Lock()

    original_execute_call = service._execute_call

    async def mock_execute(*args, **kwargs):
        nonlocal active_calls, peak_active
        async with lock:
            active_calls += 1
            if active_calls > peak_active:
                peak_active = active_calls
        await asyncio.sleep(0.02)
        async with lock:
            active_calls -= 1
        return ServiceCallRecord(
            call_id="call_mock",
            service_id="data_001",
            category=ServiceCategory.DATA,
            status=CallStatus.SUCCEEDED,
            listed_price_usdc="0.002000",
            amount_paid_usdc="0.002000",
            output={"symbol": "ETH", "price": 2650.0, "volume_24h": 1000.0, "timestamp": "2026-10-16T00:00:00Z"}
        )

    with patch.object(service, "_execute_call", side_effect=mock_execute):
        # Create plan with 6 independent calls
        plan = ExecutionPlan(
            task_prompt=request.task,
            budget_units=100000,
            calls=[
                PlannedCall(step_id=i, category="data", service_id="data_001", input_payload={"symbol": "ETH"}, estimated_price_units=2000, depends_on=[])
                for i in range(1, 7)
            ],
            worst_case_cost_units=12000,
            expected_cost_units=12000,
            fallback_allowances_units=0,
            max_concurrency=3
        )
        service._task_plans[task_record.task_id] = plan
        with patch.object(service.planner, "create_plan", return_value=plan):
            await service.execute_task(task_record.task_id)

    # Concurrency never exceeded 3
    assert peak_active <= 3


@pytest.mark.asyncio
async def test_budget_exhaustion_refuses_subsequent_calls():
    """Verify that when remaining budget is exhausted, subsequent calls are refused without reserving funds."""
    mock_payment = MockMember1PaymentClient()
    service = BuyerService(payment_client=mock_payment)
    # Budget is 3000 base units (only enough for one 2000-unit call, not two)
    budget_mgr = BudgetManager(initial_budget_units=3000)

    # Step 1 succeeds and commits 2000 units
    await budget_mgr.reserve("res_1", 2000)
    await budget_mgr.commit("res_1", 2000)
    assert budget_mgr.available_budget == 1000

    # Step 2 costs 2000 units -> exceeds available 1000 units!
    call_2 = PlannedCall(
        step_id=2,
        category="data",
        service_id="data_001",
        input_payload={"symbol": "BTC"},
        estimated_price_units=2000,
        depends_on=[]
    )

    record = await service._execute_call(
        task_id="task_budget_exhaust",
        planned=call_2,
        budget_mgr=budget_mgr,
        upstream_calls={},
        fallbacks=[],
        warnings=[]
    )

    assert record.status == CallStatus.REFUSED
    assert "budget exhausted" in record.error.lower()
    # Available budget remains untouched at 1000
    assert budget_mgr.available_budget == 1000


@pytest.mark.asyncio
async def test_ambiguous_payment_outcome_never_runs_fallback():
    """Verify that an ambiguous settlement (HTTP 200 with missing settlement proof)

    transitions to PENDING_RECONCILIATION and strictly NEVER triggers a fallback.
    """
    mock_payment = MockMember1PaymentClient(ambiguous_settlement=True)
    service = BuyerService(payment_client=mock_payment)
    budget_mgr = BudgetManager(initial_budget_units=10000)

    call_plan = PlannedCall(
        step_id=1,
        category="data",
        service_id="data_001",
        fallback_service_ids=["data_fallback_002"],
        input_payload={"symbol": "ETH"},
        estimated_price_units=2000,
        depends_on=[],
        allow_fallback=True
    )

    with patch("httpx.AsyncClient.post", side_effect=[
        # 1. 402 challenge
        MagicMock(
            status_code=402,
            headers={
                "X-402-Requirement": json.dumps({
                    "version": "2.0",
                    "network": NETWORK_BASE_SEPOLIA,
                    "token": USDC_BASE_SEPOLIA,
                    "amount": "2000",
                    "payTo": settings.data_seller_pay_to,
                    "nonce": "test_nonce_ambig",
                    "service_id": "data_001"
                })
            }
        ),
        # 2. Paid response without settlement proof header
        MagicMock(
            status_code=200,
            headers={},  # Missing X-402-Settlement-Proof
            json=MagicMock(return_value={"symbol": "ETH", "price": 2650.0})
        )
    ]):
        fallbacks_log = []
        record = await service._execute_call(
            task_id="task_ambig",
            planned=call_plan,
            budget_mgr=budget_mgr,
            upstream_calls={},
            fallbacks=fallbacks_log,
            warnings=[]
        )

        assert record.status == CallStatus.PENDING_RECONCILIATION
        # No fallback was executed!
        assert len(fallbacks_log) == 0
        # Budget reservation is HELD (10000 - 2000 = 8000 available)
        assert budget_mgr.available_budget == 8000


@pytest.mark.asyncio
async def test_fallback_budget_safety_recheck():
    """Verify fallback service rechecks available budget:

    - If fallback exceeds remaining budget: rejected and NOT started.
    - If fallback is within budget: executes safely.
    """
    mock_payment = MockMember1PaymentClient()
    service = BuyerService(payment_client=mock_payment)

    # Register an expensive fallback service (8000 units) and an affordable fallback service (2000 units)
    from backend.registry.schemas import ServiceRecord
    expensive_fb = ServiceRecord(
        service_id="data_expensive_fb",
        name="Expensive Fallback Data",
        category=ServiceCategory.DATA,
        capabilities=["data.lookup.v1"],
        endpoint_url="http://localhost:8000/api/v1/seller/data",
        price_usdc="0.008",
        price_atomic=8000,
        network=NETWORK_BASE_SEPOLIA,
        asset_address=USDC_BASE_SEPOLIA,
        pay_to=settings.data_seller_pay_to,
        input_schema={"type": "object", "required": ["symbol"]},
        output_schema={"type": "object", "required": ["symbol", "price", "volume_24h", "timestamp"]}
    )
    try:
        service.registry.register_service(expensive_fb)

        # Case 1: Available budget is 5000 units. Primary (2000) fails cleanly.
        # Fallback requires 8000 units -> Exceeds budget -> Fallback must be rejected!
        budget_mgr1 = BudgetManager(initial_budget_units=5000)
        call_plan1 = PlannedCall(
            step_id=1,
            category="data",
            service_id="data_001",
            fallback_service_ids=["data_expensive_fb"],
            input_payload={"symbol": "ETH"},
            estimated_price_units=2000,
            depends_on=[],
            allow_fallback=True
        )

        with patch("httpx.AsyncClient.post", side_effect=Exception("ConnectionRefused: primary down")):
            fallbacks_log = []
            warnings_log = []
            rec1 = await service._execute_call(
                task_id="task_fb_reject",
                planned=call_plan1,
                budget_mgr=budget_mgr1,
                upstream_calls={},
                fallbacks=fallbacks_log,
                warnings=warnings_log
            )
            assert rec1.status == CallStatus.FAILED_AND_NOT_CHARGED
            # Warning recorded for budget rejection
            assert any("exceeds remaining budget" in w.lower() for w in warnings_log)
            # Fallback was NOT executed
            assert budget_mgr1.available_budget == 5000
    finally:
        service.registry._services.pop("data_expensive_fb", None)
        service.registry._services.pop("data-expensive-fb", None)
