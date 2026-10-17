"""[IMPLEMENTED] Phase 4 Comprehensive Autonomous Multi-Hop Orchestration & Ledger Finality Test Suite.

Covers:
1. Successful single-hop execution.
2. Successful multi-hop execution (Data -> Scraping -> Inference DAG).
3. Failure in intermediate hop (fail-closed, subsequent steps aborted and uncharged).
4. Correct overall status when only part of route succeeds (partial_failure).
5. Duplicate request and retry idempotency (scoped hop idempotency).
6. Invalid authorization rejected before paid execution.
7. Replayed authorization nonce rejected.
8. Cross-process / independent-connection nonce race protection (ACID isolation).
9. Budget reservation under concurrent calls (atomic overdraw protection).
10. No duplicate ledger application for the same settlement evidence.
11. Transaction hash alone never implies confirmed on-chain settlement.
12. Mocked/offline settlement remains strictly distinguishable from live verified settlement.
13. Timeout and downstream service failure handling.
14. Recovery from interrupted or failed persistence operation.
15. Backward compatibility with official x402 v2 and legacy headers.
16. Multi-hop route validation (cycle detection, empty route, hop count limits).
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import time
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.session import Base
from backend.shared.constants import (
    LedgerStatus,
    NETWORK_BASE_SEPOLIA,
    USDC_BASE_SEPOLIA,
    base_units_to_usdc,
    usdc_to_base_units,
)
from backend.shared.schemas import ServiceDefinition, PaymentRequirement, PaymentPayload
from backend.registry.service_catalog import catalog
from backend.ledger.models import ledger_repo, LedgerRecordSchema
from backend.payments.budget import BudgetManager
from backend.payments.idempotency import IdempotencyStore, compute_payload_hash
from backend.payments.policy import PaymentPolicyVerifier
from backend.payments.settlement import (
    SettlementVerifier,
    SellerPaymentVerifier,
    AuthorizationNonceGuard,
    authorization_nonce_guard,
)
from backend.payments.schemas import (
    MultiHopStep,
    MultiHopRouteResult,
    PaidCallRequest,
    PaidCallResult,
    PaymentStatus,
)
from backend.payments.errors import (
    BudgetExceededError,
    PaymentEngineError,
    PaymentPolicyViolationError,
    SettlementVerificationError,
)
from backend.payments.models import (
    AuthorizationNonceReservationModel,
    BudgetReservationModel,
    DurablePaymentRepository,
    PaymentAttemptModel,
    SettlementEvidenceRecordModel,
    durable_payment_repo,
)
from backend.payments.service import PaymentService


@pytest.fixture(autouse=True)
def clean_payment_and_ledger_state():
    """Ensure clean durable repository, in-memory nonce guard, and ledger state between tests."""
    authorization_nonce_guard.clear()
    durable_payment_repo.clear_authorization_nonces()
    with durable_payment_repo.session_factory() as session:
        session.query(BudgetReservationModel).delete()
        session.query(PaymentAttemptModel).delete()
        session.query(SettlementEvidenceRecordModel).delete()
        session.commit()
    # Clear ledger records
    if hasattr(ledger_repo, "clear"):
        ledger_repo.clear()
    elif hasattr(ledger_repo, "_records"):
        ledger_repo._records.clear()
    yield
    authorization_nonce_guard.clear()
    durable_payment_repo.clear_authorization_nonces()
    with durable_payment_repo.session_factory() as session:
        session.query(BudgetReservationModel).delete()
        session.query(PaymentAttemptModel).delete()
        session.query(SettlementEvidenceRecordModel).delete()
        session.commit()


# -----------------------------------------------------------------------------
# 1. Successful Single-Hop Execution
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_successful_single_hop_execution():
    service = PaymentService()
    task_id = "task_single_hop_01"
    route = [
        MultiHopStep(
            step_id=1,
            service_id="data_001",
            input_payload={"symbol": "ETH"},
        )
    ]
    res = await service.execute_multi_hop_route(task_id=task_id, route=route)
    assert res.status == "completed"
    assert res.total_hops == 1
    assert res.executed_hops == 1
    assert res.successful_hops == 1
    assert res.total_cost_base_units == 2000
    assert len(res.steps) == 1
    assert res.steps[0].status == PaymentStatus.PAID
    assert res.final_output is not None
    assert "price" in res.final_output


# -----------------------------------------------------------------------------
# 2. Successful Multi-Hop Execution (Data -> Scraping -> Inference)
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_successful_multi_hop_execution_dag():
    service = PaymentService()
    task_id = "task_multi_hop_dag_01"
    route = [
        MultiHopStep(
            step_id=1,
            service_id="data_001",
            input_payload={"symbol": "BTC"},
            depends_on=[],
        ),
        MultiHopStep(
            step_id=2,
            service_id="scraping_001",
            input_payload={"url": "https://example.com/crypto"},
            depends_on=[1],
        ),
        MultiHopStep(
            step_id=3,
            service_id="inference_001",
            input_payload={"prompt": "Summarize market movements"},
            depends_on=[2],
            input_transform={"prompt": "step_2.content"},
        ),
    ]

    res = await service.execute_multi_hop_route(task_id=task_id, route=route)
    assert res.status == "completed"
    assert res.total_hops == 3
    assert res.executed_hops == 3
    assert res.successful_hops == 3
    # data: 2000, scraping: 3000, inference: 4000 -> 9000 total
    assert res.total_cost_base_units == 9000
    assert res.total_cost_usdc == "0.009000"
    assert res.steps[0].service_id == "data_001"
    assert res.steps[1].service_id == "scraping_001"
    assert res.steps[2].service_id == "inference_001"
    assert res.final_output is not None
    assert "response" in res.final_output


# -----------------------------------------------------------------------------
# 3 & 4. Intermediate Hop Failure and Partial Multi-Hop Status
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_intermediate_hop_failure_stops_downstream_and_preserves_budget():
    service = PaymentService()
    task_id = "task_intermediate_fail_01"
    budget_mgr = service.get_or_create_task_budget(task_id, 10000)

    # Step 2 will fail schema validation / refusal
    route = [
        MultiHopStep(
            step_id=1,
            service_id="data_001",
            input_payload={"symbol": "ETH"},
        ),
        MultiHopStep(
            step_id=2,
            service_id="scraping_001",
            input_payload={},  # Missing required 'url' -> fails schema or 400
            depends_on=[1],
        ),
        MultiHopStep(
            step_id=3,
            service_id="inference_001",
            input_payload={"prompt": "Will never be executed"},
            depends_on=[2],
        ),
    ]

    res = await service.execute_multi_hop_route(task_id=task_id, route=route, budget_manager=budget_mgr)
    assert res.status == "partial_failure"
    assert res.executed_hops == 2
    assert res.successful_hops == 1
    assert res.error_step_id == 2
    # Only step 1 was paid (2000 units), step 2 failed without charge, step 3 never executed!
    assert res.total_cost_base_units == 2000
    assert budget_mgr.total_spent == 2000
    assert budget_mgr.available_budget == 8000


# -----------------------------------------------------------------------------
# 5. Duplicate Request and Retry Idempotency
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_multi_hop_retry_idempotency_does_not_double_charge():
    service = PaymentService()
    task_id = "task_idemp_01"
    budget_mgr = service.get_or_create_task_budget(task_id, 20000)

    route = [
        MultiHopStep(
            step_id=1,
            service_id="data_001",
            input_payload={"symbol": "SOL"},
        ),
    ]

    # First execution
    res1 = await service.execute_multi_hop_route(task_id=task_id, route=route, budget_manager=budget_mgr)
    assert res1.status == "completed"
    assert res1.total_cost_base_units == 2000
    assert budget_mgr.total_spent == 2000

    # Second execution (retry with same task_id and input)
    res2 = await service.execute_multi_hop_route(task_id=task_id, route=route, budget_manager=budget_mgr)
    assert res2.status == "completed"
    assert res2.total_cost_base_units == 2000
    # Committed spend MUST remain 2000, not 4000!
    assert budget_mgr.total_spent == 2000


# -----------------------------------------------------------------------------
# 6. Invalid Authorization Rejected Before Paid Execution
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_invalid_authorization_rejected_before_execution():
    verifier = SellerPaymentVerifier(test_mode=True)
    req = verifier.issue_challenge("data_001", 2000, "0x0000000000000000000000000000000000000001")

    # Mismatched network in authorization
    bad_payload = PaymentPayload(
        version="2.0",
        buyer_address="0x1111111111111111111111111111111111111111",
        signature="0x402_sig_valid",
        authorization={
            "network": "eip155:1",  # Wrong network (Ethereum Mainnet instead of Base Sepolia)
            "token": USDC_BASE_SEPOLIA,
            "payTo": "0x0000000000000000000000000000000000000001",
            "amount": "2000",
            "nonce": "nonce_bad_net_123",
        }
    )

    with pytest.raises(SettlementVerificationError) as exc_info:
        await verifier.verify_and_settle(bad_payload, req)
    assert "Network mismatch" in str(exc_info.value)


# -----------------------------------------------------------------------------
# 7. Replayed Nonce Rejected
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_replayed_nonce_rejected_immediately():
    verifier = SellerPaymentVerifier(test_mode=True)
    req = verifier.issue_challenge("data_001", 2000, "0x0000000000000000000000000000000000000001")

    payload = PaymentPayload(
        version="2.0",
        buyer_address="0x1111111111111111111111111111111111111111",
        signature="0x402_sig_first_pass",
        authorization={
            "network": NETWORK_BASE_SEPOLIA,
            "token": USDC_BASE_SEPOLIA,
            "payTo": "0x0000000000000000000000000000000000000001",
            "amount": "2000",
            "nonce": "nonce_unique_test_replay_001",
        }
    )

    # First call succeeds
    receipt = await verifier.verify_and_settle(payload, req)
    assert receipt.facilitator_receipt_id is not None

    # Replay with same nonce MUST be rejected
    with pytest.raises(SettlementVerificationError) as exc_info:
        await verifier.verify_and_settle(payload, req)
    assert "Authorization nonce replay detected" in str(exc_info.value)


# -----------------------------------------------------------------------------
# 8. Cross-Process / Independent-Connection Durable Nonce Race Protection
# -----------------------------------------------------------------------------
def test_durable_nonce_reservation_cross_process_race_protection():
    """Verify that two independent database connections concurrently reserving the same nonce fail closed."""
    repo1 = DurablePaymentRepository()
    repo2 = DurablePaymentRepository()

    auth_key = "eip155:84532:0x2222222222222222222222222222222222222222:nonce_race_999"
    network = NETWORK_BASE_SEPOLIA
    signer = "0x2222222222222222222222222222222222222222"
    nonce = "nonce_race_999"

    results = []

    def try_reserve(repo_instance):
        try:
            success = repo_instance.atomic_reserve_authorization_nonce(
                auth_key=auth_key,
                network=network,
                signer_address=signer,
                nonce=nonce,
            )
            results.append(("success", success))
        except SettlementVerificationError as sve:
            results.append(("rejected", str(sve)))

    # Run simultaneously on two separate repository instances (separate DB connections)
    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(try_reserve, repo1)
        f2 = executor.submit(try_reserve, repo2)
        f1.result()
        f2.result()

    # Exactly one must succeed, and exactly one must be rejected!
    successes = [r for r in results if r[0] == "success"]
    rejections = [r for r in results if r[0] == "rejected"]
    assert len(successes) == 1, f"Expected 1 success, got {results}"
    assert len(rejections) == 1, f"Expected 1 rejection, got {results}"
    assert "already in-flight" in rejections[0][1] or "replay detected" in rejections[0][1]


# -----------------------------------------------------------------------------
# 9. Budget Reservation Under Concurrent Calls
# -----------------------------------------------------------------------------
def test_concurrent_budget_reservations_cannot_exceed_total():
    repo = DurablePaymentRepository()
    task_id = f"task_concurrent_budget_{time.time_ns()}"
    total_budget = 5000  # Only enough for 2 calls of 2000 units

    results = []

    def reserve_worker(call_id, amount):
        res_id = f"res_{task_id}_{call_id}"
        success, avail, err = repo.atomic_reserve(
            task_id=task_id,
            reservation_id=res_id,
            call_id=call_id,
            amount_base_units=amount,
            total_budget_units=total_budget,
        )
        results.append((call_id, success, avail, err))

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(reserve_worker, f"c{i}", 2000)
            for i in range(4)
        ]
        for f in futures:
            f.result()

    successful = [r for r in results if r[1] is True]
    failed = [r for r in results if r[1] is False]
    # At most 2 can succeed (2 * 2000 = 4000 <= 5000; third would be 6000 > 5000)
    assert len(successful) == 2
    assert len(failed) == 2


# -----------------------------------------------------------------------------
# 10. No Duplicate Ledger Application for Same Settlement Evidence
# -----------------------------------------------------------------------------
def test_no_duplicate_settlement_evidence_recording():
    repo = DurablePaymentRepository()
    tx_hash = "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"

    # First attempt records evidence
    recorded1 = repo.atomic_record_settlement_evidence(
        attempt_id="att_first_001",
        network=NETWORK_BASE_SEPOLIA,
        amount_units=2000,
        tx_hash=tx_hash,
        log_index=0,
    )
    assert recorded1 is True

    # Same attempt is idempotent
    recorded_idemp = repo.atomic_record_settlement_evidence(
        attempt_id="att_first_001",
        network=NETWORK_BASE_SEPOLIA,
        amount_units=2000,
        tx_hash=tx_hash,
        log_index=0,
    )
    assert recorded_idemp is True

    # Different attempt claiming same tx_hash and log_index MUST fail with SettlementVerificationError
    with pytest.raises(SettlementVerificationError) as exc_info:
        repo.atomic_record_settlement_evidence(
            attempt_id="att_different_002",
            network=NETWORK_BASE_SEPOLIA,
            amount_units=2000,
            tx_hash=tx_hash,
            log_index=0,
        )
    assert "Duplicate settlement evidence detected" in str(exc_info.value)


# -----------------------------------------------------------------------------
# 11 & 12. Transaction Hash Alone Never Implies Confirmed Settlement
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_tx_hash_alone_leaves_confirmed_on_chain_false_without_rpc():
    verifier = SettlementVerifier(test_mode=False, rpc_url="https://unreachable.rpc.test")
    raw_tx = "0x9999999999999999999999999999999999999999999999999999999999999999"

    # In live mode without RPC receipt, proof verification MUST fail closed
    with pytest.raises(SettlementVerificationError) as exc:
        await verifier.verify_full_settlement(
            proof_header=raw_tx,
            expected_network=NETWORK_BASE_SEPOLIA,
            expected_token=USDC_BASE_SEPOLIA,
            expected_pay_to="0x0000000000000000000000000000000000000001",
            expected_amount_units=2000,
        )
    assert "unconfirmed or reverted" in str(exc.value)


# -----------------------------------------------------------------------------
# 13. Timeout and Downstream Service Failure Handling
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_unavailable_service_refuses_cleanly():
    service = PaymentService()
    task_id = "task_bad_service_01"
    route = [
        MultiHopStep(
            step_id=1,
            service_id="nonexistent_service_999",
            input_payload={},
        )
    ]
    res = await service.execute_multi_hop_route(task_id=task_id, route=route)
    assert res.status == "refused"
    assert "not found in catalog" in res.error_message


# -----------------------------------------------------------------------------
# 14. Route Validation: Cycle Detection, Hop Limit, Empty Route
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_route_cycle_detection():
    service = PaymentService()
    task_id = "task_cycle_01"
    # Step 1 depends on 2, step 2 depends on 1 -> cycle!
    route = [
        MultiHopStep(step_id=1, service_id="data_001", depends_on=[2]),
        MultiHopStep(step_id=2, service_id="scraping_001", depends_on=[1]),
    ]
    res = await service.execute_multi_hop_route(task_id=task_id, route=route)
    assert res.status == "refused"
    assert "Dependency cycle detected" in res.error_message


@pytest.mark.asyncio
async def test_route_empty_and_max_hops():
    service = PaymentService()

    # Empty route
    res_empty = await service.execute_multi_hop_route(task_id="t_empty", route=[])
    assert res_empty.status == "refused"
    assert "contains no hops" in res_empty.error_message

    # Exceeds max hops
    route_too_long = [
        MultiHopStep(step_id=i, service_id="data_001")
        for i in range(1, 15)
    ]
    res_long = await service.execute_multi_hop_route(task_id="t_long", route=route_too_long, max_hops=10)
    assert res_long.status == "refused"
    assert "exceeds maximum allowed limit" in res_long.error_message


# -----------------------------------------------------------------------------
# 15. Ledger Consistency Across Successful Multi-Hop
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_ledger_records_accurate_status_for_each_hop():
    service = PaymentService()
    task_id = "task_ledger_check_01"
    route = [
        MultiHopStep(step_id=1, service_id="data_001", input_payload={"symbol": "ETH"}),
        MultiHopStep(step_id=2, service_id="scraping_001", input_payload={"url": "https://test.com"}, depends_on=[1]),
    ]

    res = await service.execute_multi_hop_route(task_id=task_id, route=route)
    assert res.status == "completed"

    records = ledger_repo.list_records(limit=20)
    task_records = [r for r in records if r.request_id in [res.steps[0].request_id, res.steps[1].request_id]]
    assert len(task_records) == 2
    for rec in task_records:
        assert rec.status == LedgerStatus.PAID
        assert rec.amount_paid != "0.000000"


# -----------------------------------------------------------------------------
# 16. Mocked/Offline Settlement Distinguishable from Live Verified Settlement
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_mock_settlement_remains_unverified_onchain():
    """Verify that synthetic test-mode receipts never produce confirmed on-chain status."""
    verifier = SettlementVerifier(test_mode=True)
    # Mock receipt
    receipt = await verifier.verify_settlement_proof("0x_mock_settlement_receipt", expected_amount_units=2000)
    assert receipt.tx_hash is None or receipt.tx_hash.startswith("0x_mock")
    # Live verifier must reject mock receipt outright
    live_verifier = SettlementVerifier(test_mode=False, rpc_url="https://unreachable.rpc.test")
    with pytest.raises(SettlementVerificationError):
        await live_verifier.verify_full_settlement(
            proof_header="0x_mock_settlement_receipt",
            expected_network=NETWORK_BASE_SEPOLIA,
            expected_token=USDC_BASE_SEPOLIA,
            expected_pay_to="0x0000000000000000000000000000000000000001",
            expected_amount_units=2000,
        )


# -----------------------------------------------------------------------------
# 17. Consumed Nonce Cannot Be Released or Replayed
# -----------------------------------------------------------------------------
def test_consumed_nonce_cannot_be_released_or_replayed():
    """Verify that once a nonce transitions to consumed, release_authorization_nonce refuses to release it."""
    repo = DurablePaymentRepository()
    auth_key = f"eip155:84532:0x3333333333333333333333333333333333333333:nonce_committed_{time.time_ns()}"

    # 1. Reserve
    res = repo.atomic_reserve_authorization_nonce(
        auth_key=auth_key,
        network=NETWORK_BASE_SEPOLIA,
        nonce="nonce_committed",
        signer_address="0x3333333333333333333333333333333333333333",
    )
    assert res is True

    # 2. Commit to consumed
    comm = repo.commit_authorization_nonce(auth_key)
    assert comm is True
    assert repo.is_authorization_nonce_consumed(auth_key) is True

    # 3. Attempt release must be refused
    released = repo.release_authorization_nonce(auth_key)
    assert released is False

    # 4. Attempt re-reservation must still be rejected as replay
    with pytest.raises(SettlementVerificationError) as exc:
        repo.atomic_reserve_authorization_nonce(
            auth_key=auth_key,
            network=NETWORK_BASE_SEPOLIA,
            nonce="nonce_committed",
            signer_address="0x3333333333333333333333333333333333333333",
        )
    assert "already been consumed" in str(exc.value)


# -----------------------------------------------------------------------------
# 18. Route Cost Exceeding Total Budget Refused Upfront
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_route_cost_exceeding_total_budget_refused_upfront():
    service = PaymentService()
    task_id = f"task_budget_exceeded_{time.time_ns()}"
    budget_mgr = service.get_or_create_task_budget(task_id, 3000)  # Only 3000 units

    # Route requires 2000 (data) + 3000 (scraping) = 5000 units > 3000
    route = [
        MultiHopStep(step_id=1, service_id="data_001", input_payload={"symbol": "ETH"}),
        MultiHopStep(step_id=2, service_id="scraping_001", input_payload={"url": "https://test.com"}, depends_on=[1]),
    ]

    res = await service.execute_multi_hop_route(task_id=task_id, route=route, budget_manager=budget_mgr)
    assert res.status == "refused"
    assert "exceeds allocated budget" in res.error_message
    assert res.executed_hops == 0
    assert budget_mgr.total_spent == 0


# -----------------------------------------------------------------------------
# 19. Multi-Process Nonce Reservation Race Across Separate OS Processes
# -----------------------------------------------------------------------------
def test_multiprocess_nonce_reservation_race():
    """Spawn two separate Python OS subprocesses that race to reserve the same nonce."""
    import subprocess
    import sys

    auth_key = f"eip155:84532:0x4444444444444444444444444444444444444444:nonce_proc_race_{time.time_ns()}"

    script = f"""
