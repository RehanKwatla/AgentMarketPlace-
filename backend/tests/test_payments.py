"""Tests for Payment Policy Verification."""
import pytest
from backend.shared.constants import NETWORK_BASE_SEPOLIA, USDC_BASE_SEPOLIA
from backend.shared.errors import PaymentPolicyViolationError
from backend.shared.schemas import PaymentRequirement, ServiceDefinition
from backend.payments.policy import PaymentPolicyVerifier


@pytest.fixture
def sample_service():
    return ServiceDefinition(
        service_id="data_001",
        name="Market Data",
        category="data",
        endpoint_url="http://localhost:8000/api/v1/seller/data",
        price_usdc="0.002",
        price_base_units=2000,
        network=NETWORK_BASE_SEPOLIA,
        pay_to="0x1111111111111111111111111111111111111111"
    )


def test_payment_policy_valid(sample_service):
    verifier = PaymentPolicyVerifier()
    req = PaymentRequirement(
        version="2.0",
        network=NETWORK_BASE_SEPOLIA,
        token=USDC_BASE_SEPOLIA,
        amount="2000",
        payTo=sample_service.pay_to,
        nonce="nonce_test_123",
        service_id="data_001"
    )
    assert verifier.verify(req, sample_service) is True


def test_payment_policy_network_mismatch(sample_service):
    verifier = PaymentPolicyVerifier()
    req = PaymentRequirement(
        version="2.0",
        network="eip155:1",  # Ethereum Mainnet (forbidden!)
        token=USDC_BASE_SEPOLIA,
        amount="2000",
        payTo=sample_service.pay_to,
        nonce="nonce_test_123",
        service_id="data_001"
    )
    with pytest.raises(PaymentPolicyViolationError) as exc_info:
        verifier.verify(req, sample_service)
    assert "Network mismatch" in str(exc_info.value)


def test_payment_policy_token_mismatch(sample_service):
    verifier = PaymentPolicyVerifier()
    req = PaymentRequirement(
        version="2.0",
        network=NETWORK_BASE_SEPOLIA,
        token="0xDeadDeAddeAddEAddeadDEaDDEAdDeaDDeAD0000",  # Fake token
        amount="2000",
        payTo=sample_service.pay_to,
        nonce="nonce_test_123",
        service_id="data_001"
    )
    with pytest.raises(PaymentPolicyViolationError) as exc_info:
        verifier.verify(req, sample_service)
    assert "Token mismatch" in str(exc_info.value)


def test_payment_policy_recipient_mismatch(sample_service):
    verifier = PaymentPolicyVerifier()
    req = PaymentRequirement(
        version="2.0",
        network=NETWORK_BASE_SEPOLIA,
        token=USDC_BASE_SEPOLIA,
        amount="2000",
        payTo="0x9999999999999999999999999999999999999999",  # Rogue address
        nonce="nonce_test_123",
        service_id="data_001"
    )
    with pytest.raises(PaymentPolicyViolationError) as exc_info:
        verifier.verify(req, sample_service)
    assert "Recipient mismatch" in str(exc_info.value)


def test_payment_policy_price_gouging(sample_service):
    verifier = PaymentPolicyVerifier()
    req = PaymentRequirement(
        version="2.0",
        network=NETWORK_BASE_SEPOLIA,
        token=USDC_BASE_SEPOLIA,
        amount="5000",  # Higher than registered catalog 2000 units
        payTo=sample_service.pay_to,
        nonce="nonce_test_123",
        service_id="data_001"
    )
    with pytest.raises(PaymentPolicyViolationError) as exc_info:
        verifier.verify(req, sample_service)
    assert "Price gouging detected" in str(exc_info.value)
