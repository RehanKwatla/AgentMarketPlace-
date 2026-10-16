"""Tests for Seller-Output Validation, Safe Fallback Handling, Result Aggregation, and Provenance Tracking.

Requirements:
1. Validate every seller response against exact output JSON Schema.
2. Reject malformed JSON, schema mismatches, missing required fields, invalid content types, and unexpected response structures.
3. Preserve service ID, call ID, schema version, timestamps, payment reference, and source metadata.
4. Aggregate only validated outputs into final task result.
5. Explain rejected outputs without presenting them as successful findings.
6. Permit fallback only when plan allows, budget supports, and earlier payment was safe.
7. If settlement is uncertain, mark call for reconciliation rather than retrying.
8. If payment settled but output was invalid, preserve paid_output_rejected and retain settlement evidence.
9. Deterministic aggregation with field-level and result-level provenance.
10. Demonstrate a result containing accepted outputs, a rejected output, and a provenance record.
"""
import asyncio
import json
import pytest
from unittest.mock import MagicMock, patch

from backend.shared.constants import (
    NETWORK_BASE_SEPOLIA,
    USDC_BASE_SEPOLIA,
    HEADER_X402_REQUIREMENT,
    HEADER_X402_PAYMENT_PAYLOAD,
    HEADER_X402_SETTLEMENT_PROOF,
    LedgerStatus,
    ServiceCategory,
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
from backend.buyer.output_validator import OutputValidator
from backend.buyer.aggregator import ResultAggregator
from backend.buyer.plan_validator import PlannedCall, ExecutionPlan
from backend.buyer.service import BuyerService

settings = get_settings()


class MockMember1PaymentClient(BuyerPaymentClientInterface):
    """Mock Member 1 payment client for validation & provenance testing."""

    def __init__(self, ambiguous_settlement: bool = False):
        self.ambiguous_settlement = ambiguous_settlement

    async def create_payment_payload(
        self,
        requirement: PaymentRequirement,
        idempotency_key: str
    ) -> PaymentPayload:
        return PaymentPayload(
            authorization={
                "network": requirement.network,
                "token": requirement.token,
                "amount": requirement.amount,
                "payTo": requirement.payTo,
                "nonce": requirement.nonce,
                "idempotency_key": idempotency_key
            },
            signature="0xmock_sig_val_test",
            buyer_address="0x1000000000000000000000000000000000000001"
        )

    async def verify_settlement(
        self,
        receipt_header: str | None
    ) -> SettlementReceipt:
        if self.ambiguous_settlement or not receipt_header:
            return SettlementReceipt(tx_hash=None, facilitator_receipt_id=None, settled_amount_units=0)
        return SettlementReceipt(
            tx_hash=receipt_header if str(receipt_header).startswith("0x") else None,
            facilitator_receipt_id=receipt_header if not str(receipt_header).startswith("0x") else None,
            settled_amount_units=2000
        )


def test_output_validator_rejects_malformed_json_and_invalid_content_type():
    """Verify OutputValidator rejects non-JSON content types and malformed JSON bodies."""
    validator = OutputValidator()
    schema = {
        "type": "object",
        "required": ["symbol", "price"],
        "properties": {
            "symbol": {"type": "string"},
            "price": {"type": "number"}
        }
    }

    # 1. Invalid Content-Type
    is_valid, err = validator.validate_output(
        output_payload={"symbol": "ETH", "price": 2650.0},
        output_schema=schema,
        content_type="text/html; charset=utf-8"
    )
    assert not is_valid
    assert "Invalid Content-Type" in err

    # 2. Malformed JSON string
    is_valid, err = validator.validate_output(
        output_payload="<not a json>hello",
        output_schema=schema,
        content_type="application/json"
    )
    assert not is_valid
    assert "Malformed JSON" in err

    # 3. Non-dictionary response structure (e.g. list instead of object)
    is_valid, err = validator.validate_output(
        output_payload=["ETH", 2650.0],
        output_schema=schema,
        content_type="application/json"
    )
    assert not is_valid
    assert "Unexpected response structure" in err

    # 4. Missing required field
    is_valid, err = validator.validate_output(
        output_payload={"symbol": "ETH"},  # Missing price
        output_schema=schema,
        content_type="application/json"
    )
    assert not is_valid
    assert "Missing required field" in err

    # 5. Type mismatch
    is_valid, err = validator.validate_output(
        output_payload={"symbol": "ETH", "price": "two thousand"},  # String instead of number
        output_schema=schema,
        content_type="application/json"
    )
    assert not is_valid
    assert "Type mismatch" in err

    # 6. Valid output passes
    is_valid, err = validator.validate_output(
        output_payload={"symbol": "ETH", "price": 2650.0},
        output_schema=schema,
        content_type="application/json"
    )
    assert is_valid
    assert err == ""


@pytest.mark.asyncio
async def test_rejected_output_after_verified_payment_preserves_cost_and_evidence():
    """Verify that if a payment settles but output is invalid:

    - Status is PAID_OUTPUT_REJECTED
    - Settlement evidence and amount paid are NOT erased
    - Member 4's ledger records status 'paid output rejected'
    - Output is NOT included in market_data
    """
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

    # Mock seller returning 402, then on payment returning 200 with settlement proof but missing 'price'
    with patch("httpx.AsyncClient.post", side_effect=[
        MagicMock(
            status_code=402,
            headers={
                HEADER_X402_REQUIREMENT: json.dumps({
                    "version": "2.0",
                    "network": NETWORK_BASE_SEPOLIA,
                    "token": USDC_BASE_SEPOLIA,
                    "amount": "2000",
                    "payTo": settings.data_seller_pay_to,
                    "nonce": "test_nonce_schema_fail",
                    "service_id": "data_001"
                })
            }
        ),
        MagicMock(
            status_code=200,
            headers={
                HEADER_X402_SETTLEMENT_PROOF: "receipt_paid_but_bad_schema_001",
                "content-type": "application/json"
            },
            json=MagicMock(return_value={"symbol": "ETH", "corrupted": "missing price"})
        )
    ]):
        record = await service._execute_call(
            task_id="task_paid_bad_schema",
            planned=call_plan,
            budget_mgr=budget_mgr,
            upstream_calls={},
            fallbacks=[],
            warnings=[]
        )

        # 1. Correct agreed status
        assert record.status == CallStatus.PAID_OUTPUT_REJECTED
        assert record.validation_status == "rejected"

        # 2. Amount paid is NOT erased (money was spent!)
        reg_svc = service.registry.get_service("data_001")
        assert record.amount_paid_usdc == reg_svc.price_usdc
        assert sum(budget_mgr._spent_units.values()) == 2000
        assert budget_mgr.available_budget == 8000

        # 3. Settlement reference preserved
        assert record.transaction_hash == "receipt_paid_but_bad_schema_001"
        assert record.payment_reference == "receipt_paid_but_bad_schema_001"

        # 4. Check Member 4's ledger
        ledger_entry = ledger_repo.get_record(record.call_id)
        assert ledger_entry is not None
        assert ledger_entry.status == LedgerStatus.PAID_OUTPUT_REJECTED
        assert ledger_entry.amount_paid == reg_svc.price_usdc
        assert ledger_entry.tx_hash == "receipt_paid_but_bad_schema_001"


@pytest.mark.asyncio
async def test_blocked_fallback_when_settlement_uncertain():
    """Verify fallback is strictly BLOCKED if primary call payment is uncertain."""
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
        MagicMock(
            status_code=402,
            headers={
                HEADER_X402_REQUIREMENT: json.dumps({
                    "version": "2.0",
                    "network": NETWORK_BASE_SEPOLIA,
                    "token": USDC_BASE_SEPOLIA,
                    "amount": "2000",
                    "payTo": settings.data_seller_pay_to,
                    "nonce": "test_nonce_ambig_block",
                    "service_id": "data_001"
                })
            }
        ),
        # HTTP 200 but missing proof header -> ambiguous settlement
        MagicMock(status_code=200, headers={}, json=MagicMock(return_value={"symbol": "ETH", "price": 2650.0}))
    ]):
        fallbacks_log = []
        rec = await service._execute_call(
            task_id="task_ambig_block",
            planned=call_plan,
            budget_mgr=budget_mgr,
            upstream_calls={},
            fallbacks=fallbacks_log,
            warnings=[]
        )

        assert rec.status == CallStatus.PENDING_RECONCILIATION
        # Fallback was NOT permitted
        assert len(fallbacks_log) == 0
        # Budget is held
        assert budget_mgr.available_budget == 8000


