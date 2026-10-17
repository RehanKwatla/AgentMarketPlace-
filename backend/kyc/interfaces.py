"""Provider-Neutral KYC Adapter Interface and State Machine Definition."""
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from backend.shared.constants import KycStatus
from backend.shared.errors import KycTransitionInvalidError

# Strict allowed transitions for KYC lifecycle
ALLOWED_KYC_TRANSITIONS: Dict[str, List[str]] = {
    KycStatus.NOT_STARTED.value: [KycStatus.PENDING.value],
    KycStatus.PENDING.value: [
        KycStatus.VERIFIED.value,
        KycStatus.REJECTED.value,
        KycStatus.REQUIRES_REVIEW.value,
    ],
    KycStatus.REQUIRES_REVIEW.value: [
        KycStatus.VERIFIED.value,
        KycStatus.REJECTED.value,
    ],
    KycStatus.VERIFIED.value: [
        KycStatus.EXPIRED.value,
        KycStatus.REQUIRES_REVIEW.value,
    ],
    KycStatus.REJECTED.value: [KycStatus.PENDING.value],  # Reverification
    KycStatus.EXPIRED.value: [KycStatus.PENDING.value],   # Reverification
}


def validate_kyc_transition(from_status: str, to_status: str) -> None:
    """Validate whether transitioning between two KYC statuses is permitted.
    Raises KycTransitionInvalidError if illegal.
    """
    allowed = ALLOWED_KYC_TRANSITIONS.get(from_status, [])
    if to_status not in allowed:
        raise KycTransitionInvalidError(from_status=from_status, to_status=to_status)


class KycAdapterInterface(ABC):
    """Abstract interface that all KYC providers (mock, Persona, SumSub, Stripe Identity) must implement."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of this provider adapter."""
        pass

    @property
    @abstractmethod
    def is_simulated(self) -> bool:
        """Whether this provider runs mock/simulated checks for development."""
        pass

    @abstractmethod
    def create_verification_session(self, user_id: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Create a hosted identity-document capture session URL.
        Returns dict with session_url, provider_reference_id, and initial_status.
        """
        pass

    @abstractmethod
    def verify_webhook_signature(self, raw_body: bytes, signature_header: str) -> bool:
        """Verify the cryptographic HMAC or signature on incoming provider webhooks."""
        pass

    @abstractmethod
    def parse_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Parse provider webhook payload into normalized dict:
        { "provider_reference_id": str, "user_id": str, "new_status": KycStatus, "reason": str }
        """
        pass
