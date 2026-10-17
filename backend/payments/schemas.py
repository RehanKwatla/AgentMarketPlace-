"""Payment Engine Schemas and Typed Models for DI-06 (Member 1)."""
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
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


class MultiHopStep(BaseModel):
    """Specification of a single step in a multi-hop execution route."""
    step_id: int = Field(..., description="1-indexed step identifier")
    service_id: str = Field(..., description="Target service identifier in catalog")
    input_payload: Dict[str, Any] = Field(default_factory=dict, description="Parameters for seller service")
    depends_on: List[int] = Field(default_factory=list, description="Step IDs that must complete before this step")
    input_transform: Optional[Dict[str, str]] = Field(
        default=None,
        description="Optional field mapping from upstream step outputs: {'target_field': 'step_{id}.output_field'}"
    )


class MultiHopRouteResult(BaseModel):
    """Result of an autonomous multi-hop paid orchestration."""
    task_id: str = Field(..., description="Parent task correlation identifier")
    status: str = Field(..., description="Route completion status: 'completed', 'partial_failure', 'refused', 'failed', 'pending_reconciliation'")
    total_hops: int = Field(default=0, description="Total planned hops in route")
    executed_hops: int = Field(default=0, description="Total executed hops")
    successful_hops: int = Field(default=0, description="Hops that succeeded with verified payment")
    total_cost_base_units: int = Field(default=0, description="Total atomic units charged across all hops")
    total_cost_usdc: str = Field(default="0.000000", description="Total USDC charged across all hops")
    budget_allocated_usdc: str = Field(default="0.000000", description="Allocated budget for the entire route")
    remaining_budget_usdc: str = Field(default="0.000000", description="Unspent budget returned/available")
    steps: List[PaidCallResult] = Field(default_factory=list, description="Ordered results for each executed step")
    final_output: Optional[Dict[str, Any]] = Field(default=None, description="Output from the terminal step if completed")
    error_step_id: Optional[int] = Field(default=None, description="Step ID where failure occurred, if any")
    error_message: Optional[str] = Field(default=None, description="Reason for route failure")
    reconciliation_needed: bool = Field(default=False, description="Whether any hop was left in pending reconciliation")
    latency_ms: float = Field(default=0.0, description="Total route execution latency in milliseconds")


class MultiHopRouteRequest(BaseModel):
    """Input payload for multi-hop route execution."""
    task_id: Optional[str] = Field(default=None, description="Optional parent task correlation identifier")
    steps: List[MultiHopStep] = Field(..., description="Ordered list of steps to execute in sequence or DAG")
    max_budget_usdc: float = Field(default=1.0, description="Maximum budget allocated in USDC for the entire route")


class SettlementClassificationSummary(BaseModel):
    """Authoritative breakdown of settlement evidence certainty (strictly distinguishing on-chain from local authorization)."""
    confirmed_on_chain: int = Field(default=0, description="Settlements confirmed via live RPC receipt and matching Transfer log")
    local_authorization: int = Field(default=0, description="Local authorization receipts (rec_auth_*) awaiting on-chain broadcast")
    unverified_hash: int = Field(default=0, description="Records with transaction hash but unconfirmed on-chain receipt")
    pending_reconciliation: int = Field(default=0, description="Records held in suspense awaiting authoritative reconciliation")
    failed_or_not_charged: int = Field(default=0, description="Calls refused, failed, or budget released without charge")


class PaymentDashboardSummary(BaseModel):
    """Authoritative dashboard metrics payload for DI-06."""
    network: str = Field(default=NETWORK_BASE_SEPOLIA, description="CAIP-2 Network identifier")
    token_address: str = Field(default=USDC_BASE_SEPOLIA, description="USDC contract address")
    total_tasks: int = Field(default=0, description="Total unique task runs recorded")
    total_paid_calls: int = Field(default=0, description="Total individual paid calls attempted or executed")
    total_spend_usdc: str = Field(default="0.000000", description="Total authorized or settled USDC spend")
    total_spend_base_units: int = Field(default=0, description="Total spend in atomic base units")
    status_breakdown: Dict[str, int] = Field(default_factory=dict, description="Counts by PaymentStatus / LedgerStatus")
    settlement_evidence: SettlementClassificationSummary = Field(
        default_factory=SettlementClassificationSummary,
        description="Detailed breakdown of settlement evidence certainty"
    )
    services_count: int = Field(default=0, description="Number of registered seller services")
    pending_reconciliations_count: int = Field(default=0, description="Number of attempts currently held in suspense")
    recent_transactions: List[Dict[str, Any]] = Field(default_factory=list, description="Recent ledger transactions with explicit evidence flags")