def test_result_aggregator_provenance_and_zero_fact_fabrication():
    """Verify aggregator preserves field-level provenance and does not invent facts for missing outputs."""
    aggregator = ResultAggregator()

    accepted_data = ServiceCallRecord(
        call_id="call_data_001",
        service_id="data_001",
        category=ServiceCategory.DATA,
        step_id=1,
        status=CallStatus.SUCCEEDED,
        listed_price_usdc="0.002000",
        amount_paid_usdc="0.002000",
        transaction_hash="0xreceipt_data",
        payment_reference="0xreceipt_data",
        schema_version="1.0.0",
        output={"symbol": "ETH", "price": 2650.0, "volume_24h": 100000.0, "timestamp": "2026-10-16T00:00:00Z"},
        validation_status="accepted"
    )

    accepted_scraping = ServiceCallRecord(
        call_id="call_scraping_001",
        service_id="scraping_001",
        category=ServiceCategory.SCRAPING,
        step_id=2,
        status=CallStatus.SUCCEEDED,
        listed_price_usdc="0.003000",
        amount_paid_usdc="0.003000",
        transaction_hash="0xreceipt_scraping",
        payment_reference="0xreceipt_scraping",
        schema_version="1.0.0",
        output={"url": "https://ethereum.org", "title": "Ethereum PoS", "content": "Proof of Stake consensus", "word_count": 4},
        validation_status="accepted"
    )

    rejected_inference = ServiceCallRecord(
        call_id="call_inference_001",
        service_id="inference_001",
        category=ServiceCategory.INFERENCE,
        step_id=3,
        status=CallStatus.PAID_OUTPUT_REJECTED,
        listed_price_usdc="0.004000",
        amount_paid_usdc="0.004000",
        transaction_hash="0xreceipt_inference",
        payment_reference="0xreceipt_inference",
        schema_version="1.0.0",
        output={"invalid_key": "bad response"},
        error="Schema validation failed: Missing required field(s): 'response' is a required property",
        validation_status="rejected"
    )

    result = aggregator.aggregate_results(
        task_prompt="Fetch ETH and scrape ethereum.org",
        calls=[accepted_data, accepted_scraping, rejected_inference]
    )

    # 1. Market data contains ETH
    assert "ETH" in result["market_data"]
    assert result["market_data"]["ETH"]["price"] == 2650.0

    # 2. Web sources contains ethereum.org
    assert len(result["web_sources"]) == 1
    assert result["web_sources"][0]["url"] == "https://ethereum.org"

    # 3. Rejected inference is quarantined in rejected_outputs
    assert len(result["rejected_outputs"]) == 1
    rej = result["rejected_outputs"][0]
    assert rej["service_id"] == "inference_001"
    assert rej["status"] == "paid output rejected"
    assert "Missing required field" in rej["rejection_reason"]
    assert rej["payment_reference"] == "0xreceipt_inference"

    # 4. Summary explicitly discloses rejected output without hallucinating an AI response!
    assert "bad response" not in result["summary"]
    assert "Output Warnings" in result["summary"]
    assert "inference_001" in result["summary"]

    # 5. Provenance records field-level links
    prov = result["provenance"]
    assert len(prov) == 2  # 2 accepted outputs
    prov_targets = {p["target_field"]: p for p in prov}
    assert "market_data.ETH" in prov_targets
    assert prov_targets["market_data.ETH"]["service_id"] == "data_001"
    assert prov_targets["market_data.ETH"]["payment_reference"] == "0xreceipt_data"

    assert "web_sources[0]" in prov_targets
    assert prov_targets["web_sources[0]"]["service_id"] == "scraping_001"
    assert prov_targets["web_sources[0]"]["payment_reference"] == "0xreceipt_scraping"


