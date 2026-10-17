"""Comprehensive Unit Tests for Member 1 Payment Engine Subsystem."""
import pytest
import httpx
from unittest.mock import AsyncMock, patch

from backend.shared.constants import NETWORK_BASE_SEPOLIA, USDC_BASE_SEPOLIA
from backend.shared.schemas import ServiceDefinition, ServiceCategory
from backend.registry.service_catalog import catalog
from backend.payments.budget import BudgetManager
from backend.payments.idempotency import IdempotencyStore, compute_payload_hash
from backend.payments.policy import PaymentPolicyVerifier
from backend.payments.settlement import SettlementVerifier
from backend.payments.x402_adapter import X402Adapter
from backend.payments.service import PaymentService
from backend.payments.schemas import PaidCallResult, PaymentStatus
from backend.payments.errors import IdempotencyConflictError, BudgetExceededError

# Also test compatibility alias
from backend.app.payments.service import payment_service as aliased_payment_service


@pytest.fixture
def mock_service():
    """Register a dedicated test service in catalog and clean up after test."""
    test_svc = ServiceDefinition(
        service_id="test_service_001",
        name="Test Analytics Service",
        category=ServiceCategory.DATA,
        endpoint_url="http://testserver/api/v1/seller/data",
        price_usdc="0.002",
        network=NETWORK_BASE_SEPOLIA,
        pay_to="0x0000000000000000000000000000000000000001",
        input_schema={"type": "object", "required": ["symbol"], "properties": {"symbol": {"type": "string"}}},
        output_schema={"type": "object", "required": ["symbol", "price"], "properties": {"symbol": {"type": "string"}, "price": {"type": "number"}}},
        is_active=True
    )
    catalog.register_service(test_svc)
    yield test_svc
    catalog._services.pop(test_svc.service_id, None)


