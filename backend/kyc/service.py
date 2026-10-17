"""KYC Lifecycle Service for Transitions, Webhook Verification, and Audit Logging."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.orm import Session

from backend.database.models import KycRecordModel, KycAuditModel, UserModel
from backend.shared.constants import KycStatus
from backend.shared.errors import (
    KycWebhookVerificationFailedError,
    KycUnauthorizedUpdateError,
    AgentEconomyBaseException,
)
from .interfaces import validate_kyc_transition, KycAdapterInterface
from .mock_provider import MockKycProvider

# Active adapter (Provider-neutral architecture: can swap with Persona/SumSub)
_active_provider: KycAdapterInterface = MockKycProvider()


def get_kyc_adapter() -> KycAdapterInterface:
    """Return configured KYC provider adapter."""
    return _active_provider


class KycService:
    """Manages identity verification sessions, status transitions, and audit trails."""

    @staticmethod
    def get_or_create_record(db: Session, user_id: str) -> KycRecordModel:
        """Fetch existing KYC record or initialize default NOT_STARTED record."""
        record = db.query(KycRecordModel).filter(KycRecordModel.user_id == user_id).first()
        if not record:
            record = KycRecordModel(
                user_id=user_id,
                status=KycStatus.NOT_STARTED.value,
                provider=_active_provider.provider_name,
                is_simulated=_active_provider.is_simulated,
                simulation_disclaimer="SIMULATED - NOT REAL-WORLD IDENTITY VERIFICATION",
                created_at=datetime.now(timezone.utc),
            )
            db.add(record)
            db.commit()
            db.refresh(record)
        return record

    @staticmethod
    def initiate_session(db: Session, user_id: str, metadata: Dict[str, Any]) -> Tuple[KycRecordModel, str]:
        """Initiate identity verification session. Transitions from NOT_STARTED/REJECTED/EXPIRED to PENDING."""
        record = KycService.get_or_create_record(db, user_id)

        # Validate transition to PENDING
        validate_kyc_transition(record.status, KycStatus.PENDING.value)

        # Create session via adapter
        session_info = _active_provider.create_verification_session(user_id, metadata)
        previous_status = record.status
        now = datetime.now(timezone.utc)

        record.status = KycStatus.PENDING.value
        record.provider = _active_provider.provider_name
        record.provider_reference_id = session_info["provider_reference_id"]
        record.session_url = session_info["session_url"]
        record.is_simulated = _active_provider.is_simulated
        record.simulation_disclaimer = session_info.get(
            "disclaimer", "SIMULATED - NOT REAL-WORLD IDENTITY VERIFICATION"
        )
        record.rejection_reasons = None

        # Record audit log entry
        audit = KycAuditModel(
            id=f"aud_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            from_status=previous_status,
            to_status=KycStatus.PENDING.value,
            provider=_active_provider.provider_name,
            provider_reference_id=record.provider_reference_id,
            reason="User initiated identity verification session",
            timestamp=now,
        )
        db.add(audit)
        db.commit()
        db.refresh(record)
        return record, session_info["session_url"]

    @staticmethod
    def process_provider_webhook(
        db: Session,
        raw_body: bytes,
        signature_header: str,
        payload: Dict[str, Any]
    ) -> KycRecordModel:
        """Process incoming provider webhook with cryptographic signature validation.
        Prevents unauthorized status updates.
        """
        # 1. Cryptographic HMAC verification
        if not _active_provider.verify_webhook_signature(raw_body, signature_header):
            raise KycWebhookVerificationFailedError(
                "Invalid webhook signature. Webhook rejected for security."
            )

        # 2. Parse payload
        parsed = _active_provider.parse_webhook(payload)
        user_id = parsed["user_id"]
        target_status = parsed["new_status"]
        if hasattr(target_status, "value"):
            target_status = target_status.value
        reason = parsed.get("reason", "Provider verification decision")

        # 3. Fetch record
        record = db.query(KycRecordModel).filter(KycRecordModel.user_id == user_id).first()
        if not record:
            raise AgentEconomyBaseException(f"KYC record for user '{user_id}' not found.", error_code="KYC_RECORD_NOT_FOUND")

        # 4. Enforce state machine transition
        validate_kyc_transition(record.status, target_status)

        previous_status = record.status
        now = datetime.now(timezone.utc)
        record.status = target_status

        if target_status == KycStatus.VERIFIED.value:
            record.verified_at = now
            record.expires_at = now + timedelta(days=365)  # 1 year validity
            record.rejection_reasons = None
        elif target_status in [KycStatus.REJECTED.value, KycStatus.REQUIRES_REVIEW.value]:
            record.rejection_reasons = reason

        # 5. Audit trail
        audit = KycAuditModel(
            id=f"aud_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            from_status=previous_status,
            to_status=target_status,
            provider=record.provider,
            provider_reference_id=record.provider_reference_id,
            reason=reason,
            timestamp=now,
        )
        db.add(audit)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def get_audit_history(db: Session, user_id: str) -> List[KycAuditModel]:
        """Fetch chronological audit history for user's KYC lifecycle."""
        return db.query(KycAuditModel).filter(
            KycAuditModel.user_id == user_id
        ).order_by(KycAuditModel.timestamp.desc()).all()
