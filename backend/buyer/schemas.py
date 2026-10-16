"""Buyer Subsystem Schemas matching API_CONTRACTS.md and Master Plan."""
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator
from backend.shared.constants import (
    ServiceCategory,
    usdc_to_base_units,
    base_units_to_usdc,
)


class TaskStatus(str, Enum):
    QUEUED = "queued"
    PLANNING = "planning"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    REFUSED = "refused"
    CANCELLED = "cancelled"


class CallStatus(str, Enum):
    CREATED = "created"
    AWAITING_PAYMENT = "awaiting_payment"
    EXECUTING = "executing"
    VALIDATING_OUTPUT = "validating_output"
    SUCCEEDED = "succeeded"
    PAID_OUTPUT_REJECTED = "paid_output_rejected"
    REFUSED = "refused"
    FAILED_AND_NOT_CHARGED = "failed_and_not_charged"
    PENDING_RECONCILIATION = "pending_reconciliation"


class TaskCreationRequest(BaseModel):
    task: Optional[str] = Field(default=None, description="Natural language task prompt")
    description: Optional[str] = Field(default=None, description="Alias for task prompt")
    budget_usdc: Optional[str] = Field(default=None, description="Explicit spending budget in decimal USDC (e.g. '0.050000')")
    max_budget_atomic: Optional[int] = Field(default=None, description="Spending budget in atomic units (6 decimals)")
    max_concurrency: int = Field(default=3, ge=1, le=10, description="Max parallel service calls (>=3 supported)")
    preferred_categories: Optional[List[ServiceCategory]] = Field(default=None)
    required_categories: Optional[List[str]] = Field(default=None)
    require_all_categories: bool = Field(default=False)

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Resolve task / description
            if not data.get("task") and data.get("description"):
                data["task"] = data["description"]
            elif not data.get("description") and data.get("task"):
                data["description"] = data["task"]

            # Validate prompt presence
            prompt = data.get("task")
            if not prompt or len(str(prompt).strip()) < 3:
                raise ValueError("Task description must be at least 3 characters.")

            # Resolve budget
            atomic = data.get("max_budget_atomic")
            usdc = data.get("budget_usdc")
            if atomic is not None:
                if atomic <= 0:
                    raise ValueError("max_budget_atomic must be strictly positive (> 0).")
                if not usdc:
                    data["budget_usdc"] = base_units_to_usdc(atomic)
            elif usdc is not None:
                units = usdc_to_base_units(str(usdc))
                if units <= 0:
                    raise ValueError("budget_usdc must be strictly positive (> 0).")
                data["max_budget_atomic"] = units
            else:
                raise ValueError("Must provide either budget_usdc or max_budget_atomic.")

            # Resolve categories
            if data.get("required_categories") and not data.get("preferred_categories"):
                cats = []
                for c in data["required_categories"]:
                    clean = str(c).strip().lower()
                    if clean in ServiceCategory._value2member_map_:
                        cats.append(ServiceCategory(clean))
                data["preferred_categories"] = cats

        return data



class ServiceCallRecord(BaseModel):
    call_id: str
    service_id: str
    category: ServiceCategory
    status: CallStatus = CallStatus.CREATED
    listed_price_usdc: str
    amount_paid_usdc: str = "0.000000"
    latency_ms: float = 0.0
    transaction_hash: Optional[str] = None
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    validation_status: str = "unvalidated"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ServiceSelectionReason(BaseModel):
    service_id: str
    category: str
    reason: str
    listed_price_usdc: str
    amount_paid_usdc: str


class PurchaseExplanation(BaseModel):
    task_interpretation: str
    selected_services: List[ServiceSelectionReason] = Field(default_factory=list)
    outputs_accepted: List[str] = Field(default_factory=list)
    outputs_rejected: List[str] = Field(default_factory=list)
    fallback_attempts: List[str] = Field(default_factory=list)
    verified_total_spend_usdc: str = "0.000000"
    remaining_budget_usdc: str = "0.000000"
    transaction_references: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class TaskCreationResponse(BaseModel):
    task_id: str
    status: TaskStatus
    budget_usdc: str
    reserved_usdc: str = "0.000000"
    spent_usdc: str = "0.000000"
    max_concurrency: int = 3
    created_at: str
    status_url: str


class TaskDetailResponse(BaseModel):
    task_id: str
    status: TaskStatus
    task: str
    budget_usdc: str
    reserved_usdc: str
    spent_usdc: str
    remaining_usdc: str
    max_concurrency: int
    calls: List[ServiceCallRecord] = Field(default_factory=list)
    result: Optional[Dict[str, Any]] = None
    explanation: Optional[PurchaseExplanation] = None
    actual_spent_atomic: int = 0
    failure_reason: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None


class TaskCallsResponse(BaseModel):
    task_id: str
    items: List[ServiceCallRecord] = Field(default_factory=list)

    @property
    def calls(self) -> List[ServiceCallRecord]:
        return self.items

    def model_dump(self, *args, **kwargs):
        data = super().model_dump(*args, **kwargs)
        data["calls"] = data.get("items", [])
        return data

