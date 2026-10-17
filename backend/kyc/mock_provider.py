"""Deterministic Mock KYC Provider for Local Development and Testing."""
import hashlib
import hmac
import secrets
from typing import Dict, Any

from backend.shared.config import get_settings
from backend.shared.constants import KycStatus
from .interfaces import KycAdapterInterface

settings = get_settings()


class MockKycProvider(KycAdapterInterface):
    """Deterministic, provider-neutral mock KYC adapter.
    Explicitly labeled as SIMULATED for development and testing.
    """

    @property
    def provider_name(self) -> str:
        return "mock_simulated"

    @property
    def is_simulated(self) -> bool:
        return True

    def create_verification_session(self, user_id: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Create a simulated hosted identity-document verification session."""
        reference_id = f"mock_kyc_{secrets.token_hex(12)}"
        session_url = f"{settings.vite_api_base_url}/kyc/hosted-session/{reference_id}"

        return {
            "provider_reference_id": reference_id,
            "session_url": session_url,
            "initial_status": KycStatus.PENDING.value,
            "is_simulated": True,
            "disclaimer": "SIMULATED - NOT REAL-WORLD IDENTITY VERIFICATION",
        }

    def verify_webhook_signature(self, raw_body: bytes, signature_header: str) -> bool:
        """Verify HMAC-SHA256 signature on incoming provider webhook."""
        if not signature_header:
            return False
        secret = settings.kyc_webhook_secret.encode("utf-8")
        expected_sig = hmac.new(secret, raw_body, hashlib.sha256).hexdigest()
        # Clean prefix if format is sha256=...
        cleaned_sig = signature_header.replace("sha256=", "").strip()
        return hmac.compare_digest(expected_sig, cleaned_sig)

    def sign_payload(self, raw_body: bytes) -> str:
        """Helper to generate valid HMAC signature for mock webhooks and tests."""
        secret = settings.kyc_webhook_secret.encode("utf-8")
        return f"sha256={hmac.new(secret, raw_body, hashlib.sha256).hexdigest()}"

    def parse_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Parse normalized webhook payload."""
        return {
            "provider_reference_id": payload.get("provider_reference_id"),
            "user_id": payload.get("user_id"),
            "new_status": payload.get("decision"),
            "reason": payload.get("reason", "Simulated mock provider decision"),
        }
