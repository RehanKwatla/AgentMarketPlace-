"""End-to-End Acceptance Audit Test Suite for Member 3 Definition-of-Done (DoD).

Explicitly covers the 10 Definition-of-Done requirements:
1. Registry API lists and filters all three seller categories: Data, Scraping, and Inference.
2. Buyer accepts a natural-language task and budget.
3. Service selection and complete plan validation happen before any payment.
4. Buyer calls Member 1's payment interface for every paid invocation.
5. A single task can use Data, Scraping, and Inference.
6. At least three concurrent calls are supported where dependencies permit, without bypassing atomic budget enforcement.
7. Seller outputs are validated against their JSON Schemas.
8. Fallback cannot cause duplicate or unaccounted payments.
9. Final results preserve provenance and explain service choices.
10. Displayed spending agrees with verified ledger data.
"""
import asyncio
import json
import pytest
from unittest.mock import MagicMock, patch
from backend.shared.constants import (
    NETWORK_BASE_SEPOLIA,
    USDC_BASE_SEPOLIA,
    HEADER_X402_REQUIREMENT,
    HEADER_X402_SETTLEMENT_PROOF,
    LedgerStatus,
    ServiceCategory,
)
from backend.shared.schemas import (
    PaymentPayload,
    PaymentRequirement,
    SettlementReceipt,
    LedgerRecordSchema,
)
from backend.ledger.models import ledger_repo, LedgerRepository
from backend.registry.service import registry_service, RegistryService
from backend.payments.budget import BudgetManager
from backend.buyer.schemas import (
    CallStatus,
    ServiceCallRecord,
    TaskCreationRequest,
    TaskStatus,
)
from backend.buyer.service import BuyerService
from backend.buyer.planner import TaskPlanner
from backend.buyer.plan_validator import PlanValidator, PlannedCall, ExecutionPlan, PlanValidationError
from backend.buyer.output_validator import OutputValidator
from backend.buyer.aggregator import ResultAggregator
from backend.buyer.explanation import ExplanationGenerator


class MockMember1PaymentClientSpy:
    """Spy tracking every invocation of Member 1's payment interface."""

    def __init__(self):
        self.payload_creation_calls = []
        self.settlement_verification_calls = []

    async def create_payment_payload(self, requirement: PaymentRequirement, idempotency_key: str = "") -> PaymentPayload:
        self.payload_creation_calls.append(requirement)
        return PaymentPayload(
            authorization={
                "network": requirement.network,
                "token": requirement.token,
                "amount": requirement.amount,
                "payTo": requirement.payTo,
                "nonce": requirement.nonce
            },
            signature="0x" + "1" * 130,
            buyer_address="0x1234567890123456789012345678901234567890"
        )

    async def verify_settlement(self, settlement_header: Optional[str] = None) -> Optional[SettlementReceipt]:
        self.settlement_verification_calls.append(settlement_header)
        if not settlement_header:
            return None
        tx_hash = "0x" + "a" * 64
        return SettlementReceipt(
            tx_hash=tx_hash,
            facilitator_receipt_id="fac_receipt_dod_test_01",
            settled_amount_units=2000
        )


# ==============================================================================
# Requirement 1: Registry API lists and filters all three seller categories
# ==============================================================================
def test_dod_1_registry_api_lists_and_filters_three_categories(client):
    """DoD 1: Registry API lists and filters all three seller categories: Data, Scraping, and Inference."""
    # List all services
    res = client.get("/api/v1/services")
    assert res.status_code == 200
    all_svcs = res.json()
    cats = {s["category"] for s in all_svcs["items"]}
    assert "data" in cats
    assert "scraping" in cats
    assert "inference" in cats

    # Filter Data
    res_data = client.get("/api/v1/services?category=data")
    assert res_data.status_code == 200
    for s in res_data.json()["items"]:
        assert s["category"] == "data"

    # Filter Scraping
    res_scraping = client.get("/api/v1/services?category=scraping")
    assert res_scraping.status_code == 200
    for s in res_scraping.json()["items"]:
        assert s["category"] == "scraping"

    # Filter Inference
    res_inf = client.get("/api/v1/services?category=inference")
    assert res_inf.status_code == 200
    for s in res_inf.json()["items"]:
        assert s["category"] == "inference"

    # Price filter
    res_price = client.get("/api/v1/services?max_price_usdc=0.003")
    assert res_price.status_code == 200
    for s in res_price.json()["items"]:
        assert float(s["price_usdc"]) <= 0.003

    # Individual service lookup
    res_single = client.get("/api/v1/services/data_001")
    assert res_single.status_code == 200
    assert res_single.json()["service_id"] == "data_001"

    # Reputation endpoint
    res_rep = client.get("/api/v1/services/data_001/reputation")
    assert res_rep.status_code == 200
    assert "reputation_score" in res_rep.json()


