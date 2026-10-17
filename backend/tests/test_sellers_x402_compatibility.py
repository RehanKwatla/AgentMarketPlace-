"""Official x402 Seller Protocol Compatibility Test Suite (Phase 2.5 Gate).

Verifies official x402 v2 header handling, challenge issuance, base64 payload decoding,
fail-closed verification, dual settlement proof headers, and lifecycle execution safety.
"""
import base64
from datetime import datetime, timezone
import json
from typing import Optional
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.shared.constants import (
    HEADER_X402_REQUIREMENT,
    HEADER_X402_PAYMENT_PAYLOAD,
    HEADER_X402_SETTLEMENT_PROOF,
    NETWORK_BASE_SEPOLIA,
    USDC_BASE_SEPOLIA,
)
from backend.shared.schemas import PaymentPayload, PaymentRequirement, SettlementReceipt
from backend.payments.interfaces import SellerPaymentVerifierInterface
from backend.payments.errors import SettlementVerificationError, ReplayAttackDetectedError
from backend.sellers.dependencies import get_data_seller_service, get_scraping_seller_service, get_inference_seller_service
from backend.sellers.routes import (
    get_payment_verifier,
    HEADER_PAYMENT_REQUIRED,
    HEADER_PAYMENT_SIGNATURE,
    HEADER_PAYMENT_RESPONSE,
    HEADER_X_PAYMENT,
    HEADER_X_PAYMENT_RESPONSE,
)

from x402 import http as x402_http
from x402.schemas import (
    PaymentRequired as OfficialPaymentRequired,
    PaymentRequirements as OfficialPaymentRequirements,
    SettleResponse as OfficialSettleResponse,
)


class MockSellerPaymentVerifier(SellerPaymentVerifierInterface):
    """Controllable test verifier for official x402 compatibility suite."""

    def __init__(
        self,
        should_succeed: bool = True,
        tx_hash: Optional[str] = "0xreal_settlement_tx_hash_1234567890abcdef",
        facilitator_receipt_id: Optional[str] = None,
        raise_exception: Optional[Exception] = None,
    ):
        self.should_succeed = should_succeed
        self.tx_hash = tx_hash
        self.facilitator_receipt_id = facilitator_receipt_id
        self.raise_exception = raise_exception
        self.call_count = 0
        self.last_payload: Optional[PaymentPayload] = None
        self.last_requirement: Optional[PaymentRequirement] = None
        self.seen_nonces = set()

    def issue_challenge(self, service_id: str, amount_units: int, pay_to: str) -> PaymentRequirement:
        return PaymentRequirement(
            version="2.0",
            network=NETWORK_BASE_SEPOLIA,
            token=USDC_BASE_SEPOLIA,
            amount=str(amount_units),
            payTo=pay_to,
            nonce=f"nonce_{service_id}_123",
            service_id=service_id,
        )

    async def verify_and_settle(self, payload: PaymentPayload, requirement: PaymentRequirement) -> SettlementReceipt:
        self.call_count += 1
        self.last_payload = payload
        self.last_requirement = requirement

        if self.raise_exception:
            raise self.raise_exception

        if requirement.nonce in self.seen_nonces:
            raise ReplayAttackDetectedError(f"Replay detected for nonce {requirement.nonce}")
        self.seen_nonces.add(requirement.nonce)

        if not self.should_succeed:
            raise SettlementVerificationError("Signature rejected by settlement verifier.")

        return SettlementReceipt(
            tx_hash=self.tx_hash,
            facilitator_receipt_id=self.facilitator_receipt_id,
            settled_at=datetime.now(timezone.utc),
            settled_amount_units=int(requirement.amount),
        )


