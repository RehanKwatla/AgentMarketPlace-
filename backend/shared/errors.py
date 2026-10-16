"""Custom Exception Classes and Standard Error Handlers."""
from fastapi import HTTPException, status


class AgentEconomyBaseException(Exception):
    """Base exception for all domain-specific agent economy errors."""
    def __init__(self, message: str, error_code: str = "INTERNAL_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class LedgerInconsistencyError(AgentEconomyBaseException):
    def __init__(self, detail: str):
        super().__init__(
            f"Ledger inconsistency detected: {detail}",
            error_code="LEDGER_INCONSISTENCY"
        )


class SettlementUnverifiedError(AgentEconomyBaseException):
    def __init__(self, detail: str = "Settlement evidence could not be verified."):
        super().__init__(detail, error_code="SETTLEMENT_UNVERIFIED")


class BudgetExceededError(AgentEconomyBaseException):
    def __init__(self, requested_units: int, available_units: int):
        super().__init__(
            f"Budget exceeded: Requested {requested_units} units, but only {available_units} units available.",
            error_code="BUDGET_EXCEEDED"
        )


class PaymentPolicyViolationError(AgentEconomyBaseException):
    def __init__(self, detail: str):
        super().__init__(detail, error_code="PAYMENT_POLICY_VIOLATION")


class ReplayAttackDetectedError(AgentEconomyBaseException):
    def __init__(self, nonce_or_key: str):
        super().__init__(f"Replay detected for token/nonce: {nonce_or_key}", error_code="REPLAY_DETECTED")


class OutputSchemaValidationError(AgentEconomyBaseException):
    def __init__(self, service_id: str, details: str):
        super().__init__(
            f"Output from service '{service_id}' violated registered schema: {details}",
            error_code="OUTPUT_SCHEMA_INVALID"
        )


class ServiceNotFoundError(HTTPException):
    def __init__(self, service_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service with ID '{service_id}' not found in registry."
        )


class PaymentRequiredHTTPException(HTTPException):
    """HTTP 402 with X-402-Requirement challenge headers."""
    def __init__(self, requirement_json: str):
        super().__init__(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Payment Required via x402 v2 protocol.",
            headers={"X-402-Requirement": requirement_json}
        )
