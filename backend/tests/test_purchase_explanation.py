"""Test suite verifying purchase explanation, authoritative ledger reconciliation,
spending summary, and provenance tracking according to Member 3 responsibilities.
"""
import pytest
from unittest.mock import MagicMock
from backend.shared.constants import (
    NETWORK_BASE_SEPOLIA,
    USDC_BASE_SEPOLIA,
    LedgerStatus,
    ServiceCategory,
)
from backend.shared.schemas import LedgerRecordSchema
from backend.ledger.models import LedgerRepository
from backend.registry.service import RegistryService
from backend.buyer.schemas import (
    CallStatus,
    ServiceCallRecord,
)
from backend.buyer.explanation import ExplanationGenerator


@pytest.fixture
def mock_ledger():
    return LedgerRepository()


@pytest.fixture
def mock_registry():
    return RegistryService()


@pytest.fixture
def explanation_gen(mock_registry, mock_ledger):
    return ExplanationGenerator(registry=mock_registry, ledger=mock_ledger)


def test_correct_ledger_totals(explanation_gen, mock_ledger):
    """1. Authoritative verified totals must be derived strictly from Member 4's ledger records."""
    call1_id = "call_ledger_test_01"
    call2_id = "call_ledger_test_02"
    valid_tx1 = "0x" + "a" * 64
    valid_tx2 = "0x" + "b" * 64

    # Seed Member 4's ledger
    mock_ledger.record_transaction(LedgerRecordSchema(
        request_id=call1_id,
        buyer_id="buyer_001",
        seller_id="data_001",
        service_id="data_001",
        listed_price="0.002000",
        amount_paid="0.002000",
        tx_hash=valid_tx1,
        status=LedgerStatus.PAID,
        latency_ms=120.0
    ))
    mock_ledger.record_transaction(LedgerRecordSchema(
        request_id=call2_id,
        buyer_id="buyer_001",
        seller_id="inference_001",
        service_id="inference_001",
        listed_price="0.005000",
        amount_paid="0.005000",
        tx_hash=valid_tx2,
        status=LedgerStatus.PAID,
        latency_ms=350.0
    ))

    calls = [
        ServiceCallRecord(
            step_id=1,
            call_id=call1_id,
            service_id="data_001",
            category=ServiceCategory.DATA,
            status=CallStatus.SUCCEEDED,
            listed_price_usdc="0.002000",
            amount_paid_usdc="0.002000",
            transaction_hash=valid_tx1,
            validation_status="valid"
        ),
        ServiceCallRecord(
            step_id=2,
            call_id=call2_id,
            service_id="inference_001",
            category=ServiceCategory.INFERENCE,
            status=CallStatus.SUCCEEDED,
            listed_price_usdc="0.005000",
            amount_paid_usdc="0.005000",
            transaction_hash=valid_tx2,
            validation_status="valid"
        )
    ]

    exp = explanation_gen.generate_explanation(
        task_prompt="Lookup ETH and analyze",
        budget_usdc="0.020000",
        calls=calls
    )

    # Verified spend is exactly 0.002 + 0.005 = 0.007000 USDC
    assert exp.spending_summary.budget_allocated_usdc == "0.020000"
    assert exp.spending_summary.verified_spent_usdc == "0.007000"
    assert exp.spending_summary.remaining_budget_usdc == "0.013000"
    assert exp.spending_summary.uncertain_pending_usdc == "0.000000"
    assert exp.spending_summary.reserved_budget_usdc == "0.000000"
    assert exp.spending_summary.refunded_amount_usdc == "0.013000"
    assert exp.verified_total_spend_usdc == "0.007000"
    assert exp.remaining_budget_usdc == "0.013000"

    # Both call executions verified
    assert len(exp.call_executions) == 2
    assert all(c.is_settlement_verified for c in exp.call_executions)
    assert all(c.output_accepted for c in exp.call_executions)


def test_missing_ledger_data(explanation_gen, mock_ledger):
    """2. If ledger record is missing for a call, spending cannot be certified from ledger."""
    call_missing_id = "call_missing_from_ledger_999"

    # The call claims in buyer memory that it was paid, but ledger has NO entry
    calls = [
        ServiceCallRecord(
            step_id=1,
            call_id=call_missing_id,
            service_id="data_001",
            category=ServiceCategory.DATA,
            status=CallStatus.SUCCEEDED,
            listed_price_usdc="0.002000",
            amount_paid_usdc="0.002000",
            transaction_hash="0x" + "c" * 64,
            validation_status="valid"
        )
    ]

    exp = explanation_gen.generate_explanation(
        task_prompt="Lookup ETH metrics",
        budget_usdc="0.010000",
        calls=calls
    )

    # Must NOT count unverified call in verified spend
    assert exp.spending_summary.verified_spent_usdc == "0.000000"
    assert exp.call_executions[0].is_settlement_verified is False
    assert exp.call_executions[0].verified_paid_usdc == "0.000000"

    # Warning must explain missing ledger record
    assert any("Authoritative ledger record missing" in w for w in exp.warnings)


