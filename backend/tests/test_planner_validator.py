"""Unit and Integration Tests for Buyer Planner, Service Selector, and Plan Validator."""
import pytest
from unittest.mock import patch, MagicMock
from backend.shared.constants import (
    NETWORK_BASE_SEPOLIA,
    USDC_BASE_SEPOLIA,
    ServiceCategory,
)
from backend.registry.schemas import ServiceRecord
from backend.registry.service import RegistryService
from backend.buyer.schemas import TaskCreationRequest
from backend.buyer.selector import ServiceSelector
from backend.buyer.plan_validator import (
    ExecutionPlan,
    PlannedCall,
    PlanValidator,
    PlanValidationError,
)
from backend.buyer.planner import TaskPlanner
from backend.buyer.service import BuyerService


def test_planner_creates_valid_dag_with_explicit_dependencies():
    """Test deterministic DAG generation with parallel Scraping/Data and dependent Inference."""
    planner = TaskPlanner()
    request = TaskCreationRequest(
        task="Scrape ethereum article, fetch crypto market data, and summarize key insights",
        budget_usdc="0.100000",
        max_concurrency=3
    )

    plan = planner.create_plan(request)
    assert plan is not None
    assert len(plan.calls) == 3

    # Check step IDs and categories
    step_map = {c.step_id: c for c in plan.calls}
    scraping_call = next(c for c in plan.calls if c.category == ServiceCategory.SCRAPING.value)
    data_call = next(c for c in plan.calls if c.category == ServiceCategory.DATA.value)
    inference_call = next(c for c in plan.calls if c.category == ServiceCategory.INFERENCE.value)

    # Scraping and Data have no dependencies (run in parallel in Stage 0)
    assert scraping_call.depends_on == []
    assert data_call.depends_on == []

    # Inference depends on both Scraping and Data (Stage 1)
    assert scraping_call.step_id in inference_call.depends_on
    assert data_call.step_id in inference_call.depends_on

    # Check execution stages
    assert len(plan.execution_stages) == 2
    assert sorted(plan.execution_stages[0]) == sorted([scraping_call.step_id, data_call.step_id])
    assert plan.execution_stages[1] == [inference_call.step_id]

    # Costs and reasons
    assert plan.expected_cost_units > 0
    assert plan.worst_case_cost_units >= plan.expected_cost_units
    assert plan.worst_case_cost_units <= plan.budget_units
    assert len(plan.reasons_for_selection) == 3

    # Verify serialization
    plan_dict = plan.to_dict()
    assert "dependency_graph" in plan_dict
    assert "execution_stages" in plan_dict
    assert "worst_case_cost_units" in plan_dict


def test_selector_hard_eligibility_checks_before_ranking():
    """Test that hard eligibility gates filter invalid services before ranking."""
    selector = ServiceSelector()

    # Base valid service
    valid_service = ServiceRecord(
        service_id="test_001",
        name="Test Service",
        category="data",
        endpoint_url="https://api.example.com/test",
        price_usdc="0.002000",
        price_atomic=2000,
        network=NETWORK_BASE_SEPOLIA,
        pay_to_address="0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        token=USDC_BASE_SEPOLIA,
        enabled=True,
        is_active=True,
        input_schema={"type": "object", "properties": {"symbol": {"type": "string"}}},
        output_schema={"type": "object"}
    )

    # 1. Valid service passes
    ok, err = selector.check_eligibility(valid_service, max_budget_units=5000)
    assert ok is True
    assert err is None

    # 2. Disabled service rejected
    disabled = valid_service.model_copy(update={"enabled": False})
    ok, err = selector.check_eligibility(disabled)
    assert ok is False
    assert "disabled" in err.lower()

    # 3. Network mismatch rejected
    wrong_net = valid_service.model_copy(update={"network": "eip155:1"})
    ok, err = selector.check_eligibility(wrong_net)
    assert ok is False
    assert "network" in err.lower()

    # 4. Token mismatch rejected
    wrong_token = valid_service.model_copy(update={"token": "0x0000000000000000000000000000000000000000"})
    ok, err = selector.check_eligibility(wrong_token)
    assert ok is False
    assert "token" in err.lower()

    # 5. Invalid pay_to address rejected
    bad_pay_to = valid_service.model_copy(update={"pay_to_address": "invalid_address"})
    ok, err = selector.check_eligibility(bad_pay_to)
    assert ok is False
    assert "pay_to" in err.lower()

    # 6. Over-budget rejected
    ok, err = selector.check_eligibility(valid_service, max_budget_units=1000)
    assert ok is False
    assert "budget" in err.lower()

    # 7. High ranking never overrides failed safety check
    # Candidate with perfect reputation (100) but wrong network must be rejected
    unsafe_perfect_rep = valid_service.model_copy(update={"network": "eip155:1"})
    ok, _ = selector.check_eligibility(unsafe_perfect_rep)
    assert ok is False


