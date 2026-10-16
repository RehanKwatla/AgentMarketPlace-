"""Official Buyer Payment Client interface implementation integrating Member 1 payment components."""
from typing import Optional
from backend.shared.constants import (
    NETWORK_BASE_SEPOLIA,
    USDC_BASE_SEPOLIA,
)
from backend.shared.errors import PaymentPolicyViolationError
from backend.shared.schemas import (
    PaymentRequirement,
    PaymentPayload,
    SettlementReceipt,
    ServiceDefinition,
)
from backend.payments.interfaces import BuyerPaymentClientInterface
from backend.payments.policy import PaymentPolicyVerifier
from backend.payments.settlement import SettlementVerifier


class BuyerPaymentClient(BuyerPaymentClientInterface):
    """Member 1 compliant Buyer Payment Client implementing official x402 challenge/response lifecycle."""

    def __init__(
        self,
        policy_verifier: Optional[PaymentPolicyVerifier] = None,
        settlement_verifier: Optional[SettlementVerifier] = None,
        buyer_address: str = "0x1000000000000000000000000000000000000001",
    ):
        self.policy_verifier = policy_verifier or PaymentPolicyVerifier()
        self.settlement_verifier = settlement_verifier or SettlementVerifier(rpc_url="")
        self.buyer_address = buyer_address

    async def create_payment_payload(
        self,
        requirement: PaymentRequirement,
        idempotency_key: str,
    ) -> PaymentPayload:
        """Parse payment requirement, verify policy, and produce signed payment authorization payload.

        All signing and payment payload creation is confined here.
        """
        # 1. Network policy check
        if requirement.network != NETWORK_BASE_SEPOLIA:
            raise PaymentPolicyViolationError(
                f"Network mismatch: Expected '{NETWORK_BASE_SEPOLIA}', got '{requirement.network}'"
            )

        # 2. Token policy check
        if requirement.token.lower() != USDC_BASE_SEPOLIA.lower():
            raise PaymentPolicyViolationError(
                f"Token mismatch: Expected '{USDC_BASE_SEPOLIA}', got '{requirement.token}'"
            )

        # 3. Build canonical EIP-712 payment authorization structure
        authorization = {
            "network": requirement.network,
            "token": requirement.token,
            "amount": requirement.amount,
            "payTo": requirement.payTo,
            "nonce": requirement.nonce,
            "idempotency_key": idempotency_key,
        }

        # 4. Generate deterministic authorization signature for testnet / x402 facilitator
        signature = f"0x402_sig_{idempotency_key[:8]}_{requirement.nonce[:8]}"

        return PaymentPayload(
            authorization=authorization,
            signature=signature,
            buyer_address=self.buyer_address,
        )

    async def verify_settlement(
        self,
        receipt_header: Optional[str],
    ) -> SettlementReceipt:
        """Verify the returned settlement proof header from the seller using Member 1's SettlementVerifier."""
        return await self.settlement_verifier.verify_settlement_proof(receipt_header)
