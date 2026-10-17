"""Focused test suite for DI-06 Phase 1: Agent Communication, JSON Contracts, and Execution Architecture."""
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from backend.main import app
from backend.buyer.output_validator import OutputValidator
from backend.buyer.plan_validator import (
    ExecutionPlan,
    PlannedCall,
    PlanValidationError,
    PlanValidator,
)
from backend.buyer.schemas import (
    AgentInvocationContract,
    AgentResultContract,
    CallStatus,
    ErrorDetail,
    PaymentAttemptReference,
    ProvenanceRecord,
    SchemaValidationResult,
    ServiceCallRecord,
    TaskCreationRequest,
    TaskStatus,
)
from backend.buyer.service import BuyerService
from backend.payments.budget import BudgetManager
from backend.shared.constants import (
    NETWORK_BASE_SEPOLIA,
    USDC_BASE_SEPOLIA,
    LedgerStatus,
    ServiceCategory,
)


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# 1. Valid and Invalid JSON Output Validation (Draft-7)
# ---------------------------------------------------------------------------

def test_valid_and_invalid_json_output_validation():
    """Verify Draft-7 schema validation accepts compliant output and rejects malformed/type-mismatched data."""
    validator = OutputValidator()
    schema = {
        "type": "object",
        "required": ["symbol", "price", "timestamp"],
        "properties": {
            "symbol": {"type": "string"},
            "price": {"type": "number"},
            "timestamp": {"type": "string"},
        },
        "additionalProperties": False,
    }

    # Compliant payload
    valid_payload = {"symbol": "ETH", "price": 3500.50, "timestamp": "2026-10-17T12:00:00Z"}
    is_valid, err = validator.validate_output(valid_payload, schema, content_type="application/json")
    assert is_valid is True
    assert err == ""

    # Missing required field
    missing_field = {"symbol": "ETH", "price": 3500.50}
    is_valid, err = validator.validate_output(missing_field, schema, content_type="application/json")
    assert is_valid is False
    assert "Missing required field" in err

    # Type mismatch (price is string instead of number)
    type_mismatch = {"symbol": "ETH", "price": "three-thousand", "timestamp": "2026-10-17T12:00:00Z"}
    is_valid, err = validator.validate_output(type_mismatch, schema, content_type="application/json")
    assert is_valid is False
    assert "Type mismatch" in err

    # Unexpected additional property
    extra_field = {"symbol": "ETH", "price": 3500.50, "timestamp": "2026-10-17T12:00:00Z", "extra": "unauthorized"}
    is_valid, err = validator.validate_output(extra_field, schema, content_type="application/json")
    assert is_valid is False
    assert "Unexpected additional field" in err

    # Malformed non-JSON string
    is_valid, err = validator.validate_output("{not valid json: ", schema, content_type="application/json")
    assert is_valid is False
    assert "Malformed JSON" in err

    # Content-type rejection
    is_valid, err = validator.validate_output(valid_payload, schema, content_type="text/html")
    assert is_valid is False
    assert "Invalid Content-Type" in err


# ---------------------------------------------------------------------------
# 2. Dependency Ordering and DAG Cycle Detection
# ---------------------------------------------------------------------------

def test_dag_cycle_detection():
    """Verify that circular dependencies in execution plan are detected and rejected."""
    plan_validator = PlanValidator()
    cyclic_calls = [
        PlannedCall(
            step_id=1,
            category="data",
            service_id="data_001",
            capability="data.lookup.v1",
            estimated_price_units=2000,
            depends_on=[2],
            input_payload={"symbol": "ETH"},
        ),
        PlannedCall(
            step_id=2,
            category="inference",
            service_id="inference_001",
            capability="inference.summarize.v1",
            estimated_price_units=4000,
            depends_on=[1],
            input_payload={"prompt": "Analyze"},
        ),
    ]
    plan = ExecutionPlan(
        task_prompt="Cycle test",
        budget_units=50000,
        calls=cyclic_calls,
        worst_case_cost_units=6000,
        max_concurrency=3,
    )

    with pytest.raises(PlanValidationError, match="Cycle detected"):
        plan_validator.validate_plan(plan)


