"""Pydantic Models and Shared Schemas for DI-06 Agent Economy."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator
from .constants import (
    NETWORK_BASE_SEPOLIA,
    USDC_BASE_SEPOLIA,
    LedgerStatus,
    ServiceCategory,
    usdc_to_base_units,
)


class HealthResponse(BaseModel):
    status: str = Field(default="healthy")
    version: str = Field(default="0.1.0")
    network: str = Field(default=NETWORK_BASE_SEPOLIA)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    services: Dict[str, str] = Field(default_factory=dict)


# ==============================================================================
# Payment Protocol Schemas (x402 v2)
# ==============================================================================

class PaymentRequirement(BaseModel):
    """Specification emitted by seller in X-402-Requirement header."""
    version: str = Field(default="2.0", description="Protocol version")
    network: str = Field(default=NETWORK_BASE_SEPOLIA, description="CAIP-2 network string")
    token: str = Field(default=USDC_BASE_SEPOLIA, description="USDC contract address")
    amount: str = Field(..., description="Integer amount in base units as string")
    payTo: str = Field(..., description="Registered seller recipient address")
    nonce: str = Field(..., description="Server-issued replay-prevention nonce")
    service_id: str = Field(..., description="Target service identifier")


class PaymentPayload(BaseModel):
    """Payload sent by buyer in X-402-Payment-Payload header."""
    authorization: Dict[str, Any] = Field(..., description="EIP-712 payment authorization parameters")
    signature: str = Field(..., description="Hex-encoded ECDSA signature")
    buyer_address: str = Field(..., description="Buyer wallet address")


class SettlementReceipt(BaseModel):
    """Settlement proof returned in X-402-Settlement-Proof header."""
    tx_hash: Optional[str] = Field(default=None, description="On-chain Base Sepolia transaction hash")
    facilitator_receipt_id: Optional[str] = Field(default=None)
    settled_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    settled_amount_units: int = Field(default=0)


# ==============================================================================
# Service Registry Schemas
# ==============================================================================

class CapabilityMetadata(BaseModel):
    """Detailed capability profile, SLA guarantees, and execution constraints."""
    version: str = Field(default="1.0.0", description="Capability schema semantic version")
    tags: List[str] = Field(default_factory=list, description="Searchable domain tags")
    supported_formats: List[str] = Field(default_factory=list, description="Supported MIME or content formats")
    max_payload_bytes: Optional[int] = Field(default=None, description="Max input payload size in bytes")
    rate_limit_per_minute: Optional[int] = Field(default=None, description="Max allowed requests per minute")
    sla_latency_p95_ms: Optional[int] = Field(default=None, description="Service level agreement p95 latency target")
    deterministic: bool = Field(default=True, description="Whether output is idempotent and deterministic")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary service-specific execution constraints")


class ServiceDefinition(BaseModel):
    service_id: str = Field(..., description="Unique service slug, e.g. data_001")
    name: str = Field(..., description="Human-readable service title")
    category: ServiceCategory = Field(..., description="Category: data, scraping, inference")
    endpoint_url: str = Field(..., description="HTTP endpoint URL for service calls")
    price_usdc: str = Field(..., description="Decimal USDC price, e.g. '0.002'")
    price_base_units: int = Field(default=0, description="Price in base units (computed)")
    network: str = Field(default=NETWORK_BASE_SEPOLIA)
    pay_to: str = Field(..., description="Registered recipient wallet address")
    description: str = Field(default="")
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = Field(default=True)
    capability_metadata: Optional[CapabilityMetadata] = Field(
        default=None,
        description="Detailed capability profile and execution constraints",
    )

    @model_validator(mode="after")
    def populate_base_units(self) -> "ServiceDefinition":
        if self.price_usdc and (self.price_base_units is None or self.price_base_units == 0):
            self.price_base_units = usdc_to_base_units(self.price_usdc)
        return self


class ServiceListResponse(BaseModel):
    services: List[ServiceDefinition]
    total: int


# ==============================================================================
# Buyer Agent Task Schemas
# ==============================================================================

class TaskRequest(BaseModel):
    task: str = Field(..., min_length=3, description="Natural language objective")
    budget_usdc: str = Field(..., description="Total budget allocated in decimal USDC")


class ExecutionStep(BaseModel):
    step: int
    service_id: str
    request_id: str
    price_paid_usdc: str
    tx_hash: Optional[str] = None
    status: LedgerStatus
    latency_ms: float
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class TaskResponse(BaseModel):
    task_id: str
    status: str
    budget_allocated_usdc: str
    total_cost_usdc: str
    cost_explanation: str
    selected_services: List[str]
    executions: List[ExecutionStep]
    final_result: Optional[str] = None
    errors_and_fallbacks: List[str] = Field(default_factory=list)


# ==============================================================================
# Ledger & Reputation Schemas
# ==============================================================================

class LedgerRecordSchema(BaseModel):
    request_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    buyer_id: str
    seller_id: str
    service_id: str
    listed_price: str
    amount_paid: str
    tx_hash: Optional[str] = None
    status: LedgerStatus
    latency_ms: float
    error_reason: Optional[str] = None
    task_id: Optional[str] = None
    payment_id: Optional[str] = None
    amount_paid_units: Optional[int] = None
    listed_price_units: Optional[int] = None
    network: Optional[str] = NETWORK_BASE_SEPOLIA
    token: Optional[str] = USDC_BASE_SEPOLIA

    @model_validator(mode="after")
    def populate_units(self) -> "LedgerRecordSchema":
        if self.amount_paid and self.amount_paid_units is None:
            try:
                self.amount_paid_units = usdc_to_base_units(self.amount_paid)
            except Exception:
                pass
        if self.listed_price and self.listed_price_units is None:
            try:
                self.listed_price_units = usdc_to_base_units(self.listed_price)
            except Exception:
                pass
        return self


class LedgerListResponse(BaseModel):
    total: int
    records: List[LedgerRecordSchema]


class ReputationMetrics(BaseModel):
    service_id: str
    total_calls: int = 0
    successful_calls: int = 0
    success_rate: float = 0.0
    median_latency_ms: float = 0.0
    failure_counts: int = 0
    schema_invalid_counts: int = 0
    listed_price_usdc: str = "0.000000"
    reputation_score: float = 100.0
    total_volume_units: int = 0
    total_volume_usdc: str = "0.000000"


class PaymentReconciliationInput(BaseModel):
    request_id: str
    service_id: str
    buyer_id: str
    seller_id: str
    amount_paid_units: int
    listed_price_units: int
    proof_header: Optional[str] = None
    tx_hash: Optional[str] = None
    settlement_receipt: Optional[SettlementReceipt] = None
    network: str = NETWORK_BASE_SEPOLIA
    token: str = USDC_BASE_SEPOLIA
    task_id: Optional[str] = None
    latency_ms: float = 0.0
    output_valid: bool = True
    error_reason: Optional[str] = None


class ReconciliationResult(BaseModel):
    request_id: str
    status: LedgerStatus
    reconciled: bool
    is_duplicate: bool = False
    ledger_record: Optional[LedgerRecordSchema] = None
    reputation_updated: bool = False
    reputation_repair_needed: bool = False
    message: str = ""