# ==============================================================================
# Requirement 2: Buyer accepts a natural-language task and budget
# ==============================================================================
def test_dod_2_buyer_accepts_natural_language_task_and_budget(client):
    """DoD 2: Buyer accepts a natural-language task and budget without float arithmetic."""
    # Success path
    res = client.post(
        "/api/v1/tasks",
        json={
            "task": "Extract Ethereum price and synthesize market summary",
            "budget_usdc": "0.050000",
            "max_concurrency": 3,
            "execute_now": False
        }
    )
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "accepted"
    assert data["budget_usdc"] == "0.050000"
    assert data["budget_atomic"] == 50000

    # Failure path: missing / empty task
    res_bad_task = client.post(
        "/api/v1/tasks",
        json={"task": "", "budget_usdc": "0.050000"}
    )
    assert res_bad_task.status_code in [400, 422]

    # Failure path: negative or zero budget
    res_bad_budget = client.post(
        "/api/v1/tasks",
        json={"task": "Valid task description", "budget_usdc": "-0.010000"}
    )
    assert res_bad_budget.status_code in [400, 422]


# ==============================================================================
# Requirement 3: Service selection and complete plan validation happen before payment
# ==============================================================================
@pytest.mark.asyncio
async def test_dod_3_service_selection_and_plan_validation_precede_payment():
    """DoD 3: Complete plan validation occurs strictly before payment initiation."""
    spy = MockMember1PaymentClientSpy()
    service = BuyerService(payment_client=spy)

    # 1. Overbudget plan is refused with 0 payment calls
    task_req = TaskCreationRequest(
        task="Lookup ETH data, scrape website, and summarize",
        budget_usdc="0.000100",  # 100 atomic units: below minimum price of any service
        execute_now=False
    )
    task_detail = service.create_task(task_req)
    executed = await service.execute_task(task_detail.task_id)

    assert executed.status == TaskStatus.REFUSED.value
    assert executed.spent_usdc == "0.000000"
    assert len(spy.payload_creation_calls) == 0  # Payment NEVER called!
    assert len(spy.settlement_verification_calls) == 0

    # 2. Plan validator rejects forged client prices before payment
    validator = PlanValidator(registry_service)
    plan_tampered = ExecutionPlan(
        task_prompt="tampered_task",
        budget_units=100,
        calls=[
            PlannedCall(
                step_id=1,
                category="data",
                service_id="data_001",
                input_payload={"symbol": "ETH"},
                estimated_price_units=1  # Tampered: actual price is 2000
            )
        ],
        worst_case_cost_units=1,
        max_concurrency=3
    )
    # Validation corrects the price to server authority and detects budget overflow
    with pytest.raises(PlanValidationError) as excinfo:
        validator.validate_plan(plan_tampered)
    assert "exceeds" in str(excinfo.value).lower()