def test_pending_reconciliation_not_counted_as_verified_spend(explanation_gen, mock_ledger):
    """3. Ambiguous or unsettled payments must NEVER be labeled as verified spending."""
    call_recon_id = "call_recon_timeout_001"

    # Recorded as pending reconciliation in ledger
    mock_ledger.record_transaction(LedgerRecordSchema(
        request_id=call_recon_id,
        buyer_id="buyer_001",
        seller_id="scraping_001",
        service_id="scraping_001",
        listed_price="0.005000",
        amount_paid="0.000000",
        tx_hash=None,
        status=LedgerStatus.FAILED_AND_NOT_CHARGED,
        latency_ms=100.0,
        error_reason="UNCERTAIN_SETTLEMENT: Network timeout after payment dispatched"
    ))

    calls = [
        ServiceCallRecord(
            step_id=1,
            call_id=call_recon_id,
            service_id="scraping_001",
            category=ServiceCategory.SCRAPING,
            status=CallStatus.PENDING_RECONCILIATION,
            listed_price_usdc="0.005000",
            amount_paid_usdc="0.000000",
            transaction_hash=None,
            error="Network timeout after payment dispatched",
            validation_status="pending_reconciliation"
        )
    ]

    exp = explanation_gen.generate_explanation(
        task_prompt="Scrape website",
        budget_usdc="0.010000",
        calls=calls
    )

    # Spending is NOT verified
    assert exp.spending_summary.verified_spent_usdc == "0.000000"
    assert exp.verified_total_spend_usdc == "0.000000"

    # Amount held in uncertain pending
    assert exp.spending_summary.uncertain_pending_usdc == "0.005000"
    assert exp.spending_summary.reserved_budget_usdc == "0.005000"

    # Remaining available budget subtracts held uncertain amount
    assert exp.spending_summary.remaining_budget_usdc == "0.005000"
    assert exp.call_executions[0].is_settlement_verified is False
    assert exp.call_executions[0].output_accepted is False
    assert "pending settlement reconciliation" in exp.task_interpretation


def test_rejected_output_after_verified_payment_retains_cost_and_explanation(explanation_gen, mock_ledger):
    """4. If payment settled but output was invalid, cost is preserved and output rejected."""
    call_bad_schema_id = "call_paid_bad_schema_001"
    valid_tx = "0x" + "d" * 64

    # Ledger marks paid output rejected with verified settlement
    mock_ledger.record_transaction(LedgerRecordSchema(
        request_id=call_bad_schema_id,
        buyer_id="buyer_001",
        seller_id="data_001",
        service_id="data_001",
        listed_price="0.002000",
        amount_paid="0.002000",
        tx_hash=valid_tx,
        status=LedgerStatus.PAID_OUTPUT_REJECTED,
        latency_ms=150.0,
        error_reason="Missing required property: 'price'"
    ))

    calls = [
        ServiceCallRecord(
            step_id=1,
            call_id=call_bad_schema_id,
            service_id="data_001",
            category=ServiceCategory.DATA,
            status=CallStatus.PAID_OUTPUT_REJECTED,
            listed_price_usdc="0.002000",
            amount_paid_usdc="0.002000",
            transaction_hash=valid_tx,
            error="Missing required property: 'price'",
            validation_status="rejected"
        )
    ]

    exp = explanation_gen.generate_explanation(
        task_prompt="Lookup ETH price",
        budget_usdc="0.010000",
        calls=calls
    )

    # Cost is NOT erased! (Money was paid and verified on-chain)
    assert exp.spending_summary.verified_spent_usdc == "0.002000"
    assert exp.spending_summary.remaining_budget_usdc == "0.008000"

    # But output was rejected and not accepted
    assert len(exp.outputs_accepted) == 0
    assert len(exp.outputs_rejected) == 1
    assert "paid 0.002000 USDC, output rejected" in exp.outputs_rejected[0]

    # Execution summary records paid_output_rejected
    summary = exp.call_executions[0]
    assert summary.status == "paid_output_rejected"
    assert summary.is_settlement_verified is True
    assert summary.verified_paid_usdc == "0.002000"
    assert summary.output_accepted is False
    assert summary.rejection_or_failure_reason == "Missing required property: 'price'"


