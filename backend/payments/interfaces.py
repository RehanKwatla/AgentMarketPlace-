"""[DEFINED INTERFACE] Abstract Base Classes for Buyer & Seller Payment Lifecycle."""
from abc import ABC, abstractmethod
from typing import Optional
from backend.shared.schemas import PaymentRequirement, PaymentPayload, SettlementReceipt


class BuyerPaymentClientInterface(ABC):
    """Client interface used by Buyer Agent to handle x402 payment challenges."""

    @abstractmethod
    async def create_payment_payload(
        self,
        requirement: PaymentRequirement,
        idempotency_key: str
    ) -> PaymentPayload:
        """Parse payment requirement, verify policy, reserve budget, and sign payment authorization."""
        pass

    @abstractmethod
    async def verify_settlement(
        self,
        receipt_header: Optional[str]
    ) -> SettlementReceipt:
        """Verify the returned settlement proof from the seller."""
        pass


class SellerPaymentVerifierInterface(ABC):
    """Verifier interface used by Seller Agents to challenge and settle payments."""

    @abstractmethod
    def issue_challenge(
        self,
        service_id: str,
        amount_units: int,
        pay_to: str
    ) -> PaymentRequirement:
        """Issue an HTTP 402 payment requirement challenge with a unique nonce."""
        pass

    @abstractmethod
    async def verify_and_settle(
        self,
        payload: PaymentPayload,
        requirement: PaymentRequirement
    ) -> SettlementReceipt:
        """Verify the signed payment payload with the x402 facilitator and settle on-chain."""
        pass