def _make_official_b64_payment_payload(
    amount: str = "2000",
    pay_to: str = "0x1111111111111111111111111111111111111111",
    signature: str = "0x9876543210abcdef9876543210abcdef9876543210abcdef9876543210abcdef1b",
    buyer_address: str = "0xBuyer000000000000000000000000000000000000",
) -> str:
    """Helper to build official base64-encoded x402 PaymentPayload."""
    payload_dict = {
        "x402Version": 2,
        "accepted": {
            "scheme": "exact",
            "network": NETWORK_BASE_SEPOLIA,
            "asset": USDC_BASE_SEPOLIA,
            "amount": amount,
            "payTo": pay_to,
            "maxTimeoutSeconds": 60,
            "extra": {},
        },
        "payload": {
            "authorization": {
                "amount": amount,
                "payTo": pay_to,
                "token": USDC_BASE_SEPOLIA,
                "network": NETWORK_BASE_SEPOLIA,
                "buyer_address": buyer_address,
            },
            "signature": signature,
        },
    }
    return base64.b64encode(json.dumps(payload_dict).encode("utf-8")).decode("utf-8")


@pytest.fixture
def client():
    return TestClient(app)


# ==============================================================================
# Scenario A: Missing Payment Header
# ==============================================================================

def test_missing_payment_header_returns_official_and_legacy_challenge(client):
    """Missing payment headers must return HTTP 402 with both official and legacy headers."""
    response = client.post("/api/v1/seller/data", json={"symbol": "BTC"})
    assert response.status_code == 402

    headers = response.headers
    # Official challenge headers
    assert HEADER_PAYMENT_REQUIRED in headers
    assert HEADER_X_PAYMENT in headers
    # Legacy challenge header
    assert HEADER_X402_REQUIREMENT in headers

    # Access-Control-Expose-Headers must expose all official and legacy headers
    expose = headers.get("Access-Control-Expose-Headers", "")
    assert HEADER_PAYMENT_REQUIRED in expose
    assert HEADER_X_PAYMENT in expose
    assert HEADER_X402_REQUIREMENT in expose
    assert HEADER_PAYMENT_RESPONSE in expose
    assert HEADER_X402_SETTLEMENT_PROOF in expose

    # Official challenge must decode correctly via official SDK
    decoded = x402_http.decode_payment_required_header(headers[HEADER_PAYMENT_REQUIRED])
    assert decoded.x402_version == 2
    assert len(decoded.accepts) == 1
    req = decoded.accepts[0]
    assert req.scheme == "exact"
    assert req.network == NETWORK_BASE_SEPOLIA
    assert req.asset == USDC_BASE_SEPOLIA
    assert req.amount == "2000"
    assert req.extra.get("service_id") == "data_001"


# ==============================================================================
# Scenario B: Malformed Payment Header
# ==============================================================================

def test_malformed_base64_payment_header_rejected_400(client):
    """Corrupted base64 in PAYMENT-SIGNATURE must be rejected with HTTP 400."""
    response = client.post(
        "/api/v1/seller/data",
        json={"symbol": "BTC"},
        headers={HEADER_PAYMENT_SIGNATURE: "not_valid_base64???"},
    )
    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "PAYMENT_PAYLOAD_INVALID"


def test_corrupted_json_in_payment_header_rejected_400(client):
    """Valid base64 containing unparseable JSON string must be rejected with HTTP 400."""
    corrupted_b64 = base64.b64encode(b"invalid-json{not:closed").decode()
    response = client.post(
        "/api/v1/seller/data",
        json={"symbol": "BTC"},
        headers={HEADER_PAYMENT_SIGNATURE: corrupted_b64},
    )
    assert response.status_code == 400
    assert response.json()["error_code"] == "PAYMENT_PAYLOAD_INVALID"


def test_arbitrary_unstructured_json_rejected_400(client):
    """Valid base64 containing JSON missing required auth/signature must be rejected with HTTP 400."""
    unstructured_b64 = base64.b64encode(json.dumps({"some_key": "some_value"}).encode()).decode()
    response = client.post(
        "/api/v1/seller/data",
        json={"symbol": "BTC"},
        headers={HEADER_PAYMENT_SIGNATURE: unstructured_b64},
    )
    assert response.status_code == 400
    assert response.json()["error_code"] == "PAYMENT_PAYLOAD_INVALID"


# ==============================================================================
# Scenario C: Invalid Payment (Verification Rejection)
# ==============================================================================

