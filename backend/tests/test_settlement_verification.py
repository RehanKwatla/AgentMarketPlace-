"""Comprehensive Test Suite for 6-Point On-Chain Settlement Verification (Phase 2B).

Validates:
1. Expected network (eip155:84532).
2. Transaction receipt status (status == 0x1).
3. Target token contract (USDC Base Sepolia).
4. Verified seller recipient (payTo).
5. Exact integer amount in USDC base units.
6. Decoded ERC-20 Transfer(address,address,uint256) event logs.
7. SellerPaymentVerifierInterface concrete implementation for Member 2.
"""
import pytest
from unittest.mock import AsyncMock, patch

from backend.shared.constants import (
    NETWORK_BASE_SEPOLIA,
    USDC_BASE_SEPOLIA,
)
from backend.shared.schemas import PaymentPayload, PaymentRequirement
from backend.payments.settlement import (
    SettlementVerifier,
    SellerPaymentVerifier,
    ERC20_TRANSFER_TOPIC,
)
from backend.payments.errors import SettlementVerificationError
from backend.payments.schemas import PaymentStatus


def _build_mock_transfer_log(
    token_address: str,
    from_address: str,
    to_address: str,
    amount_base_units: int,
    tx_hash: str = "0x" + "a" * 64,
) -> dict:
    """Helper to construct raw EVM log dictionary matching ERC-20 Transfer."""
    from_padded = "0x" + "0" * 24 + from_address[2:].lower()
    to_padded = "0x" + "0" * 24 + to_address[2:].lower()
    data_hex = "0x" + hex(amount_base_units)[2:].zfill(64)

    return {
        "address": token_address.lower(),
        "topics": [
            ERC20_TRANSFER_TOPIC.lower(),
            from_padded,
            to_padded,
        ],
        "data": data_hex,
        "transactionHash": tx_hash,
        "blockNumber": "0x12345",
    }


@pytest.mark.asyncio
async def test_full_settlement_success_with_valid_erc20_transfer_logs():
    """Verify on-chain settlement succeeds when receipt has valid ERC-20 Transfer log."""
    verifier = SettlementVerifier(test_mode=False)
    tx_hash = "0x" + "1" * 64
    seller_pay_to = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
    buyer_addr = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"

    mock_receipt = {
        "status": "0x1",
        "transactionHash": tx_hash,
        "logs": [
            _build_mock_transfer_log(
                token_address=USDC_BASE_SEPOLIA,
                from_address=buyer_addr,
                to_address=seller_pay_to,
                amount_base_units=2000,
                tx_hash=tx_hash,
            )
        ]
    }

    with patch.object(verifier, "_verify_onchain_tx", new=AsyncMock(return_value=(True, mock_receipt))):
        receipt = await verifier.verify_full_settlement(
            proof_header=tx_hash,
            expected_network=NETWORK_BASE_SEPOLIA,
            expected_token=USDC_BASE_SEPOLIA,
            expected_pay_to=seller_pay_to,
            expected_amount_units=2000,
            expected_sender=buyer_addr,
        )

    assert receipt.tx_hash == tx_hash
    assert receipt.settled_amount_units == 2000
    assert receipt.settled_at is not None


@pytest.mark.asyncio
async def test_full_settlement_rejection_on_wrong_network():
    """Verify settlement rejects immediately if network does not match Base Sepolia."""
    verifier = SettlementVerifier(test_mode=False)
    tx_hash = "0x" + "1" * 64

    with pytest.raises(SettlementVerificationError) as exc_info:
        await verifier.verify_full_settlement(
            proof_header=tx_hash,
            expected_network="eip155:1",  # Ethereum Mainnet (forbidden)
            expected_token=USDC_BASE_SEPOLIA,
            expected_pay_to="0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            expected_amount_units=2000,
        )

    assert "expected network 'eip155:84532'" in str(exc_info.value)