def test_remaining_budget_calculation_zero_float_drift(explanation_gen, mock_ledger):
    """5. Ensure remaining budget, refunded amount, and verified spending have zero floating-point drift."""
    valid_tx = "0x" + "e" * 64
    mock_ledger.record_transaction(LedgerRecordSchema(
        request_id="call_precise_01",
        buyer_id="buyer_001",
        seller_id="inference_001",
        service_id="inference_001",
        listed_price="0.003333",
        amount_paid="0.003333",
        tx_hash=valid_tx,
        status=LedgerStatus.PAID,
        latency_ms=200.0
    ))

    calls = [
        ServiceCallRecord(
            step_id=1,
            call_id="call_precise_01",
            service_id="inference_001",
            category=ServiceCategory.INFERENCE,
            status=CallStatus.SUCCEEDED,
            listed_price_usdc="0.003333",
            amount_paid_usdc="0.003333",
            transaction_hash=valid_tx,
            validation_status="valid"
        )
    ]

    exp = explanation_gen.generate_explanation(
        task_prompt="Analyze precision",
        budget_usdc="0.010000",
        calls=calls
    )

    # 10000 - 3333 = 6667 base units -> exactly 0.006667
    assert exp.spending_summary.budget_allocated_usdc == "0.010000"
    assert exp.spending_summary.verified_spent_usdc == "0.003333"
    assert exp.spending_summary.remaining_budget_usdc == "0.006667"
    assert exp.spending_summary.refunded_amount_usdc == "0.006667"


def test_basescan_explorer_link_no_fabrication():
    """6. Base Sepolia explorer link must be generated ONLY for verified 66-character hex tx hashes."""
    # Valid 66-character tx hash
    valid_tx = "0x" + "f" * 64
    url = ExplanationGenerator._format_explorer_url(valid_tx)
    assert url == f"https://sepolia.basescan.org/tx/{valid_tx}"

    # Invalid / mock strings must return None (NO fabricated links!)
    assert ExplanationGenerator._format_explorer_url("receipt_12345") is None
    assert ExplanationGenerator._format_explorer_url("0x1234fake") is None
    assert ExplanationGenerator._format_explorer_url("") is None
    assert ExplanationGenerator._format_explorer_url(None) is None
    assert ExplanationGenerator._format_explorer_url("0x" + "g" * 64) is None  # 'g' is not hex


def test_service_selection_explanation_actual_evidence(explanation_gen):
    """7. Explain service choices using actual selection factors from registry without fabricating reputation."""
    calls = [
        ServiceCallRecord(
            step_id=1,
            call_id="call_sel_01",
            service_id="data_001",
            category=ServiceCategory.DATA,
            status=CallStatus.SUCCEEDED,
            listed_price_usdc="0.002000",
            validation_status="valid"
        )
    ]

    exp = explanation_gen.generate_explanation(
        task_prompt="Lookup ETH",
        budget_usdc="0.010000",
        calls=calls
    )

    reason = exp.selected_services[0]
    assert reason.service_id == "data_001"
    assert reason.category == "data"
    assert reason.listed_price_usdc == "0.002000"
    # data_001 in seed registry has reputation score 98.5
    assert reason.reputation_score == 98.5
    assert reason.median_latency_ms == 120.0
    assert "98.5/100" in reason.reason


@pytest.mark.asyncio
async def test_dashboard_endpoint_agrees_with_authoritative_ledger(client):
    """8. Task and result endpoints agree with authoritative ledger totals."""
    # Create and execute task via buyer API
    res = client.post(
        "/api/v1/tasks",
        json={
            "task": "Explain purchase and spending summary for ETH analysis",
            "budget_usdc": "0.050000",
            "max_concurrency": 3,
            "execute_now": False
        }
    )
    assert res.status_code == 201
    data = res.json()
    task_id = data["task_id"]

    # Verify task detail endpoint returns consistent schema
    detail_res = client.get(f"/api/v1/tasks/{task_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["task_id"] == task_id
    assert detail["budget_usdc"] == "0.050000"
    assert detail["spent_usdc"] == "0.000000"
    assert detail["remaining_usdc"] == "0.050000"

    # Verify task result endpoint returns consistent schema
    result_res = client.get(f"/api/v1/tasks/{task_id}/result")
    assert result_res.status_code == 200
    result_data = result_res.json()
    assert result_data["task_id"] == task_id
    assert "provenance" in result_data
    assert result_data["spent_usdc"] == "0.000000"
    assert result_data["remaining_usdc"] == "0.050000"

    # Verify legacy dashboard route also returns 200
    legacy_res = client.get(f"/api/v1/buyer/tasks/{task_id}")
    assert legacy_res.status_code == 200
    assert legacy_res.json()["task_id"] == task_id