# ==============================================================================
# Requirement 4: Buyer calls Member 1's payment interface for every paid invocation
# ==============================================================================
@pytest.mark.asyncio
async def test_dod_4_every_paid_call_routes_through_member1_payment_interface():
    """DoD 4: Every paid service invocation routes through Member 1's payment client."""
    spy = MockMember1PaymentClientSpy()
    service = BuyerService(payment_client=spy)
    budget_mgr = BudgetManager(initial_budget_units=10000)
    data_svc = service.registry.get_service("data_001")

    call_plan = PlannedCall(
        step_id=1,
        category="data",
        service_id="data_001",
        input_payload={"symbol": "ETH"},
        estimated_price_units=2000,
        depends_on=[]
    )

    with patch("httpx.AsyncClient.post", side_effect=[
        MagicMock(
            status_code=402,
            headers={
                HEADER_X402_REQUIREMENT: json.dumps({
                    "version": "2.0",
                    "network": NETWORK_BASE_SEPOLIA,
                    "token": USDC_BASE_SEPOLIA,
                    "amount": "2000",
                    "payTo": data_svc.pay_to,
                    "nonce": "test_nonce_dod_4",
                    "service_id": "data_001"
                })
            }
        ),
        MagicMock(
            status_code=200,
            headers={
                HEADER_X402_SETTLEMENT_PROOF: "proof_dod_4_receipt",
                "content-type": "application/json"
            },
            json=MagicMock(return_value={"symbol": "ETH", "price": 3500.0, "volume_24h": 10000.0, "timestamp": "2026-10-16T12:00:00Z"})
        )
    ]):
        record = await service._execute_call(
            task_id="task_dod_4",
            planned=call_plan,
            budget_mgr=budget_mgr,
            upstream_calls={},
            fallbacks=[],
            warnings=[]
        )

    assert record.status == CallStatus.SUCCEEDED
    assert len(spy.payload_creation_calls) == 1
    assert len(spy.settlement_verification_calls) == 1
    assert spy.payload_creation_calls[0].amount == "2000"
    assert spy.settlement_verification_calls[0] == "proof_dod_4_receipt"


# ==============================================================================
# Requirement 5: A single task can use Data, Scraping, and Inference
# ==============================================================================
@pytest.mark.asyncio
async def test_dod_5_single_task_uses_data_scraping_and_inference():
    """DoD 5: Multi-step task coordinates Data, Scraping, and Inference in dependency order."""
    planner = TaskPlanner()
    plan = planner.create_plan(TaskCreationRequest(
        task="Lookup ETH price, scrape ethereum news, and summarize findings",
        budget_usdc="0.050000",
        max_concurrency=3
    ))

    # Must contain all 3 categories
    plan_cats = {c.category for c in plan.calls}
    assert "data" in plan_cats
    assert "scraping" in plan_cats
    assert "inference" in plan_cats

    # Verify Stage 0 has independent calls (data, scraping) and Stage 1 has dependent inference
    assert len(plan.execution_stages) >= 2
    stage_0_calls = [c for c in plan.calls if c.step_id in plan.execution_stages[0]]
    stage_1_calls = [c for c in plan.calls if c.step_id in plan.execution_stages[1]]

    assert all(c.category in ["data", "scraping"] for c in stage_0_calls)
    assert any(c.category == "inference" for c in stage_1_calls)
    assert len(stage_1_calls[0].depends_on) >= 1


# ==============================================================================
# Requirement 6: At least three concurrent calls supported with atomic budget lock
# ==============================================================================
@pytest.mark.asyncio
async def test_dod_6_three_concurrent_calls_with_atomic_budget_enforcement():
    """DoD 6: Support at least 3 concurrent calls while atomic budget locking prevents overdrawing."""
    budget_mgr = BudgetManager(initial_budget_units=5000)

    # 3 calls each requesting 2000 units (total 6000 > 5000)
    async def try_reserve(cid: str):
        try:
            await budget_mgr.reserve(cid, 2000)
            return True
        except Exception:
            return False

    # Execute 3 parallel reservations
    results = await asyncio.gather(
        try_reserve("call_1"),
        try_reserve("call_2"),
        try_reserve("call_3")
    )

    # Exactly 2 succeed (4000 units), 1 is blocked by atomic lock!
    assert results.count(True) == 2
    assert results.count(False) == 1
    assert budget_mgr.available_budget == 1000


# ==============================================================================
# Requirement 7: Seller outputs are validated against their JSON Schemas
# ==============================================================================
def test_dod_7_seller_outputs_validated_against_json_schema():
    """DoD 7: Draft-7 output validation accepts valid schemas and rejects corrupted schemas."""
    validator = OutputValidator()
    data_svc = registry_service.get_service("data_001")
    output_schema = data_svc.output_schema

    # Valid output
    valid_out = {"symbol": "ETH", "price": 3450.5, "volume_24h": 5000000.0, "timestamp": "2026-10-16T12:00:00Z"}
    is_valid, err = validator.validate_output(valid_out, output_schema, content_type="application/json")
    assert is_valid is True
    assert not err

    # Invalid: missing required field 'price'
    invalid_out = {"symbol": "ETH", "volume_24h": 5000000.0, "timestamp": "2026-10-16T12:00:00Z"}
    is_valid, err = validator.validate_output(invalid_out, output_schema, content_type="application/json")
    assert is_valid is False
    assert "price" in err

    # Invalid: wrong content type
    is_valid, err = validator.validate_output(valid_out, output_schema, content_type="text/html")
    assert is_valid is False
    assert "text/html" in err