@pytest.mark.asyncio
async def test_end_to_end_demonstration_accepted_outputs_rejected_output_and_provenance():
    """Demonstrate a full task result containing accepted outputs, a paid-but-rejected output,

    and complete field-level provenance tracking.
    """
    mock_payment = MockMember1PaymentClient()
    service = BuyerService(payment_client=mock_payment)

    request = TaskCreationRequest(
        task="Scrape ethereum site, lookup ETH market metrics, and summarize with AI",
        budget_usdc="0.050000",
        max_concurrency=3,
        execute_now=False
    )
    task_record = service.create_task(request)

    # Simulate: Step 1 (Scraping) succeeds, Step 2 (Data) settles but returns invalid schema, Step 3 (Inference) succeeds
    async def mock_execute(task_id, planned, budget_mgr, upstream_calls, fallbacks, warnings):
        if planned.category == ServiceCategory.SCRAPING.value:
            # Succeeded
            await budget_mgr.reserve(f"res_{planned.step_id}", 3000)
            await budget_mgr.commit(f"res_{planned.step_id}", 3000)
            rec = ServiceCallRecord(
                call_id=f"call_{planned.step_id}_scraping",
                service_id="scraping_001",
                category=ServiceCategory.SCRAPING,
                step_id=planned.step_id,
                status=CallStatus.SUCCEEDED,
                listed_price_usdc="0.003000",
                amount_paid_usdc="0.003000",
                transaction_hash="0xreceipt_demo_scraping",
                payment_reference="0xreceipt_demo_scraping",
                schema_version="1.0.0",
                output={"url": "https://ethereum.org", "title": "Ethereum Home", "content": "Ethereum is programmable money", "word_count": 4},
                validation_status="accepted"
            )
            service.repository.record_call_to_ledger(
                task_id=task_id,
                request_id=f"call_{planned.step_id}_scraping",
                service_id="scraping_001",
                listed_price="0.003000",
                amount_paid="0.003000",
                status="paid",
                tx_hash="0xreceipt_demo_scraping"
            )
            return rec
        elif planned.category == ServiceCategory.DATA.value:
            # Paid but output rejected due to missing 'volume_24h'
            await budget_mgr.reserve(f"res_{planned.step_id}", 2000)
            await budget_mgr.commit(f"res_{planned.step_id}", 2000)
            rec = ServiceCallRecord(
                call_id=f"call_{planned.step_id}_data",
                service_id="data_001",
                category=ServiceCategory.DATA,
                step_id=planned.step_id,
                status=CallStatus.PAID_OUTPUT_REJECTED,
                listed_price_usdc="0.002000",
                amount_paid_usdc="0.002000",
                transaction_hash="0xreceipt_demo_data",
                payment_reference="0xreceipt_demo_data",
                schema_version="1.0.0",
                output={"symbol": "ETH", "price": 2650.0},  # missing volume_24h and timestamp
                error="Schema validation failed: Missing required field(s): 'volume_24h' is a required property",
                validation_status="rejected"
            )
            service.repository.record_call_to_ledger(
                task_id=task_id,
                request_id=f"call_{planned.step_id}_data",
                service_id="data_001",
                listed_price="0.002000",
                amount_paid="0.002000",
                status="paid output rejected",
                tx_hash="0xreceipt_demo_data"
            )
            return rec
        else:
            # Inference succeeds
            await budget_mgr.reserve(f"res_{planned.step_id}", 4000)
            await budget_mgr.commit(f"res_{planned.step_id}", 4000)
            rec = ServiceCallRecord(
                call_id=f"call_{planned.step_id}_inference",
                service_id="inference_001",
                category=ServiceCategory.INFERENCE,
                step_id=planned.step_id,
                status=CallStatus.SUCCEEDED,
                listed_price_usdc="0.004000",
                amount_paid_usdc="0.004000",
                transaction_hash="0xreceipt_demo_inference",
                payment_reference="0xreceipt_demo_inference",
                schema_version="1.0.0",
                output={"response": "Executive Summary: Validated findings from Ethereum scraping indicate stable network activity.", "model_used": "reasoner-v1", "tokens_generated": 14},
                validation_status="accepted"
            )
            service.repository.record_call_to_ledger(
                task_id=task_id,
                request_id=f"call_{planned.step_id}_inference",
                service_id="inference_001",
                listed_price="0.004000",
                amount_paid="0.004000",
                status="paid",
                tx_hash="0xreceipt_demo_inference"
            )
            return rec

    with patch.object(service, "_execute_call", side_effect=mock_execute):
        task_response = await service.execute_task(task_record.task_id)

    # 1. Overall task completed with warnings due to rejected output
    assert task_response.status == TaskStatus.COMPLETED_WITH_WARNINGS.value

    # 2. Total spent includes all committed payments (3000 + 2000 + 4000 = 9000 units = 0.009 USDC)
    assert task_response.spent_usdc == "0.009000"
    assert task_response.remaining_usdc == "0.041000"

    res = task_response.result
    # 3. Accepted web sources has scraping output
    assert len(res["web_sources"]) == 1
    assert res["web_sources"][0]["url"] == "https://ethereum.org"

    # 4. Rejected output contains the corrupted data seller call
    assert len(res["rejected_outputs"]) == 1
    assert res["rejected_outputs"][0]["service_id"] == "data_001"
    assert res["rejected_outputs"][0]["status"] == "paid output rejected"
    assert res["rejected_outputs"][0]["payment_reference"] == "0xreceipt_demo_data"

    # 5. Provenance records exact links
    prov = res["provenance"]
    assert any(p["service_id"] == "scraping_001" and p["target_field"] == "web_sources[0]" for p in prov)
    assert any(p["service_id"] == "inference_001" and p["target_field"] == "summary" for p in prov)

    # 6. Explanation contains itemized outputs_accepted and outputs_rejected
    exp = task_response.explanation
    assert len(exp.outputs_accepted) >= 2
    assert len(exp.outputs_rejected) == 1
    assert "data_001" in exp.outputs_rejected[0]
