"""Payment Engine Schemas and Typed Models for DI-06 (Member 1)."""
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from backend.shared.constants import (
    NETWORK_BASE_SEPOLIA,
    USDC_BASE_SEPOLIA,
    base_units_to_usdc,
    usdc_to_base_units,
)


class PaymentStatus(str, Enum):
    """The five standard payment engine lifecycle statuses."""
    PAID = "paid"
    PAID_OUTPUT_REJECTED = "paid output rejected"
    REFUSED = "refused"
    FAILED_AND_NOT_CHARGED = "failed and not charged"
    PENDING_RECONCILIATION = "pending reconciliation"


class PaidCallRequest(BaseModel):
    """Input contract for execute_paid_call."""
    task_id: str = Field(..., description="Parent task correlation identifier")
    call_id: str = Field(..., description="Unique step call identifier")
    service_id: str = Field(..., description="Target service identifier in catalog")
    input_payload: Dict[str, Any] = Field(default_factory=dict, description="Parameters for seller service")
    idempotency_key: str = Field(..., description="Client-supplied idempotency key")


class PaidCallResult(BaseModel):
    """Typed result contract returned by execute_paid_call."""
    task_id: str = Field(..., description="Parent task correlation identifier")
    call_id: str = Field(..., description="Unique step call identifier")
    service_id: str = Field(..., description="Target service identifier")
    request_id: str = Field(..., description="Unique payment request identifier (req_*)")
    status: PaymentStatus = Field(..., description="Terminal or suspense payment status")
    amount_base_units: int = Field(default=0, description="Amount charged in integer token atomic units (1 USDC = 1,000,000)")
    amount_usdc: str = Field(default="0.000000", description="Decimal string representation of amount")
    token_address: str = Field(default=USDC_BASE_SEPOLIA, description="Settlement token contract address")
    network: str = Field(default=NETWORK_BASE_SEPOLIA, description="CAIP-2 network identifier")
    seller_recipient: str = Field(..., description="Recipient wallet address (payTo)")
    tx_hash: Optional[str] = Field(default=None, description="Base Sepolia on-chain transaction hash")
    settlement_proof: Optional[str] = Field(default=None, description="Facilitator receipt ID or cryptographic proof")
    seller_output: Optional[Dict[str, Any]] = Field(default=None, description="Verified output from seller endpoint")
    latency_ms: float = Field(default=0.0, description="Total call latency in milliseconds")
    error_code: Optional[str] = Field(default=None, description="Standard machine-readable error code if failed")
    error_message: Optional[str] = Field(default=None, description="Sanitized diagnostic error explanation")
    settled_at: Optional[datetime] = Field(default=None, description="Timestamp of confirmed settlement")


class PaymentAttemptRecord(BaseModel):
    """Durable record tracking a single payment attempt."""
    attempt_id: str
    task_id: str
    call_id: str
    service_id: str
    idempotency_key: str
    request_hash: str
    amount_base_units: int
    pay_to: str
    nonce: Optional[str] = None
    status: PaymentStatus
    tx_hash: Optional[str] = None
    settlement_proof: Optional[str] = None
    error_reason: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BudgetReservationRecord(BaseModel):
    """Record tracking an active hold against a task budget."""
    reservation_id: str
    task_id: str
    amount_base_units: int
    status: str = Field(default="reserved")  # reserved, committed, released
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