def test_plan_validator_rejects_missing_dependency():
    """Test PlanValidator raises PlanValidationError if a step depends on an unknown step."""
    validator = PlanValidator()
    plan = ExecutionPlan(
        task_prompt="Test task",
        budget_units=50000,
        calls=[
            PlannedCall(
                step_id=1,
                category="data",
                service_id="data_001",
                input_payload={"symbol": "ETH"},
                estimated_price_units=2000,
                depends_on=[99]  # Unknown step!
            )
        ],
        worst_case_cost_units=2000,
        max_concurrency=3
    )

    with pytest.raises(PlanValidationError) as exc:
        validator.validate_plan(plan)
    assert "unknown step 99" in str(exc.value)


def test_plan_validator_rejects_self_dependency():
    """Test PlanValidator raises PlanValidationError if a step depends on itself."""
    validator = PlanValidator()
    plan = ExecutionPlan(
        task_prompt="Test task",
        budget_units=50000,
        calls=[
            PlannedCall(
                step_id=1,
                category="data",
                service_id="data_001",
                input_payload={"symbol": "ETH"},
                estimated_price_units=2000,
                depends_on=[1]  # Self-dependency!
            )
        ],
        worst_case_cost_units=2000,
        max_concurrency=3
    )

    with pytest.raises(PlanValidationError) as exc:
        validator.validate_plan(plan)
    assert "self-dependency" in str(exc.value)


def test_plan_validator_rejects_cycles():
    """Test PlanValidator detects indirect and direct cycles."""
    validator = PlanValidator()

    # Direct 2-step cycle: 1 depends on 2, 2 depends on 1
    plan = ExecutionPlan(
        task_prompt="Test task",
        budget_units=50000,
        calls=[
            PlannedCall(
                step_id=1,
                category="data",
                service_id="data_001",
                input_payload={"symbol": "ETH"},
                estimated_price_units=2000,
                depends_on=[2]
            ),
            PlannedCall(
                step_id=2,
                category="inference",
                service_id="inference_001",
                input_payload={"prompt": "test"},
                estimated_price_units=4000,
                depends_on=[1]
            )
        ],
        worst_case_cost_units=6000,
        max_concurrency=3
    )

    with pytest.raises(PlanValidationError) as exc:
        validator.validate_plan(plan)
    assert "cycle detected" in str(exc.value).lower()


def test_plan_validator_rejects_over_budget_plan():
    """Test PlanValidator rejects plans where worst-case or expected cost exceeds budget."""
    validator = PlanValidator()
    plan = ExecutionPlan(
        task_prompt="Test task",
        budget_units=1000,  # 1000 base units allocated
        calls=[
            PlannedCall(
                step_id=1,
                category="data",
                service_id="data_001",
                input_payload={"symbol": "ETH"},
                estimated_price_units=2000,  # Costs 2000 units
                depends_on=[]
            )
        ],
        worst_case_cost_units=2000,
        max_concurrency=3
    )

    with pytest.raises(PlanValidationError) as exc:
        validator.validate_plan(plan)
    assert "exceeds allocated budget" in str(exc.value)