def test_invalid_payment_fails_closed_402(client):
    """When verifier rejects signature, seller must return 402 and not execute."""
    verifier = MockSellerPaymentVerifier(should_succeed=False)
    app.dependency_overrides[get_payment_verifier] = lambda: verifier

    b64_payload = _make_official_b64_payment_payload()

    try:
        response = client.post(
            "/api/v1/seller/data",
            json={"symbol": "BTC"},
            headers={HEADER_PAYMENT_SIGNATURE: b64_payload},
        )
        assert response.status_code == 402
        assert response.json()["error_code"] == "PAYMENT_AUTHORIZATION_FAILED"
        assert HEADER_PAYMENT_RESPONSE not in response.headers
        assert HEADER_X402_SETTLEMENT_PROOF not in response.headers
        assert verifier.call_count == 1
    finally:
        app.dependency_overrides.pop(get_payment_verifier, None)


# ==============================================================================
# Scenario D: Verification Service Unavailable (Missing Verifier)
# ==============================================================================

def test_missing_verifier_fails_closed_503(client):
    """When no verifier is configured, official header request must fail closed with HTTP 503."""
    app.dependency_overrides[get_payment_verifier] = lambda: None
    b64_payload = _make_official_b64_payment_payload()

    try:
        response = client.post(
            "/api/v1/seller/data",
            json={"symbol": "BTC"},
            headers={HEADER_PAYMENT_SIGNATURE: b64_payload},
        )
        assert response.status_code == 503
        assert response.json()["error_code"] == "PAYMENT_VERIFIER_UNAVAILABLE"
        assert HEADER_PAYMENT_RESPONSE not in response.headers
        assert HEADER_X402_SETTLEMENT_PROOF not in response.headers
    finally:
        app.dependency_overrides.pop(get_payment_verifier, None)


# ==============================================================================
# Scenario E: Verification Exception Sanitization
# ==============================================================================

def test_verifier_exception_sanitizes_secrets(client):
    """Exceptions from verifier containing DB credentials or private info must be sanitized."""
    verifier = MockSellerPaymentVerifier(
        raise_exception=RuntimeError("Connection refused postgresql://dbuser:super_secret_pw@10.0.0.1:5432")
    )
    app.dependency_overrides[get_payment_verifier] = lambda: verifier
    b64_payload = _make_official_b64_payment_payload()

    try:
        response = client.post(
            "/api/v1/seller/data",
            json={"symbol": "BTC"},
            headers={HEADER_PAYMENT_SIGNATURE: b64_payload},
        )
        assert response.status_code == 402
        data = response.json()
        assert data["error_code"] == "PAYMENT_AUTHORIZATION_FAILED"
        assert "super_secret_pw" not in json.dumps(data)
        assert "Internal verification system error." in data["message"]
    finally:
        app.dependency_overrides.pop(get_payment_verifier, None)


# ==============================================================================
# Scenario F & J: Valid Payment via Official PAYMENT-SIGNATURE Header
# ==============================================================================

def test_valid_payment_via_official_payment_signature_header_success(client):
    """Valid payment in PAYMENT-SIGNATURE executes seller and returns official SettleResponse headers."""
    tx_hash = "0x8888888888888888888888888888888888888888888888888888888888888888"
    verifier = MockSellerPaymentVerifier(should_succeed=True, tx_hash=tx_hash)
    app.dependency_overrides[get_payment_verifier] = lambda: verifier

    b64_payload = _make_official_b64_payment_payload()

    try:
        response = client.post(
            "/api/v1/seller/data",
            json={"symbol": "BTC"},
            headers={HEADER_PAYMENT_SIGNATURE: b64_payload},
        )
        assert response.status_code == 200
        output = response.json()
        assert output["symbol"] == "BTC"
        assert output["price"] > 0

        # Legacy settlement proof header
        assert HEADER_X402_SETTLEMENT_PROOF in response.headers
        assert response.headers[HEADER_X402_SETTLEMENT_PROOF] == tx_hash

        # Official settlement response headers
        assert HEADER_PAYMENT_RESPONSE in response.headers
        assert HEADER_X_PAYMENT_RESPONSE in response.headers

        # Decode official response header using official x402 SDK
        settle = x402_http.decode_payment_response_header(response.headers[HEADER_PAYMENT_RESPONSE])
        assert settle.success is True
        assert settle.transaction == tx_hash
        assert settle.network == NETWORK_BASE_SEPOLIA
        assert settle.amount == "2000"

        # Verify X-PAYMENT-RESPONSE decodes identically
        x_settle = x402_http.decode_payment_response_header(response.headers[HEADER_X_PAYMENT_RESPONSE])
        assert x_settle.success is True
        assert x_settle.transaction == tx_hash

        assert verifier.call_count == 1
    finally:
        app.dependency_overrides.pop(get_payment_verifier, None)