@pytest.mark.asyncio
async def test_full_settlement_rejection_on_wrong_token_contract():
    """Verify settlement rejects if transfer event is emitted by wrong token contract."""
    verifier = SettlementVerifier(test_mode=False)
    tx_hash = "0x" + "2" * 64
    seller_pay_to = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
    fake_token = "0x000000000000000000000000000000000000dEaD"

    mock_receipt = {
        "status": "0x1",
        "transactionHash": tx_hash,
        "logs": [
            _build_mock_transfer_log(
                token_address=fake_token,
                from_address="0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
                to_address=seller_pay_to,
                amount_base_units=2000,
                tx_hash=tx_hash,
            )
        ]
    }

    with patch.object(verifier, "_verify_onchain_tx", new=AsyncMock(return_value=(True, mock_receipt))):
        with pytest.raises(SettlementVerificationError) as exc_info:
            await verifier.verify_full_settlement(
                proof_header=tx_hash,
                expected_network=NETWORK_BASE_SEPOLIA,
                expected_token=USDC_BASE_SEPOLIA,
                expected_pay_to=seller_pay_to,
                expected_amount_units=2000,
            )

    assert "No matching ERC-20 Transfer event log found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_full_settlement_rejection_on_wrong_recipient():
    """Verify settlement rejects if payment was sent to someone other than seller payTo."""
    verifier = SettlementVerifier(test_mode=False)
    tx_hash = "0x" + "3" * 64
    expected_seller = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
    attacker_address = "0x999999cf1046e68e36E1aA2E0E07105eDDD1f08E"

    mock_receipt = {
        "status": "0x1",
        "transactionHash": tx_hash,
        "logs": [
            _build_mock_transfer_log(
                token_address=USDC_BASE_SEPOLIA,
                from_address="0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
                to_address=attacker_address,
                amount_base_units=2000,
                tx_hash=tx_hash,
            )
        ]
    }

    with patch.object(verifier, "_verify_onchain_tx", new=AsyncMock(return_value=(True, mock_receipt))):
        with pytest.raises(SettlementVerificationError) as exc_info:
            await verifier.verify_full_settlement(
                proof_header=tx_hash,
                expected_network=NETWORK_BASE_SEPOLIA,
                expected_token=USDC_BASE_SEPOLIA,
                expected_pay_to=expected_seller,
                expected_amount_units=2000,
            )

    assert "No matching ERC-20 Transfer event log found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_full_settlement_rejection_on_wrong_amount():
    """Verify settlement rejects if transfer amount does not match expected integer base units."""
    verifier = SettlementVerifier(test_mode=False)
    tx_hash = "0x" + "4" * 64
    seller_pay_to = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"

    mock_receipt = {
        "status": "0x1",
        "transactionHash": tx_hash,
        "logs": [
            _build_mock_transfer_log(
                token_address=USDC_BASE_SEPOLIA,
                from_address="0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
                to_address=seller_pay_to,
                amount_base_units=1000,  # Underpaid! Expected 2000
                tx_hash=tx_hash,
            )
        ]
    }

    with patch.object(verifier, "_verify_onchain_tx", new=AsyncMock(return_value=(True, mock_receipt))):
        with pytest.raises(SettlementVerificationError) as exc_info:
            await verifier.verify_full_settlement(
                proof_header=tx_hash,
                expected_network=NETWORK_BASE_SEPOLIA,
                expected_token=USDC_BASE_SEPOLIA,
                expected_pay_to=seller_pay_to,
                expected_amount_units=2000,
            )

    assert "ERC-20 Transfer amount mismatch: expected 2000 base units, found 1000" in str(exc_info.value)


@pytest.mark.asyncio
async def test_full_settlement_rejection_on_reverted_receipt_status():
    """Verify settlement rejects if transaction receipt status is 0x0 (reverted)."""
    verifier = SettlementVerifier(test_mode=False)
    tx_hash = "0x" + "5" * 64

    # Status 0x0 = reverted on EVM
    reverted_receipt = {"status": "0x0", "transactionHash": tx_hash, "logs": []}

    with patch.object(verifier, "_verify_onchain_tx", new=AsyncMock(return_value=(False, reverted_receipt))):
        with pytest.raises(SettlementVerificationError) as exc_info:
            await verifier.verify_full_settlement(
                proof_header=tx_hash,
                expected_network=NETWORK_BASE_SEPOLIA,
                expected_token=USDC_BASE_SEPOLIA,
                expected_pay_to="0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
                expected_amount_units=2000,
            )

    assert "unconfirmed or reverted" in str(exc_info.value)


@pytest.mark.asyncio
async def test_full_settlement_rejection_on_missing_event_logs():
    """Verify settlement rejects in live mode if receipt has status 0x1 but zero event logs."""
    verifier = SettlementVerifier(test_mode=False)
    tx_hash = "0x" + "6" * 64

    mock_receipt = {"status": "0x1", "transactionHash": tx_hash, "logs": []}

    with patch.object(verifier, "_verify_onchain_tx", new=AsyncMock(return_value=(True, mock_receipt))):
        with pytest.raises(SettlementVerificationError) as exc_info:
            await verifier.verify_full_settlement(
                proof_header=tx_hash,
                expected_network=NETWORK_BASE_SEPOLIA,
                expected_token=USDC_BASE_SEPOLIA,
                expected_pay_to="0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
                expected_amount_units=2000,
            )

    assert "contains no event logs to verify ERC-20 Transfer" in str(exc_info.value)


def test_seller_payment_verifier_issue_challenge():
    """Verify SellerPaymentVerifier issues compliant x402 requirement challenge."""
    verifier = SellerPaymentVerifier()
    challenge = verifier.issue_challenge(
        service_id="data_001",
        amount_units=2000,
        pay_to="0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
    )

    assert challenge.network == NETWORK_BASE_SEPOLIA
    assert challenge.token == USDC_BASE_SEPOLIA
    assert challenge.amount == "2000"
    assert challenge.payTo == "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
    assert challenge.nonce.startswith("nonce_")