def test_dag_dependency_topological_stages():
    """Verify independent steps share Stage 0 and dependent steps execute in Stage 1."""
    plan_validator = PlanValidator()
    calls = [
        PlannedCall(
            step_id=1,
            category="data",
            service_id="data_001",
            capability="data.lookup.v1",
            estimated_price_units=2000,
            depends_on=[],
            input_payload={"symbol": "ETH"},
        ),
        PlannedCall(
            step_id=2,
            category="scraping",
            service_id="scraping_001",
            capability="scraping.extract.v1",
            estimated_price_units=3000,
            depends_on=[],
            input_payload={"url": "https://ethereum.org"},
        ),
        PlannedCall(
            step_id=3,
            category="inference",
            service_id="inference_001",
            capability="inference.summarize.v1",
            estimated_price_units=4000,
            depends_on=[1, 2],
            input_payload={"prompt": "Synthesize"},
        ),
    ]
    plan = ExecutionPlan(
        task_prompt="DAG stages test",
        budget_units=50000,
        calls=calls,
        worst_case_cost_units=9000,
        max_concurrency=3,
    )
    plan_validator.validate_plan(plan)
    assert len(plan.execution_stages) == 2
    assert set(plan.execution_stages[0]) == {1, 2}
    assert plan.execution_stages[1] == [3]


# ---------------------------------------------------------------------------
# 3. Asynchronous Task Status Lifecycle & Execution APIs
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_asynchronous_task_status_lifecycle(client):
    """Verify task submission with execute_now=False creates accepted record, and execute endpoint triggers execution."""
    # 1. Create task with execute_now=False
    create_res = client.post(
        "/api/v1/tasks",
        json={
            "task": "Lookup ETH price and summarize analysis",
            "budget_usdc": "0.050000",
            "max_concurrency": 3,
            "execute_now": False,
        },
    )
    assert create_res.status_code == status.HTTP_201_CREATED
    data = create_res.json()
    task_id = data["task_id"]
    assert data["status"] == "accepted"
    assert data["spent_usdc"] == "0.000000"
    assert len(data["calls"]) == 0

    # 2. Check task status endpoint returns accepted
    status_res = client.get(f"/api/v1/tasks/{task_id}")
    assert status_res.status_code == status.HTTP_200_OK
    assert status_res.json()["status"] == "accepted"

    # 3. Trigger execution via POST /api/v1/tasks/{task_id}/execute
    exec_res = client.post(f"/api/v1/tasks/{task_id}/execute")
    assert exec_res.status_code == status.HTTP_200_OK
    exec_data = exec_res.json()
    assert exec_data["status"] in ["completed", "completed_with_warnings", "pending_reconciliation"]
    assert len(exec_data["calls"]) >= 1

    # 4. Attempting to execute an already executed task returns 400 INVALID_STATE
    re_exec_res = client.post(f"/api/v1/tasks/{task_id}/execute")
    assert re_exec_res.status_code == status.HTTP_400_BAD_REQUEST
    assert re_exec_res.json()["error"]["code"] == "INVALID_STATE"


@pytest.mark.asyncio
async def test_background_task_creation(client):
    """Verify background=True returns 202 Accepted immediately with active task id."""
    res = client.post(
        "/api/v1/tasks",
        json={
            "task": "Fetch Ethereum spot price",
            "budget_usdc": "0.020000",
            "max_concurrency": 3,
            "execute_now": True,
            "background": True,
        },
    )
    assert res.status_code == status.HTTP_202_ACCEPTED
    task_id = res.json()["task_id"]
    assert res.json()["status"] in ["accepted", "planning", "running", "completed", "pending_reconciliation"]

    # Poll status endpoint
    poll = client.get(f"/api/v1/tasks/{task_id}")
    assert poll.status_code == status.HTTP_200_OK
    assert poll.json()["task_id"] == task_id


