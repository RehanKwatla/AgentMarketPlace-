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


# --- Phase 3 Domain Exceptions ---

class AuthenticationFailedError(AgentEconomyBaseException):
    def __init__(self, detail: str = "Invalid email or password."):
        super().__init__(detail, error_code="AUTHENTICATION_FAILED")


class TokenRevokedOrExpiredError(AgentEconomyBaseException):
    def __init__(self, detail: str = "Session token has been revoked or expired."):
        super().__init__(detail, error_code="TOKEN_REVOKED_OR_EXPIRED")


class WalletVerificationFailedError(AgentEconomyBaseException):
    def __init__(self, detail: str = "Cryptographic wallet signature verification failed."):
        super().__init__(detail, error_code="WALLET_VERIFICATION_FAILED")


class WalletAlreadyLinkedError(AgentEconomyBaseException):
    def __init__(self, address: str):
        super().__init__(
            f"Wallet address '{address}' is already linked to another active account.",
            error_code="WALLET_ALREADY_LINKED"
        )


class WalletNotFoundError(AgentEconomyBaseException):
    def __init__(self, wallet_id: str):
        super().__init__(
            f"Linked wallet with ID '{wallet_id}' not found.",
            error_code="WALLET_NOT_FOUND"
        )


class WalletRoleViolationError(AgentEconomyBaseException):
    def __init__(self, detail: str):
        super().__init__(detail, error_code="WALLET_ROLE_VIOLATION")


class KycTransitionInvalidError(AgentEconomyBaseException):
    def __init__(self, from_status: str, to_status: str):
        super().__init__(
            f"Invalid KYC status transition from '{from_status}' to '{to_status}'.",
            error_code="KYC_INVALID_TRANSITION"
        )


class KycUnauthorizedUpdateError(AgentEconomyBaseException):
    def __init__(self, detail: str = "Direct client status updates are forbidden. Status must come from verified provider webhooks."):
        super().__init__(detail, error_code="KYC_UNAUTHORIZED_UPDATE")


class KycWebhookVerificationFailedError(AgentEconomyBaseException):
    def __init__(self, detail: str = "KYC provider webhook signature verification failed."):
        super().__init__(detail, error_code="KYC_WEBHOOK_VERIFICATION_FAILED")


class UnauthorizedAccessError(AgentEconomyBaseException):
    def __init__(self, detail: str = "Access denied: insufficient permissions or verification level."):
        super().__init__(detail, error_code="UNAUTHORIZED_ACCESS")