@pytest.mark.asyncio
async def test_seller_payment_verifier_verify_and_settle():
    """Verify SellerPaymentVerifier validates requirement match and mock signature gating."""
    req = PaymentRequirement(
        network=NETWORK_BASE_SEPOLIA,
        token=USDC_BASE_SEPOLIA,
        payTo="0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        amount="2000",
        nonce="nonce_test",
        service_id="data_001",
    )

    # 1. Live mode must reject mock signature
    live_seller_verifier = SellerPaymentVerifier(test_mode=False)
    mock_payload = PaymentPayload(
        authorization={
            "network": req.network,
            "token": req.token,
            "payTo": req.payTo,
            "amount": req.amount,
            "nonce": req.nonce,
        },
        signature="0x_mock_sig_12345",
        buyer_address="0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
    )
    with pytest.raises(SettlementVerificationError) as exc_info:
        await live_seller_verifier.verify_and_settle(mock_payload, req)
    assert "Mock signature rejected in live seller verification" in str(exc_info.value)

    # 2. Test mode allows mock signature
    test_seller_verifier = SellerPaymentVerifier(test_mode=True)
    receipt = await test_seller_verifier.verify_and_settle(mock_payload, req)
    assert receipt.settled_amount_units == 2000
    assert receipt.settled_at is not None


@pytest.mark.asyncio
async def test_full_settlement_rejection_on_wrong_payer():
    """Verify settlement rejects if payment was emitted by someone other than expected buyer."""
    verifier = SettlementVerifier(test_mode=False)
    tx_hash = "0x" + "5" * 64
    seller_pay_to = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
    expected_buyer = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
    other_payer = "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"

    mock_receipt = {
        "status": "0x1",
        "transactionHash": tx_hash,
        "logs": [
            _build_mock_transfer_log(
                token_address=USDC_BASE_SEPOLIA,
                from_address=other_payer,
                to_address=seller_pay_to,
                amount_base_units=2000,
                tx_hash=tx_hash,
            )
        ]
    }

    with patch.object(verifier, "_verify_onchain_tx", new=AsyncMock(return_value=(True, mock_receipt))):
        with pytest.raises(SettlementVerificationError) as exc_info:
            await verifier.verify_full_settlement(
                proof_header=tx_hash,
                expected_network=NETWORK_BASE_SEPOLIA,
                expected_token=USDC_BASE_SEPOLIA,
                expected_pay_to=seller_pay_to,
                expected_amount_units=2000,
                expected_sender=expected_buyer,
            )

    assert "No matching ERC-20 Transfer event log found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_payment_service_live_mode_unverified_proof_transitions_to_suspense():
    """Verify that in live mode, unverified settlement proof transitions to PENDING_RECONCILIATION, never PAID."""
    from backend.payments.service import PaymentService
    from backend.payments.policy import PaymentPolicyVerifier
    from backend.payments.idempotency import IdempotencyStore
    from backend.payments.x402_adapter import X402Adapter
    from backend.shared.schemas import ServiceDefinition, ServiceCategory
    from backend.registry.service_catalog import catalog

    svc_def = ServiceDefinition(
        service_id="test_live_unverified_01",
        name="Test Service",
        category=ServiceCategory.DATA,
        endpoint_url="http://test/data",
        price_usdc="0.002",
        network=NETWORK_BASE_SEPOLIA,
        pay_to="0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        input_schema={},
        output_schema={},
        is_active=True,
    )
    catalog.register_service(svc_def)
    try:
        live_verifier = SettlementVerifier(test_mode=False)
        live_adapter = X402Adapter(test_mode=True)  # allows mock network execute_paid_request
        service = PaymentService(
            policy_verifier=PaymentPolicyVerifier(),
            settlement_verifier=live_verifier,
            adapter=live_adapter,
            store=IdempotencyStore(),
        )
        budget = service.get_or_create_task_budget("task_live_audit", 10_000)

        # Seller returns HTTP 200 with an unconfirmed on-chain hash
        unconfirmed_tx = "0x" + "e" * 64
        with patch.object(
            live_adapter,
            "execute_paid_request",
            new=AsyncMock(return_value=(200, {"data": "test"}, unconfirmed_tx))
        ):
            result = await service.execute_paid_call(
                task_id="task_live_audit",
                call_id="call_audit_01",
                service_id=svc_def.service_id,
                input_payload={},
                idempotency_key="idemp_live_audit_01",
                task_budget_manager=budget,
            )

        # Must be PENDING_RECONCILIATION, NOT PAID!
        assert result.status == PaymentStatus.PENDING_RECONCILIATION
        assert result.error_code == "SETTLEMENT_UNVERIFIED"
        assert budget.reserved_budget == 2000
    finally:
        catalog._services.pop(svc_def.service_id, None)
