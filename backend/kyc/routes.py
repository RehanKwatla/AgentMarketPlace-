"""FastAPI Router for Provider-Neutral KYC Lifecycle."""
import json
import time
from typing import Optional
from fastapi import APIRouter, Depends, Header, Request, status, HTTPException
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.database.models import UserModel
from backend.auth.policy import get_current_user
from backend.shared.constants import KycStatus
from .schemas import (
    KycInitiateRequest,
    KycSessionResponse,
    KycStatusResponse,
    KycAuditEntry,
    KycWebhookPayload,
)
from .service import KycService, get_kyc_adapter
from .mock_provider import MockKycProvider

router = APIRouter(prefix="/api/v1/kyc", tags=["KYC Verification"])


@router.get("/status", response_model=KycStatusResponse)
async def get_kyc_status(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve the current user's KYC verification status, simulation badges, and audit history."""
    record = KycService.get_or_create_record(db, current_user.id)
    history = KycService.get_audit_history(db, current_user.id)

    audit_entries = [
        KycAuditEntry(
            id=entry.id,
            from_status=entry.from_status,
            to_status=entry.to_status,
            provider=entry.provider,
            provider_reference_id=entry.provider_reference_id,
            reason=entry.reason,
            timestamp=entry.timestamp,
        )
        for entry in history
    ]

    return KycStatusResponse(
        user_id=record.user_id,
        status=KycStatus(record.status),
        provider=record.provider,
        provider_reference_id=record.provider_reference_id,
        is_simulated=record.is_simulated,
        simulation_disclaimer=record.simulation_disclaimer,
        rejection_reasons=record.rejection_reasons,
        session_url=record.session_url,
        verified_at=record.verified_at,
        expires_at=record.expires_at,
        audit_history=audit_entries,
    )


@router.post("/initiate", response_model=KycSessionResponse)
async def initiate_kyc_session(
    payload: KycInitiateRequest,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Initiate a provider-neutral hosted identity verification session."""
    record, session_url = KycService.initiate_session(
        db, current_user.id, payload.model_dump()
    )
    return KycSessionResponse(
        status=KycStatus(record.status),
        provider=record.provider,
        provider_reference_id=record.provider_reference_id or "",
        session_url=session_url,
        is_simulated=record.is_simulated,
        disclaimer=record.simulation_disclaimer,
    )


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def process_kyc_webhook(
    request: Request,
    x_kyc_signature: Optional[str] = Header(None, alias="X-KYC-Signature"),
    db: Session = Depends(get_db)
):
    """Webhook listener for provider identity decisions.
    Requires cryptographic HMAC verification. Direct client updates are forbidden.
    """
    body_bytes = await request.body()
    if not x_kyc_signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required X-KYC-Signature header."
        )

    try:
        payload = json.loads(body_bytes.decode("utf-8"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload in webhook body."
        )

    updated_record = KycService.process_provider_webhook(
        db=db,
        raw_body=body_bytes,
        signature_header=x_kyc_signature,
        payload=payload
    )

    return {
        "status": "processed",
        "user_id": updated_record.user_id,
        "new_status": updated_record.status,
        "is_simulated": updated_record.is_simulated,
    }


@router.post("/mock-decision")
async def trigger_mock_decision(
    payload: KycWebhookPayload,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Development simulator endpoint: creates and cryptographically signs a mock provider decision.
    Only permitted in mock mode.
    """
    adapter = get_kyc_adapter()
    if not adapter.is_simulated or not isinstance(adapter, MockKycProvider):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Mock decision endpoint is only available when mock provider is active."
        )

    # Use current_user.id if user_id in payload is empty or "me"
    target_user_id = payload.user_id if payload.user_id and payload.user_id != "me" else current_user.id
    record = KycService.get_or_create_record(db, target_user_id)

    raw_data = {
        "event_id": payload.event_id or f"evt_{int(time.time())}",
        "provider_reference_id": record.provider_reference_id or f"mock_ref_{target_user_id}",
        "user_id": target_user_id,
        "decision": payload.decision.value if hasattr(payload.decision, "value") else str(payload.decision),
        "reason": payload.reason or "Simulated test decision",
        "timestamp": int(time.time()),
    }
    raw_body = json.dumps(raw_data).encode("utf-8")
    sig = adapter.sign_payload(raw_body)

    updated_record = KycService.process_provider_webhook(
        db=db,
        raw_body=raw_body,
        signature_header=sig,
        payload=raw_data
    )

    return {
        "message": "Mock KYC decision processed successfully [SIMULATED]",
        "user_id": updated_record.user_id,
        "status": updated_record.status,
        "is_simulated": True,
        "disclaimer": updated_record.simulation_disclaimer,
    }