# ==============================================================================
# Scenario F2: Valid Payment via Official X-PAYMENT Header
# ==============================================================================

def test_valid_payment_via_official_x_payment_header_success(client):
    """Valid payment via X-PAYMENT alternative header also succeeds and returns official headers."""
    tx_hash = "0x7777777777777777777777777777777777777777777777777777777777777777"
    verifier = MockSellerPaymentVerifier(should_succeed=True, tx_hash=tx_hash)
    app.dependency_overrides[get_payment_verifier] = lambda: verifier

    b64_payload = _make_official_b64_payment_payload()

    try:
        response = client.post(
            "/api/v1/seller/data",
            json={"symbol": "ETH"},
            headers={HEADER_X_PAYMENT: b64_payload},
        )
        assert response.status_code == 200
        assert response.headers[HEADER_X402_SETTLEMENT_PROOF] == tx_hash
        settle = x402_http.decode_payment_response_header(response.headers[HEADER_PAYMENT_RESPONSE])
        assert settle.success is True
        assert settle.transaction == tx_hash
    finally:
        app.dependency_overrides.pop(get_payment_verifier, None)


# ==============================================================================
# Scenario G: Pending Payment (No Confirmed Settlement Proof)
# ==============================================================================

def test_pending_payment_with_empty_proof_fails_closed(client):
    """When verifier returns a receipt with empty proof (pending/unconfirmed), fail closed with 402."""
    verifier = MockSellerPaymentVerifier(should_succeed=True, tx_hash=None, facilitator_receipt_id=None)
    app.dependency_overrides[get_payment_verifier] = lambda: verifier
    b64_payload = _make_official_b64_payment_payload()

    try:
        response = client.post(
            "/api/v1/seller/data",
            json={"symbol": "BTC"},
            headers={HEADER_PAYMENT_SIGNATURE: b64_payload},
        )
        assert response.status_code == 402
        assert response.json()["error_code"] == "PAYMENT_AUTHORIZATION_FAILED"
        assert HEADER_PAYMENT_RESPONSE not in response.headers
        assert HEADER_X402_SETTLEMENT_PROOF not in response.headers
    finally:
        app.dependency_overrides.pop(get_payment_verifier, None)


# ==============================================================================
# Scenario H: Replay Attack Protection
# ==============================================================================

def test_replayed_payment_nonce_fails_closed(client):
    """Replaying identical request that reuses nonce must fail closed on second attempt."""
    verifier = MockSellerPaymentVerifier(should_succeed=True)
    app.dependency_overrides[get_payment_verifier] = lambda: verifier

    from backend.sellers.dependencies import get_seller_execution_context
    from backend.sellers.common import SellerExecutionContext

    fixed_ctx = SellerExecutionContext(
        service_id="data_001",
        request_id="fixed_replay_id_12345",
    )
    app.dependency_overrides[get_seller_execution_context] = lambda: fixed_ctx

    b64_payload = _make_official_b64_payment_payload()

    try:
        # First request succeeds
        res1 = client.post(
            "/api/v1/seller/data",
            json={"symbol": "BTC"},
            headers={HEADER_PAYMENT_SIGNATURE: b64_payload},
        )
        assert res1.status_code == 200

        # Second request reuses same request id (and therefore same nonce), verifier rejects
        res2 = client.post(
            "/api/v1/seller/data",
            json={"symbol": "BTC"},
            headers={HEADER_PAYMENT_SIGNATURE: b64_payload},
        )
        assert res2.status_code == 402
        assert res2.json()["error_code"] == "PAYMENT_AUTHORIZATION_FAILED"
        assert "Replay detected" in res2.json()["message"]
        assert HEADER_PAYMENT_RESPONSE not in res2.headers
    finally:
        app.dependency_overrides.pop(get_payment_verifier, None)
        app.dependency_overrides.pop(get_seller_execution_context, None)