# ---------------------------------------------------------------------------
# 4. Provenance and Timestamp Tracking
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_provenance_propagation_and_timestamps(client):
    """Verify task result contains structured provenance with timestamps and source metadata."""
    res = client.post(
        "/api/v1/tasks",
        json={
            "task": "Lookup Ethereum price",
            "budget_usdc": "0.020000",
            "execute_now": True,
        },
    )
    assert res.status_code == status.HTTP_201_CREATED
    task_id = res.json()["task_id"]

    result_res = client.get(f"/api/v1/tasks/{task_id}/result")
    assert result_res.status_code == status.HTTP_200_OK
    result_data = result_res.json()
    assert "provenance" in result_data
    assert len(result_data["provenance"]) >= 1

    prov = result_data["provenance"][0]
    assert "call_id" in prov
    assert "service_id" in prov
    assert "category" in prov
    assert "status" in prov
    assert "timestamp" in prov
    assert "source_metadata" in prov
    assert "endpoint_url" in prov["source_metadata"]
    assert "network" in prov["source_metadata"]


# ---------------------------------------------------------------------------
# 5. Invalid Output Rejection Prevents Downstream Execution
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_invalid_output_rejection_prevents_downstream():
    """Verify that when an upstream step produces schema-invalid output, dependent steps are not executed or charged."""
    service = BuyerService()

    # Create dummy calls where step 1 was rejected
    step1_call = ServiceCallRecord(
        call_id="call_step1_data",
        service_id="data_001",
        category=ServiceCategory.DATA,
        step_id=1,
        status=CallStatus.PAID_OUTPUT_REJECTED,
        listed_price_usdc="0.002000",
        amount_paid_usdc="0.002000",
        output={"corrupted": True},
        error="Missing required field 'symbol'",
        validation_status="rejected",
    )

    upstream = {1: step1_call}
    planned_step2 = PlannedCall(
        step_id=2,
        category="inference",
        service_id="inference_001",
        capability="inference.summarize.v1",
        estimated_price_units=4000,
        depends_on=[1],
        input_payload={"prompt": "Summarize data"},
    )

    b_mgr = BudgetManager(initial_budget_units=10000)

    record = await service._execute_call(
        task_id="test_dag_rejection",
        planned=planned_step2,
        budget_mgr=b_mgr,
        upstream_calls=upstream,
        fallbacks=[],
        warnings=[],
    )

    assert record.status == CallStatus.FAILED_AND_NOT_CHARGED
    assert record.amount_paid_usdc == "0.000000"
    assert "Upstream dependency failed or unfulfilled" in record.error
    assert b_mgr.available_budget == 10000


# ---------------------------------------------------------------------------
# 6. Standardized JSON Contracts Data Models
# ---------------------------------------------------------------------------

def test_standardized_json_contracts_instantiation():
    """Verify instantiate and round-trip of Phase 1 JSON contracts."""
    val_result = SchemaValidationResult(
        is_valid=True,
        schema_version="1.0.0",
        error_message=None,
    )
    assert val_result.is_valid is True
    assert val_result.validation_engine == "Draft7Validator"

    prov = ProvenanceRecord(
        call_id="call_test_01",
        service_id="data_001",
        category="data",
        step_id=1,
        source_url="http://localhost:8000/api/v1/sellers/data",
        data_freshness_seconds=0.12,
    )
    assert prov.call_id == "call_test_01"
    assert prov.data_freshness_seconds == 0.12

    pmt_ref = PaymentAttemptReference(
        call_id="call_test_01",
        service_id="data_001",
        amount_atomic=2000,
        amount_usdc="0.002000",
        nonce="nonce_abc",
        transaction_hash="0xabcdef123456",
        status="confirmed",
    )
    assert pmt_ref.amount_atomic == 2000

    err_detail = ErrorDetail(
        code="SCHEMA_VALIDATION_FAILED",
        message="Missing required property: symbol",
        details={"missing": ["symbol"]},
        retryable=False,
    )
    assert err_detail.code == "SCHEMA_VALIDATION_FAILED"

    invoc = AgentInvocationContract(
        invocation_id="invoc_01",
        task_id="task_01",
        step_id=1,
        service_id="data_001",
        category="data",
        payload={"symbol": "ETH"},
        budget_limit_atomic=5000,
    )
    assert invoc.budget_limit_atomic == 5000

    res_contract = AgentResultContract(
        invocation_id="invoc_01",
        task_id="task_01",
        step_id=1,
        service_id="data_001",
        category="data",
        status="succeeded",
        output={"symbol": "ETH", "price": 3500.5},
        validation=val_result,
        provenance=prov,
        payment_reference=pmt_ref,
    )
    assert res_contract.status == "succeeded"
    assert res_contract.validation.is_valid is True
