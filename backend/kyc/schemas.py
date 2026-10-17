"""Pydantic Schemas for Provider-Neutral KYC Module."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from backend.shared.constants import KycStatus


class KycInitiateRequest(BaseModel):
    country: Optional[str] = "US"
    account_type: Optional[str] = "individual"  # "individual", "business"
    intended_use: Optional[str] = None


class KycSessionResponse(BaseModel):
    status: KycStatus
    provider: str
    provider_reference_id: str
    session_url: str
    is_simulated: bool = True
    disclaimer: str = "SIMULATED - NOT REAL-WORLD IDENTITY VERIFICATION"


class KycAuditEntry(BaseModel):
    id: str
    from_status: str
    to_status: str
    provider: str
    provider_reference_id: Optional[str]
    reason: Optional[str]
    timestamp: datetime


class KycStatusResponse(BaseModel):
    user_id: str
    status: KycStatus
    provider: str
    provider_reference_id: Optional[str] = None
    is_simulated: bool = True
    simulation_disclaimer: str
    rejection_reasons: Optional[str] = None
    session_url: Optional[str] = None
    verified_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    audit_history: List[KycAuditEntry] = []


class KycWebhookPayload(BaseModel):
    event_id: str
    provider_reference_id: str
    user_id: str
    decision: KycStatus
    reason: Optional[str] = None
    timestamp: int