# ==============================================================================
# Scenario I: Seller Execution Failure Does Not Fabricate Proof
# ==============================================================================

def test_seller_execution_failure_attaches_no_proof(client):
    """If seller logic crashes after payment verification, no settlement proof is attached to error."""
    verifier = MockSellerPaymentVerifier(should_succeed=True)
    app.dependency_overrides[get_payment_verifier] = lambda: verifier

    mock_service = AsyncMock()
    mock_service.execute_lifecycle.side_effect = RuntimeError("Fatal hardware failure")
    app.dependency_overrides[get_data_seller_service] = lambda: mock_service

    b64_payload = _make_official_b64_payment_payload()

    try:
        response = client.post(
            "/api/v1/seller/data",
            json={"symbol": "BTC"},
            headers={HEADER_PAYMENT_SIGNATURE: b64_payload},
        )
        assert response.status_code == 500
        # Critical security check: NEVER attach settlement proof to failed execution responses
        assert HEADER_PAYMENT_RESPONSE not in response.headers
        assert HEADER_X_PAYMENT_RESPONSE not in response.headers
        assert HEADER_X402_SETTLEMENT_PROOF not in response.headers
    finally:
        app.dependency_overrides.pop(get_payment_verifier, None)
        app.dependency_overrides.pop(get_data_seller_service, None)


# ==============================================================================
# Scenario K: Scraping and Inference Sellers Support Official Header
# ==============================================================================

def test_scraping_seller_official_x402_flow(client):
    """Scraping seller endpoint accepts official PAYMENT-SIGNATURE and returns official headers."""
    tx_hash = "0xscraping_official_proof_123456"
    verifier = MockSellerPaymentVerifier(should_succeed=True, tx_hash=tx_hash)
    app.dependency_overrides[get_payment_verifier] = lambda: verifier

    b64_payload = _make_official_b64_payment_payload(amount="3000")

    try:
        response = client.post(
            "/api/v1/seller/scraping",
            json={"url": "https://example.com/blog"},
            headers={HEADER_PAYMENT_SIGNATURE: b64_payload},
        )
        assert response.status_code == 200
        assert response.headers[HEADER_X402_SETTLEMENT_PROOF] == tx_hash
        settle = x402_http.decode_payment_response_header(response.headers[HEADER_PAYMENT_RESPONSE])
        assert settle.success is True
        assert settle.transaction == tx_hash
        assert settle.amount == "3000"
    finally:
        app.dependency_overrides.pop(get_payment_verifier, None)


def test_inference_seller_official_x402_flow(client):
    """Inference seller endpoint accepts official PAYMENT-SIGNATURE and returns official headers."""
    tx_hash = "0xinference_official_proof_654321"
    verifier = MockSellerPaymentVerifier(should_succeed=True, tx_hash=tx_hash)
    app.dependency_overrides[get_payment_verifier] = lambda: verifier

    b64_payload = _make_official_b64_payment_payload(amount="4000")

    try:
        response = client.post(
            "/api/v1/seller/inference",
            json={"prompt": "Analyze market trends"},
            headers={HEADER_PAYMENT_SIGNATURE: b64_payload},
        )
        assert response.status_code == 200
        assert response.headers[HEADER_X402_SETTLEMENT_PROOF] == tx_hash
        settle = x402_http.decode_payment_response_header(response.headers[HEADER_PAYMENT_RESPONSE])
        assert settle.success is True
        assert settle.transaction == tx_hash
        assert settle.amount == "4000"
    finally:
        app.dependency_overrides.pop(get_payment_verifier, None)