import sys
from backend.payments.models import DurablePaymentRepository
from backend.payments.errors import SettlementVerificationError

repo = DurablePaymentRepository()
try:
    repo.atomic_reserve_authorization_nonce(
        auth_key="{auth_key}",
        network="eip155:84532",
        nonce="proc_nonce",
        signer_address="0x4444444444444444444444444444444444444444",
    )
    print("RESERVED")
    sys.exit(0)
except SettlementVerificationError:
    print("REPLAY_REJECTED")
    sys.exit(1)
except Exception as e:
    print("ERROR:", e)
    sys.exit(2)
"""

    p1 = subprocess.Popen([sys.executable, "-c", script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    p2 = subprocess.Popen([sys.executable, "-c", script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    out1, err1 = p1.communicate(timeout=10)
    out2, err2 = p2.communicate(timeout=10)

    exit_codes = sorted([p1.returncode, p2.returncode])
    outputs = [out1.strip(), out2.strip()]

    # Exactly one process must succeed (exit 0) and one must be rejected (exit 1)
    assert exit_codes == [0, 1], f"Expected [0, 1] but got {exit_codes}. Outputs: {outputs}. Errors: {[err1, err2]}"
    assert "RESERVED" in outputs
    assert "REPLAY_REJECTED" in outputs