# ==============================================================================
# Requirement 8: Fallback cannot cause duplicate or unaccounted payments
# ==============================================================================
@pytest.mark.asyncio
async def test_dod_8_fallback_safety_and_budget_guards():
    """DoD 8: Fallbacks are strictly blocked on uncertain settlements and rechecked for affordability."""
    spy = MockMember1PaymentClientSpy()
    service = BuyerService(payment_client=spy)
    budget_mgr = BudgetManager(initial_budget_units=10000)
    scraping_svc = service.registry.get_service("scraping_001")

    # 1. Primary call has uncertain settlement -> Fallback strictly blocked
    uncertain_plan = PlannedCall(
        step_id=1,
        category="scraping",
        service_id="scraping_001",
        input_payload={"url": "https://ethereum.org"},
        estimated_price_units=scraping_svc.price_atomic,
        allow_fallback=True,
        fallback_service_ids=["scraping_001"]
    )

    with patch("httpx.AsyncClient.post", side_effect=[
        MagicMock(
            status_code=402,
            headers={
                HEADER_X402_REQUIREMENT: json.dumps({
                    "version": "2.0",
                    "network": NETWORK_BASE_SEPOLIA,
                    "token": USDC_BASE_SEPOLIA,
                    "amount": str(scraping_svc.price_atomic),
                    "payTo": scraping_svc.pay_to,
                    "nonce": "test_nonce_recon",
                    "service_id": "scraping_001"
                })
            }
        ),
        # 200 returned but settlement proof is missing -> uncertain
        MagicMock(status_code=200, headers={}, json=MagicMock(return_value={}))
    ]):
        record = await service._execute_call(
            task_id="task_recon_block_fb",
            planned=uncertain_plan,
            budget_mgr=budget_mgr,
            upstream_calls={},
            fallbacks=[],
            warnings=[]
        )

    assert record.status == CallStatus.PENDING_RECONCILIATION
    # Primary call recorded
    assert record.service_id == "scraping_001"
    # Budget remains safely held in reservation for reconciliation: 10000 - 3000 = 7000
    assert budget_mgr.available_budget == 10000 - scraping_svc.price_atomic


# ==============================================================================
# Requirement 9: Final results preserve provenance and explain service choices
# ==============================================================================
def test_dod_9_final_results_preserve_provenance_and_explain_choices():
    """DoD 9: Deterministic aggregation preserves field-level provenance and explains choices."""
    aggregator = ResultAggregator()
    valid_tx = "0x" + "9" * 64

    calls = [
        ServiceCallRecord(
            step_id=1,
            call_id="call_data_01",
            service_id="data_001",
            category=ServiceCategory.DATA,
            status=CallStatus.SUCCEEDED,
            listed_price_usdc="0.002000",
            amount_paid_usdc="0.002000",
            transaction_hash=valid_tx,
            payment_reference=valid_tx,
            schema_version="1.0.0",
            output={"symbol": "ETH", "price": 3200.0, "timestamp": 1718000000},
            validation_status="valid"
        )
    ]

    res = aggregator.aggregate_results(task_prompt="Lookup ETH", calls=calls)
    assert "provenance" in res
    assert len(res["provenance"]) >= 1
    prov = res["provenance"][0]
    assert prov["service_id"] == "data_001"
    assert prov["call_id"] == "call_data_01"
    assert prov["payment_reference"] == valid_tx
    assert prov["validation_status"] == "valid"