def test_plan_validator_rejects_untrusted_service_id():
    """Test PlanValidator verifies service IDs against server-side registry records."""
    validator = PlanValidator()
    plan = ExecutionPlan(
        task_prompt="Test task",
        budget_units=50000,
        calls=[
            PlannedCall(
                step_id=1,
                category="data",
                service_id="untrusted_fake_seller",
                input_payload={"symbol": "ETH"},
                estimated_price_units=100,
                depends_on=[]
            )
        ],
        worst_case_cost_units=100,
        max_concurrency=3
    )

    with pytest.raises(PlanValidationError) as exc:
        validator.validate_plan(plan)
    assert "does not exist or is disabled" in str(exc.value)


def test_plan_validator_overrides_client_price_tampering():
    """Test that PlanValidator enforces server-side registry price if client provides forged lower price."""
    validator = PlanValidator()
    # data_001 actually costs 2000 units in server registry
    # Client forges plan claiming data_001 costs only 500 units, but budget is only 1500 units
    plan = ExecutionPlan(
        task_prompt="Test task",
        budget_units=1500,
        calls=[
            PlannedCall(
                step_id=1,
                category="data",
                service_id="data_001",
                input_payload={"symbol": "ETH"},
                estimated_price_units=500,  # Forged lower price
                depends_on=[]
            )
        ],
        worst_case_cost_units=500,
        max_concurrency=3
    )

    # When validated, authoritative price (2000) is enforced, causing budget overflow
    with pytest.raises(PlanValidationError) as exc:
        validator.validate_plan(plan)
    assert "exceeds allocated budget" in str(exc.value)


def test_plan_validator_rejects_invalid_input_payload_schema():
    """Test that PlanValidator validates input payloads against the candidate's input_schema."""
    validator = PlanValidator()
    # scraping_001 requires 'url' in input_schema
    plan = ExecutionPlan(
        task_prompt="Test task",
        budget_units=50000,
        calls=[
            PlannedCall(
                step_id=1,
                category="scraping",
                service_id="scraping_001",
                input_payload={"invalid_field": 123},  # Missing required 'url'
                estimated_price_units=3000,
                depends_on=[]
            )
        ],
        worst_case_cost_units=3000,
        max_concurrency=3
    )

    with pytest.raises(PlanValidationError) as exc:
        validator.validate_plan(plan)
    assert "input schema" in str(exc.value).lower()


def test_plan_validator_rejects_unsafe_concurrency():
    """Test that PlanValidator rejects plans where parallel stage steps exceed concurrency limits."""
    validator = PlanValidator()
    # 3 parallel calls in Stage 0 when max_concurrency is set to 2
    plan = ExecutionPlan(
        task_prompt="Test task",
        budget_units=50000,
        calls=[
            PlannedCall(step_id=1, category="data", service_id="data_001", input_payload={"symbol": "ETH"}, estimated_price_units=2000, depends_on=[]),
            PlannedCall(step_id=2, category="scraping", service_id="scraping_001", input_payload={"url": "https://eth.org"}, estimated_price_units=3000, depends_on=[]),
            PlannedCall(step_id=3, category="inference", service_id="inference_001", input_payload={"prompt": "hi"}, estimated_price_units=4000, depends_on=[]),
        ],
        worst_case_cost_units=9000,
        max_concurrency=2  # Limit is 2, but 3 steps are parallel!
    )

    with pytest.raises(PlanValidationError) as exc:
        validator.validate_plan(plan, concurrency_limit=3)
    assert "exceeding max concurrency" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_plan_validation_always_happens_before_payment():
    """Demonstrate that an invalid/over-budget plan fails and refuses task BEFORE any payment interface is called."""
    service = BuyerService()

    # Create task with tiny budget (500 units) where minimum service is 2000 units
    request = TaskCreationRequest(
        task="Collect crypto market data and summarize",
        max_budget_atomic=500,
        execute_now=False
    )
    task_detail = service.create_task(request)
    assert task_detail.status == "accepted"

    # Patch BudgetManager to prove no budget reservation is ever attempted
    with patch("backend.buyer.service.BudgetManager.reserve") as mock_reserve:
        result = await service.execute_task(task_detail.task_id)
        assert result.status == "refused"
        assert "budget" in (result.failure_reason or "").lower()

        # Zero payment reservation calls occurred!
        mock_reserve.assert_not_called()
