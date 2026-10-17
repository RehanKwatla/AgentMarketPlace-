"""Constants, Enums, and Currency Utilities for DI-06 Agent Economy."""
from enum import Enum
from decimal import Decimal, ROUND_HALF_UP

# Official CAIP-2 Network Identifier for Base Sepolia
NETWORK_BASE_SEPOLIA: str = "eip155:84532"
CHAIN_ID_BASE_SEPOLIA: int = 84532

# Official Base Sepolia USDC Contract
USDC_BASE_SEPOLIA: str = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
USDC_DECIMALS: int = 6
USDC_BASE_UNIT_MULTIPLIER: int = 10**USDC_DECIMALS

# HTTP Protocol Headers for x402 v2
HEADER_X402_REQUIREMENT: str = "X-402-Requirement"
HEADER_X402_PAYMENT_PAYLOAD: str = "X-402-Payment-Payload"
HEADER_X402_SETTLEMENT_PROOF: str = "X-402-Settlement-Proof"
HEADER_IDEMPOTENCY_KEY: str = "Idempotency-Key"

# System-wide Limits
DEFAULT_MAX_SERVICE_PRICE_USDC: str = "0.05"
DEFAULT_MAX_SERVICE_PRICE_UNITS: int = 50_000
DEFAULT_USER_MAX_BUDGET_USDC: str = "1.00"
DEFAULT_USER_MAX_BUDGET_UNITS: int = 1_000_000


class ServiceCategory(str, Enum):
    DATA = "data"
    SCRAPING = "scraping"
    INFERENCE = "inference"


class LedgerStatus(str, Enum):
    """The four strictly required terminal payment statuses."""
    PAID = "paid"
    PAID_OUTPUT_REJECTED = "paid output rejected"
    REFUSED = "refused"
    FAILED_AND_NOT_CHARGED = "failed and not charged"


class WalletRole(str, Enum):
    """Roles assignable to linked EVM wallets."""
    IDENTITY = "identity"
    PAYMENT = "payment"
    RECEIVING = "receiving"


class WalletType(str, Enum):
    """Supported EVM wallet providers."""
    METAMASK = "metamask"
    COINBASE = "coinbase"
    OTHER = "other"


class KycStatus(str, Enum):
    """Provider-neutral KYC verification lifecycle statuses."""
    NOT_STARTED = "NOT_STARTED"
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"
    EXPIRED = "EXPIRED"



def usdc_to_base_units(amount_usdc: str | float | Decimal) -> int:
    """Convert decimal USDC string (e.g. '0.002') to integer base units (2000).
    Uses Decimal to avoid floating-point inaccuracies.
    """
    d = Decimal(str(amount_usdc))
    units = (d * Decimal(USDC_BASE_UNIT_MULTIPLIER)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(units)


def base_units_to_usdc(units: int) -> str:
    """Convert integer base units (e.g. 2000) to standard 6-decimal string ('0.002000')."""
    d = Decimal(units) / Decimal(USDC_BASE_UNIT_MULTIPLIER)
    return f"{d:.6f}"