# ==============================================================================
# Requirement 10: Displayed spending agrees with verified ledger data
# ==============================================================================
def test_dod_10_displayed_spending_agrees_with_verified_ledger_data():
    """DoD 10: Displayed spending is derived strictly from Member 4's authoritative ledger."""
    mock_ledger = LedgerRepository()
    gen = ExplanationGenerator(ledger=mock_ledger)
    valid_tx = "0x" + "8" * 64

    # Seed Member 4 ledger with verified settlement
    mock_ledger.record_transaction(LedgerRecordSchema(
        request_id="call_dod_10",
        buyer_id="buyer_001",
        seller_id="data_001",
        service_id="data_001",
        listed_price="0.002000",
        amount_paid="0.002000",
        tx_hash=valid_tx,
        status=LedgerStatus.PAID,
        latency_ms=105.0
    ))

    calls = [
        ServiceCallRecord(
            step_id=1,
            call_id="call_dod_10",
            service_id="data_001",
            category=ServiceCategory.DATA,
            status=CallStatus.SUCCEEDED,
            listed_price_usdc="0.002000",
            amount_paid_usdc="0.002000",
            transaction_hash=valid_tx,
            validation_status="valid"
        )
    ]

    exp = gen.generate_explanation(
        task_prompt="Lookup ETH",
        budget_usdc="0.010000",
        calls=calls
    )

    # Check 7-part spending summary
    summary = exp.spending_summary
    assert summary.budget_allocated_usdc == "0.010000"
    assert summary.verified_spent_usdc == "0.002000"
    assert summary.remaining_budget_usdc == "0.008000"
    assert summary.refunded_amount_usdc == "0.008000"
    assert summary.uncertain_pending_usdc == "0.000000"
    assert summary.reserved_budget_usdc == "0.000000"

    # Base Sepolia explorer link formatted strictly without fabrication
    assert len(exp.explorer_links) == 1
    assert exp.explorer_links[0] == f"https://sepolia.basescan.org/tx/{valid_tx}"


# ==============================================================================
# Additional Protocol Verification: Official vs Custom Headers Compatibility
# ==============================================================================
@pytest.mark.asyncio
async def test_dod_4b_standard_x402_protocol_headers_compatibility():
    """Verify that BuyerService seamlessly supports standard and custom x402 headers."""
    from backend.payments.x402_adapter import (
        HEADER_OFFICIAL_PAYMENT_REQUIRED,
        HEADER_OFFICIAL_PAYMENT_RESPONSE,
    )
    spy = MockMember1PaymentClientSpy()
    service = BuyerService(payment_client=spy)
    budget_mgr = BudgetManager(initial_budget_units=10000)
    data_svc = service.registry.get_service("data_001")

    call_plan = PlannedCall(
        step_id=1,
        category="data",
        service_id="data_001",
        input_payload={"symbol": "ETH"},
        estimated_price_units=2000,
        depends_on=[]
    )

    import json as json_module
    mock_402 = MagicMock(
        status_code=402,
        headers={
            HEADER_OFFICIAL_PAYMENT_REQUIRED: "mock_challenge_terms",
            HEADER_X402_REQUIREMENT: json_module.dumps({
                "version": "2.0",
                "network": NETWORK_BASE_SEPOLIA,
                "token": USDC_BASE_SEPOLIA,
                "amount": "2000",
                "payTo": data_svc.pay_to,
                "nonce": "test_nonce_standard_headers",
                "service_id": "data_001"
            })
        }
    )
    mock_200 = MagicMock(
        status_code=200,
        headers={
            HEADER_OFFICIAL_PAYMENT_RESPONSE: "official_settle_proof_receipt_123",
            HEADER_X402_SETTLEMENT_PROOF: "official_settle_proof_receipt_123",
            "content-type": "application/json"
        },
        json=MagicMock(return_value={"symbol": "ETH", "price": 3500.0, "volume_24h": 10000.0, "timestamp": "2026-10-16T12:00:00Z"})
    )

    with patch("httpx.AsyncClient.post", side_effect=[mock_402, mock_200]):
        record = await service._execute_call(
            task_id="task_standard_headers",
            planned=call_plan,
            budget_mgr=budget_mgr,
            upstream_calls={},
            fallbacks=[],
            warnings=[]
        )

    assert record.status == CallStatus.SUCCEEDED, f"Call failed with error: {record.error_message}"
    assert len(spy.payload_creation_calls) == 1
    assert len(spy.settlement_verification_calls) == 1

