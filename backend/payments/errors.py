"""Typed Domain Errors for Payment Engine Subsystem (Member 1)."""
from backend.shared.errors import (
    AgentEconomyBaseException,
    BudgetExceededError,
    PaymentPolicyViolationError,
    ReplayAttackDetectedError,
    OutputSchemaValidationError,
)


class PaymentEngineError(AgentEconomyBaseException):
    """Base error for all payment engine failures."""
    def __init__(self, message: str, error_code: str = "PAYMENT_ENGINE_ERROR"):
        super().__init__(message=message, error_code=error_code)


class IdempotencyConflictError(PaymentEngineError):
    """Raised when an idempotency key is reused with a mutated request payload."""
    def __init__(self, key: str):
        super().__init__(
            f"Idempotency conflict: Key '{key}' was previously submitted with a different request payload.",
            error_code="IDEMPOTENCY_CONFLICT"
        )


class ServiceDisabledError(PaymentEngineError):
    """Raised when a service is inactive in the catalog."""
    def __init__(self, service_id: str):
        super().__init__(
            f"Service '{service_id}' is currently disabled in the catalog.",
            error_code="SERVICE_DISABLED"
        )


class SettlementVerificationError(PaymentEngineError):
    """Raised when settlement proof fails verification."""
    def __init__(self, detail: str):
        super().__init__(
            f"Settlement verification failed: {detail}",
            error_code="SETTLEMENT_VERIFICATION_FAILED"
        )


class SettlementTimeoutError(PaymentEngineError):
    """Raised when seller or facilitator times out after payment transmission."""
    def __init__(self, attempt_id: str):
        super().__init__(
            f"Payment operation timed out for attempt '{attempt_id}'. Outcome uncertain; marked pending reconciliation.",
            error_code="SETTLEMENT_TIMEOUT"
        )


__all__ = [
    "AgentEconomyBaseException",
    "BudgetExceededError",
    "PaymentPolicyViolationError",
    "ReplayAttackDetectedError",
    "OutputSchemaValidationError",
    "PaymentEngineError",
    "IdempotencyConflictError",
    "ServiceDisabledError",
    "SettlementVerificationError",
    "SettlementTimeoutError",
]