@pytest.fixture
def clean_payment_service():
    """Create a clean isolated PaymentService with dedicated in-memory stores in test mode."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from backend.payments.models import Base, DurablePaymentRepository

    test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(test_engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    repo = DurablePaymentRepository(session_factory=TestSession)

    store = IdempotencyStore(repo=repo)
    policy = PaymentPolicyVerifier()
    settlement = SettlementVerifier(test_mode=True, durable_repo=repo)
    adapter = X402Adapter(policy_verifier=policy, test_mode=True)
    return PaymentService(
        policy_verifier=policy,
        settlement_verifier=settlement,
        adapter=adapter,
        store=store,
        durable_repo=repo
    )


@pytest.mark.asyncio
async def test_execute_paid_call_success(mock_service, clean_payment_service):
    """Test successful paid call flow returning PAID status and verified output."""
    budget_mgr = clean_payment_service.get_or_create_task_budget("task_001", 100_000)

    # Mock the adapter's network call
    with patch.object(
        clean_payment_service.adapter,
        "execute_paid_request",
        new=AsyncMock(return_value=(200, {"symbol": "ETH", "price": 2750.0}, "receipt_test_123456"))
    ):
        result = await clean_payment_service.execute_paid_call(
            task_id="task_001",
            call_id="call_001",
            service_id=mock_service.service_id,
            input_payload={"symbol": "ETH"},
            idempotency_key="key_success_001",
            task_budget_manager=budget_mgr
        )

    assert result.status == PaymentStatus.PAID
    assert result.amount_base_units == 2000
    assert result.amount_usdc == "0.002"
    assert result.seller_output == {"symbol": "ETH", "price": 2750.0}
    assert result.settlement_proof == "receipt_test_123456"
    assert result.error_code is None
    # Budget check
    assert budget_mgr.available_budget == 98_000


@pytest.mark.asyncio
async def test_execute_paid_call_output_rejected(mock_service, clean_payment_service):
    """Test when payment settles but seller response fails output schema (PAID_OUTPUT_REJECTED)."""
    budget_mgr = clean_payment_service.get_or_create_task_budget("task_002", 100_000)

    # Seller output violates required schema (missing 'price')
    with patch.object(
        clean_payment_service.adapter,
        "execute_paid_request",
        new=AsyncMock(return_value=(200, {"symbol": "ETH", "corrupted": True}, "receipt_corrupted_001"))
    ):
        result = await clean_payment_service.execute_paid_call(
            task_id="task_002",
            call_id="call_002",
            service_id=mock_service.service_id,
            input_payload={"symbol": "ETH"},
            idempotency_key="key_corrupted_002",
            task_budget_manager=budget_mgr
        )

    assert result.status == PaymentStatus.PAID_OUTPUT_REJECTED
    assert result.error_code == "OUTPUT_SCHEMA_INVALID"
    # Money was still spent and committed
    assert budget_mgr.available_budget == 98_000


@pytest.mark.asyncio
async def test_execute_paid_call_budget_refused(mock_service, clean_payment_service):
    """Test that insufficient budget refuses operation before payment (REFUSED)."""
    budget_mgr = clean_payment_service.get_or_create_task_budget("task_003", 1000)  # Only 1000 units, service costs 2000

    result = await clean_payment_service.execute_paid_call(
        task_id="task_003",
        call_id="call_003",
        service_id=mock_service.service_id,
        input_payload={"symbol": "ETH"},
        idempotency_key="key_budget_refused",
        task_budget_manager=budget_mgr
    )

    assert result.status == PaymentStatus.REFUSED
    assert result.error_code == "BUDGET_EXCEEDED"
    assert budget_mgr.available_budget == 1000  # Untouched


@pytest.mark.asyncio
async def test_idempotency_replay_cached_result(mock_service, clean_payment_service):
    """Test that repeating the identical call returns cached result without duplicate payment."""
    budget_mgr = clean_payment_service.get_or_create_task_budget("task_004", 100_000)

    mock_exec = AsyncMock(return_value=(200, {"symbol": "BTC", "price": 68000.0}, "receipt_btc_01"))
    with patch.object(clean_payment_service.adapter, "execute_paid_request", new=mock_exec):
        res1 = await clean_payment_service.execute_paid_call(
            task_id="task_004",
            call_id="call_004",
            service_id=mock_service.service_id,
            input_payload={"symbol": "BTC"},
            idempotency_key="key_replay_001",
            task_budget_manager=budget_mgr
        )
        assert res1.status == PaymentStatus.PAID
        assert mock_exec.call_count == 1

        # Second call with identical key and payload
        res2 = await clean_payment_service.execute_paid_call(
            task_id="task_004",
            call_id="call_004",
            service_id=mock_service.service_id,
            input_payload={"symbol": "BTC"},
            idempotency_key="key_replay_001",
            task_budget_manager=budget_mgr
        )
        assert res2.status == PaymentStatus.PAID
        assert res2.request_id == res1.request_id
        # Adapter was NOT called a second time
        assert mock_exec.call_count == 1


@pytest.mark.asyncio
async def test_idempotency_conflict_different_payload(mock_service, clean_payment_service):
    """Test that reusing key with mutated payload raises IDEMPOTENCY_CONFLICT."""
    budget_mgr = clean_payment_service.get_or_create_task_budget("task_005", 100_000)

    mock_exec = AsyncMock(return_value=(200, {"symbol": "BTC", "price": 68000.0}, "receipt_btc_01"))
    with patch.object(clean_payment_service.adapter, "execute_paid_request", new=mock_exec):
        await clean_payment_service.execute_paid_call(
            task_id="task_005",
            call_id="call_005",
            service_id=mock_service.service_id,
            input_payload={"symbol": "BTC"},
            idempotency_key="key_conflict_001",
            task_budget_manager=budget_mgr
        )

        # Mutate input_payload to SOL with same key
        conflict_res = await clean_payment_service.execute_paid_call(
            task_id="task_005",
            call_id="call_005",
            service_id=mock_service.service_id,
            input_payload={"symbol": "SOL"},
            idempotency_key="key_conflict_001",
            task_budget_manager=budget_mgr
        )

    assert conflict_res.status == PaymentStatus.REFUSED
    assert conflict_res.error_code == "IDEMPOTENCY_CONFLICT"


@pytest.mark.asyncio
async def test_settlement_timeout_transitions_to_pending_reconciliation(mock_service, clean_payment_service):
    """Test that timeout after payment submission marks PENDING_RECONCILIATION and holds budget."""
    budget_mgr = clean_payment_service.get_or_create_task_budget("task_006", 100_000)

    from backend.payments.errors import SettlementTimeoutError
    with patch.object(
        clean_payment_service.adapter,
        "execute_paid_request",
        side_effect=SettlementTimeoutError("att_timeout_01")
    ):
        result = await clean_payment_service.execute_paid_call(
            task_id="task_006",
            call_id="call_006",
            service_id=mock_service.service_id,
            input_payload={"symbol": "ETH"},
            idempotency_key="key_timeout_001",
            task_budget_manager=budget_mgr
        )

    assert result.status == PaymentStatus.PENDING_RECONCILIATION
    assert result.error_code == "SETTLEMENT_TIMEOUT"
    # Budget is NOT released because funds may have been debited on-chain!
    assert budget_mgr.reserved_budget == 2000
    # Crucial boundary: attempt is retained in suspense, NOT written as REFUSED in ledger
    assert clean_payment_service.get_pending_reconciliation(result.request_id) is not None


def test_x402_adapter_fails_closed_in_live_mode_without_credentials():
    """Verify live mode fails closed and forbids mock signing if credentials/deps are missing."""
    from backend.shared.schemas import PaymentRequirement
    from backend.payments.errors import PaymentEngineError

    # Force live mode (test_mode=False) with no private key
    adapter = X402Adapter(test_mode=False)
    adapter.buyer_private_key = None

    req = PaymentRequirement(
        network=NETWORK_BASE_SEPOLIA,
        token=USDC_BASE_SEPOLIA,
        payTo="0x0000000000000000000000000000000000000001",
        amount="2000",
        nonce="nonce_test_001",
        service_id="test_service_001",
    )

    with pytest.raises(PaymentEngineError) as exc_info:
        adapter.create_payment_payload(req, idempotency_key="key_live_fail_closed")

    assert "Live mode fails closed and strictly forbids mock signatures" in str(exc_info.value)


def test_x402_adapter_allows_mock_signature_only_in_test_mode():
    """Verify deterministic mock signatures are generated only when test_mode=True."""
    from backend.shared.schemas import PaymentRequirement

    adapter = X402Adapter(test_mode=True)
    adapter.buyer_private_key = None

    req = PaymentRequirement(
        network=NETWORK_BASE_SEPOLIA,
        token=USDC_BASE_SEPOLIA,
        payTo="0x0000000000000000000000000000000000000001",
        amount="2000",
        nonce="nonce_test_002",
        service_id="test_service_001",
    )

    payload = adapter.create_payment_payload(req, idempotency_key="key_test_mode")
    assert payload["signature"].startswith("0x_mock_sig_")


@pytest.mark.asyncio
async def test_settlement_verifier_live_mode_rejects_unverified_hash():
    """Verify live mode verifier rejects unconfirmed on-chain hash instead of accepting hex length."""
    from backend.payments.errors import SettlementVerificationError

    verifier = SettlementVerifier(test_mode=False)
    unconfirmed_tx = "0x" + "a" * 64

    # In live mode with mock/offline RPC, unconfirmed tx MUST raise SettlementVerificationError
    with pytest.raises(SettlementVerificationError) as exc_info:
        await verifier.verify_settlement_proof(unconfirmed_tx, expected_amount_units=2000)

    assert "unconfirmed or reverted" in str(exc_info.value)


def test_payments_module_compatibility_alias_singletons():
    """Verify backend.app.payments aliases share identical singleton instances without duplication."""
    import backend.payments as bp
    import backend.app.payments as bap

    assert bap.payment_service is bp.payment_service
    assert bap.idempotency_store is bp.idempotency_store
    assert bap.x402_adapter is bp.x402_adapter
    assert bap.PaymentStatus is bp.PaymentStatus

