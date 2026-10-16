"""[IMPLEMENTED FOUNDATION] Payment Policy Verification Engine."""
from backend.shared.constants import (
    NETWORK_BASE_SEPOLIA,
    USDC_BASE_SEPOLIA,
    DEFAULT_MAX_SERVICE_PRICE_UNITS,
)
from backend.shared.errors import PaymentPolicyViolationError
from backend.shared.schemas import PaymentRequirement, ServiceDefinition


class PaymentPolicyVerifier:
    """Enforces network, token, recipient, and price boundaries before payment signing."""

    def __init__(
        self,
        allowed_network: str = NETWORK_BASE_SEPOLIA,
        allowed_token: str = USDC_BASE_SEPOLIA,
        max_price_base_units: int = DEFAULT_MAX_SERVICE_PRICE_UNITS,
    ):
        self.allowed_network = allowed_network.lower()
        self.allowed_token = allowed_token.lower()
        self.max_price_base_units = max_price_base_units

    def verify(
        self,
        requirement: PaymentRequirement,
        registered_service: ServiceDefinition
    ) -> bool:
        """Execute full policy check against registered service catalog data.
        Raises PaymentPolicyViolationError on any violation.
        """
        # 1. Network Verification
        if requirement.network.lower() != self.allowed_network:
            raise PaymentPolicyViolationError(
                f"Network mismatch: Expected '{self.allowed_network}', got '{requirement.network}'"
            )

        # 2. Token Verification
        if requirement.token.lower() != self.allowed_token:
            raise PaymentPolicyViolationError(
                f"Token mismatch: Expected '{self.allowed_token}', got '{requirement.token}'"
            )

        # 3. Recipient (payTo) Verification
        if requirement.payTo.lower() != registered_service.pay_to.lower():
            raise PaymentPolicyViolationError(
                f"Recipient mismatch: Registered pay_to is '{registered_service.pay_to}', "
                f"but challenge requested '{requirement.payTo}'"
            )

        # 4. Price Quoted vs. Catalog Price Verification
        try:
            req_amount_units = int(requirement.amount)
        except ValueError:
            raise PaymentPolicyViolationError(f"Invalid integer amount in requirement: {requirement.amount}")

        if req_amount_units > registered_service.price_base_units:
            raise PaymentPolicyViolationError(
                f"Price gouging detected: Quoted {req_amount_units} units, "
                f"but catalog price is {registered_service.price_base_units} units"
            )

        # 5. Maximum Allowed Price Ceiling
        if req_amount_units > self.max_price_base_units:
            raise PaymentPolicyViolationError(
                f"Price exceeds maximum ceiling: {req_amount_units} > {self.max_price_base_units} units"
            )

        return True
