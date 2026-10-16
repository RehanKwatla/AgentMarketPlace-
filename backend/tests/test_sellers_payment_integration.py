"""[TEST SUITE] Comprehensive Seller-Payment Integration & Safety Boundary Tests.

Verifies:
1. HTTP 402 Payment Challenges (missing, empty, whitespace headers, exact fields & prices).
2. Fail-Closed Security (missing verifier, None receipt, empty/whitespace proof, verifier crash).
3. SSRF Protection and input validation for Scraping Seller.
4. Input sanitization and bounding for Data and Inference Sellers.
5. Zero Fake Evidence: only genuine verifier-provided proof is attached to responses.
6. Execution Failure Handling (timeout, invalid output, internal error).
7. Execution Context & Idempotency Key forwarding.
8. Local Buyer-to-Seller handshake lifecycle.
"""
import json
import pytest
from fastapi import status
from fastapi.testclient import TestClient

from backend.main import app
from backend.shared.constants import (
    HEADER_X402_REQUIREMENT,
    HEADER_X402_PAYMENT_PAYLOAD,
    HEADER_X402_SETTLEMENT_PROOF,
    HEADER_IDEMPOTENCY_KEY,
    NETWORK_BASE_SEPOLIA,
    USDC_BASE_SEPOLIA,
)
from backend.shared.schemas import PaymentPayload, PaymentRequirement, SettlementReceipt
from backend.payments.interfaces import SellerPaymentVerifierInterface
from backend.sellers.routes import get_payment_verifier
from backend.sellers.dependencies import (
    get_data_seller_service,
    get_scraping_seller_service,
    get_inference_seller_service,
)
from backend.sellers.data_seller import DataSellerService
from backend.sellers.scraping_seller import ScrapingSellerService
from backend.sellers.inference_seller import InferenceSellerService


@pytest.fixture
def client():
    return TestClient(app)


# ==============================================================================
# 1. PAYMENT CHALLENGE TESTS (Section 7.A)
# ==============================================================================

def test_missing_payment_header_returns_402_challenge_all_services(client):
    """Verify that omitting X-402-Payment-Payload returns HTTP 402 with full challenge."""
    services = [
        ("/api/v1/seller/data", {"symbol": "ETH"}, "data_001", "2000"),
        ("/api/v1/seller/scraping", {"url": "https://ethereum.org"}, "scraping_001", "3000"),
        ("/api/v1/seller/inference", {"prompt": "Analyze", "max_tokens": 50}, "inference_001", "4000"),
    ]
    for endpoint, payload, expected_id, expected_amount in services:
        res = client.post(endpoint, json=payload)
        assert res.status_code == status.HTTP_402_PAYMENT_REQUIRED
        assert HEADER_X402_REQUIREMENT in res.headers
        assert HEADER_X402_SETTLEMENT_PROOF not in res.headers

        req = json.loads(res.headers[HEADER_X402_REQUIREMENT])
        assert req["version"] == "2.0"
        assert req["network"] == NETWORK_BASE_SEPOLIA
        assert req["token"] == USDC_BASE_SEPOLIA
        assert req["service_id"] == expected_id
        assert req["amount"] == expected_amount
        assert "nonce" in req and req["nonce"].startswith("nonce_")
        assert "payTo" in req and req["payTo"].startswith("0x")


def test_empty_and_whitespace_payment_header_returns_402_challenge(client):
    """Verify that an empty or whitespace X-402-Payment-Payload header is treated as unprovided."""
    for empty_val in ["", "   ", "\t\n"]:
        res = client.post(
            "/api/v1/seller/data",
            json={"symbol": "BTC"},
            headers={HEADER_X402_PAYMENT_PAYLOAD: empty_val}
        )
        assert res.status_code == status.HTTP_402_PAYMENT_REQUIRED
        assert HEADER_X402_REQUIREMENT in res.headers
        req = json.loads(res.headers[HEADER_X402_REQUIREMENT])
        assert req["service_id"] == "data_001"
        assert req["amount"] == "2000"


# ==============================================================================
# 2. FAIL-CLOSED PAYMENT VERIFICATION TESTS (Section 7.B)
# ==============================================================================

def test_receipt_with_no_proof_fails_closed(client):
    """Verify that if a verifier returns a SettlementReceipt with neither tx_hash nor receipt_id, route fails closed."""
    class EmptyProofVerifier(SellerPaymentVerifierInterface):
        def issue_challenge(self, service_id, amount_units, pay_to):
            return PaymentRequirement(
                version="2.0", network=NETWORK_BASE_SEPOLIA, token=USDC_BASE_SEPOLIA,
                amount=str(amount_units), payTo=pay_to, nonce="nonce_empty", service_id=service_id
            )
        async def verify_and_settle(self, payload, req):
            # Returns receipt with None proof
            return SettlementReceipt(tx_hash=None, facilitator_receipt_id=None, settled_amount_units=int(req.amount))

    app.dependency_overrides[get_payment_verifier] = lambda: EmptyProofVerifier()
    try:
        headers = {
            HEADER_X402_PAYMENT_PAYLOAD: json.dumps({
                "authorization": {"amount": "2000"},
                "signature": "0x123",
                "buyer_address": "0x0000000000000000000000000000000000000000"
            })
        }
        res = client.post("/api/v1/seller/data", json={"symbol": "ETH"}, headers=headers)
        assert res.status_code == status.HTTP_402_PAYMENT_REQUIRED
        assert res.json()["error_code"] == "PAYMENT_AUTHORIZATION_FAILED"
        assert "unconfirmed settlement proof" in res.json()["message"]
        assert HEADER_X402_SETTLEMENT_PROOF not in res.headers
    finally:
        app.dependency_overrides.pop(get_payment_verifier, None)


def test_receipt_with_whitespace_proof_fails_closed(client):
    """Verify that whitespace-only proof strings are rejected as unconfirmed."""
    class WhitespaceProofVerifier(SellerPaymentVerifierInterface):
        def issue_challenge(self, service_id, amount_units, pay_to):
            return PaymentRequirement(
                version="2.0", network=NETWORK_BASE_SEPOLIA, token=USDC_BASE_SEPOLIA,
                amount=str(amount_units), payTo=pay_to, nonce="nonce_ws", service_id=service_id
            )
        async def verify_and_settle(self, payload, req):
            return SettlementReceipt(facilitator_receipt_id="   ", settled_amount_units=int(req.amount))

    app.dependency_overrides[get_payment_verifier] = lambda: WhitespaceProofVerifier()
    try:
        headers = {
            HEADER_X402_PAYMENT_PAYLOAD: json.dumps({
                "authorization": {"amount": "2000"},
                "signature": "0x123",
                "buyer_address": "0x0000000000000000000000000000000000000000"
            })
        }
        res = client.post("/api/v1/seller/data", json={"symbol": "ETH"}, headers=headers)
        assert res.status_code == status.HTTP_402_PAYMENT_REQUIRED
        assert res.json()["error_code"] == "PAYMENT_AUTHORIZATION_FAILED"
        assert HEADER_X402_SETTLEMENT_PROOF not in res.headers
    finally:
        app.dependency_overrides.pop(get_payment_verifier, None)


def test_verifier_raising_domain_error_fails_closed(client):
    """Verify that verifier exceptions return HTTP 402 with sanitized error and no proof."""
    class CrashingVerifier(SellerPaymentVerifierInterface):
        def issue_challenge(self, service_id, amount_units, pay_to):
            return PaymentRequirement(
                version="2.0", network=NETWORK_BASE_SEPOLIA, token=USDC_BASE_SEPOLIA,
                amount=str(amount_units), payTo=pay_to, nonce="nonce_crash", service_id=service_id
            )
        async def verify_and_settle(self, payload, req):
            raise RuntimeError("RPC Connection Refused to Node 84532")

    app.dependency_overrides[get_payment_verifier] = lambda: CrashingVerifier()
    try:
        headers = {
            HEADER_X402_PAYMENT_PAYLOAD: json.dumps({
                "authorization": {"amount": "2000"},
                "signature": "0x123",
                "buyer_address": "0x0000000000000000000000000000000000000000"
            })
        }
        res = client.post("/api/v1/seller/data", json={"symbol": "ETH"}, headers=headers)
        assert res.status_code == status.HTTP_402_PAYMENT_REQUIRED
        assert res.json()["error_code"] == "PAYMENT_AUTHORIZATION_FAILED"
        assert HEADER_X402_SETTLEMENT_PROOF not in res.headers
    finally:
        app.dependency_overrides.pop(get_payment_verifier, None)


# ==============================================================================
# 3. SSRF & INPUT VALIDATION TESTS FOR SCRAPING SELLER (Section 7.E)
# ==============================================================================

def test_ssrf_protection_blocks_private_and_loopback_destinations(client):
    """Verify that ScrapingSellerInput strictly rejects loopback, private ranges, and cloud metadata."""
    forbidden_urls = [
        "http://localhost/admin",
        "http://127.0.0.1:8000/api/v1/ledger",
        "http://[::1]/secret",
        "http://0.0.0.0/debug",
        "http://169.254.169.254/latest/meta-data/",
        "http://metadata.google.internal/computeMetadata/v1/",
        "http://10.0.0.1/internal",
        "http://192.168.1.1/router",
        "http://172.16.0.1/service",
        "ftp://example.com/file.txt",
        "file:///etc/passwd",
    ]
    for url in forbidden_urls:
        res = client.post("/api/v1/seller/scraping", json={"url": url})
        assert res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, f"Failed to reject forbidden URL: {url}"


def test_scraping_seller_accepts_valid_public_urls(client):
    """Verify that valid public HTTP/HTTPS URLs pass schema validation and issue 402 challenge."""
    valid_urls = [
        "https://ethereum.org",
        "https://base.org/about",
        "http://example.com/index.html",
        "https://api.github.com/repos",
    ]
    for url in valid_urls:
        res = client.post("/api/v1/seller/scraping", json={"url": url})
        assert res.status_code == status.HTTP_402_PAYMENT_REQUIRED
        assert HEADER_X402_REQUIREMENT in res.headers


# ==============================================================================
# 4. INPUT VALIDATION TESTS FOR DATA & INFERENCE SELLERS (Section 7.E)
# ==============================================================================

def test_data_seller_input_validation(client):
    """Verify DataSellerInput rejects empty, whitespace, and non-alphanumeric ticker symbols."""
    # Empty
    res = client.post("/api/v1/seller/data", json={"symbol": ""})
    assert res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Whitespace only
    res = client.post("/api/v1/seller/data", json={"symbol": "   "})
    assert res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Special characters / SQL injection attempt
    res = client.post("/api/v1/seller/data", json={"symbol": "ETH'; DROP--"})
    assert res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Valid symbol passes
    res = client.post("/api/v1/seller/data", json={"symbol": "eth"})
    assert res.status_code == status.HTTP_402_PAYMENT_REQUIRED


def test_inference_seller_input_validation(client):
    """Verify InferenceSellerInput bounds prompt length, max_tokens, and temperature."""
    # Empty prompt
    res = client.post("/api/v1/seller/inference", json={"prompt": ""})
    assert res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Whitespace only
    res = client.post("/api/v1/seller/inference", json={"prompt": "   "})
    assert res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Temperature out of bounds (> 1.0)
    res = client.post("/api/v1/seller/inference", json={"prompt": "Test", "temperature": 1.5})
    assert res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Max tokens out of bounds (> 2000)
    res = client.post("/api/v1/seller/inference", json={"prompt": "Test", "max_tokens": 5000})
    assert res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ==============================================================================
# 5. ZERO FAKE EVIDENCE TESTS (Section 7.C)
# ==============================================================================

def test_onchain_tx_hash_passed_verbatim_as_settlement_proof(client):
    """Verify that an on-chain transaction hash from the verifier is passed verbatim without synthetic wrappers."""
    real_tx_hash = "0x5d9e8432a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef012345678"

    class OnChainVerifier(SellerPaymentVerifierInterface):
        def issue_challenge(self, service_id, amount_units, pay_to):
            return PaymentRequirement(
                version="2.0", network=NETWORK_BASE_SEPOLIA, token=USDC_BASE_SEPOLIA,
                amount=str(amount_units), payTo=pay_to, nonce="nonce_onchain", service_id=service_id
            )
        async def verify_and_settle(self, payload, req):
            return SettlementReceipt(tx_hash=real_tx_hash, facilitator_receipt_id=None, settled_amount_units=int(req.amount))

    app.dependency_overrides[get_payment_verifier] = lambda: OnChainVerifier()
    try:
        headers = {
            HEADER_X402_PAYMENT_PAYLOAD: json.dumps({
                "authorization": {"amount": "2000"},
                "signature": "0x123",
                "buyer_address": "0x0000000000000000000000000000000000000000"
            })
        }
        res = client.post("/api/v1/seller/data", json={"symbol": "ETH"}, headers=headers)
        assert res.status_code == status.HTTP_200_OK
        assert HEADER_X402_SETTLEMENT_PROOF in res.headers
        # Exact transaction hash match — zero random UUIDs synthesized
        assert res.headers[HEADER_X402_SETTLEMENT_PROOF] == real_tx_hash
        assert "receipt_" not in res.headers[HEADER_X402_SETTLEMENT_PROOF]
    finally:
        app.dependency_overrides.pop(get_payment_verifier, None)


def test_facilitator_receipt_passed_verbatim_as_settlement_proof(client):
    """Verify that facilitator receipt IDs from verifier are attached without modification."""
    facilitator_receipt = "rec_fac_base_sepolia_777888999"

    class FacilitatorVerifier(SellerPaymentVerifierInterface):
        def issue_challenge(self, service_id, amount_units, pay_to):
            return PaymentRequirement(
                version="2.0", network=NETWORK_BASE_SEPOLIA, token=USDC_BASE_SEPOLIA,
                amount=str(amount_units), payTo=pay_to, nonce="nonce_fac", service_id=service_id
            )
        async def verify_and_settle(self, payload, req):
            return SettlementReceipt(tx_hash=None, facilitator_receipt_id=facilitator_receipt, settled_amount_units=int(req.amount))

    app.dependency_overrides[get_payment_verifier] = lambda: FacilitatorVerifier()
    try:
        headers = {
            HEADER_X402_PAYMENT_PAYLOAD: json.dumps({
                "authorization": {"amount": "3000"},
                "signature": "0x123",
                "buyer_address": "0x0000000000000000000000000000000000000000"
            })
        }
        res = client.post("/api/v1/seller/scraping", json={"url": "https://base.org"}, headers=headers)
        assert res.status_code == status.HTTP_200_OK
        assert HEADER_X402_SETTLEMENT_PROOF in res.headers
        assert res.headers[HEADER_X402_SETTLEMENT_PROOF] == facilitator_receipt
    finally:
        app.dependency_overrides.pop(get_payment_verifier, None)


# ==============================================================================
# 6. EXECUTION CONTEXT & IDEMPOTENCY KEY TESTS (Section 7.E)
# ==============================================================================

def test_idempotency_key_forwarded_to_seller_execution_context(client):
    """Verify that Idempotency-Key header is cleanly captured in SellerExecutionContext."""
    captured_context = {}

    class ContextCapturingDataSeller(DataSellerService):
        async def _execute_business_logic(self, payload, context):
            captured_context["idempotency_key"] = context.idempotency_key
            captured_context["request_id"] = context.request_id
            captured_context["service_id"] = context.service_id
            return await super()._execute_business_logic(payload, context)

    class ValidVerifier(SellerPaymentVerifierInterface):
        def issue_challenge(self, service_id, amount_units, pay_to):
            return PaymentRequirement(
                version="2.0", network=NETWORK_BASE_SEPOLIA, token=USDC_BASE_SEPOLIA,
                amount=str(amount_units), payTo=pay_to, nonce="nonce_ctx", service_id=service_id
            )
        async def verify_and_settle(self, payload, req):
            return SettlementReceipt(facilitator_receipt_id="rec_ctx_123", settled_amount_units=int(req.amount))

    app.dependency_overrides[get_data_seller_service] = lambda: ContextCapturingDataSeller()
    app.dependency_overrides[get_payment_verifier] = lambda: ValidVerifier()
    try:
        custom_key = "idemp_test_client_key_999"
        headers = {
            HEADER_X402_PAYMENT_PAYLOAD: json.dumps({
                "authorization": {"amount": "2000"},
                "signature": "0x123",
                "buyer_address": "0x0000000000000000000000000000000000000000"
            }),
            HEADER_IDEMPOTENCY_KEY: custom_key
        }
        res = client.post("/api/v1/seller/data", json={"symbol": "ETH"}, headers=headers)
        assert res.status_code == status.HTTP_200_OK
        assert captured_context["idempotency_key"] == custom_key
        assert captured_context["service_id"] == "data_001"
        assert captured_context["request_id"].startswith("req_")
    finally:
        app.dependency_overrides.pop(get_data_seller_service, None)
        app.dependency_overrides.pop(get_payment_verifier, None)


# ==============================================================================
# 7. EXECUTION FAILURE TESTS (Section 7.D)
# ==============================================================================

def test_confirmed_payment_followed_by_seller_timeout_leaves_no_fake_proof(client):
    """Verify that execution timeout returns HTTP 504 and never fabricates fake proof."""
    import asyncio
    from backend.sellers.common import SellerExecutionTimeoutError

    class SlowService(DataSellerService):
        async def _execute_business_logic(self, payload, context):
            raise SellerExecutionTimeoutError(timeout_seconds=0.01, service_id=self.service_id)

    class ValidVerifier(SellerPaymentVerifierInterface):
        def issue_challenge(self, service_id, amount_units, pay_to):
            return PaymentRequirement(
                version="2.0", network=NETWORK_BASE_SEPOLIA, token=USDC_BASE_SEPOLIA,
                amount=str(amount_units), payTo=pay_to, nonce="nonce_to", service_id=service_id
            )
        async def verify_and_settle(self, payload, req):
            return SettlementReceipt(facilitator_receipt_id="rec_timeout_test", settled_amount_units=int(req.amount))

    app.dependency_overrides[get_data_seller_service] = lambda: SlowService()
    app.dependency_overrides[get_payment_verifier] = lambda: ValidVerifier()
    try:
        headers = {
            HEADER_X402_PAYMENT_PAYLOAD: json.dumps({
                "authorization": {"amount": "2000"},
                "signature": "0x123",
                "buyer_address": "0x0000000000000000000000000000000000000000"
            })
        }
        res = client.post("/api/v1/seller/data", json={"symbol": "ETH"}, headers=headers)
        assert res.status_code == status.HTTP_504_GATEWAY_TIMEOUT
        assert res.json()["error_code"] == "SELLER_TIMEOUT"
        assert HEADER_X402_SETTLEMENT_PROOF not in res.headers
    finally:
        app.dependency_overrides.pop(get_data_seller_service, None)
        app.dependency_overrides.pop(get_payment_verifier, None)


def test_confirmed_payment_followed_by_internal_crash_sanitizes_error(client):
    """Verify that unhandled internal exceptions in seller logic return sanitized 500 without leaking details."""
    class CrashingDataSeller(DataSellerService):
        async def _execute_business_logic(self, payload, context):
            raise Exception("PostgreSQL connection password leak: supersecret123@db.prod")

    class ValidVerifier(SellerPaymentVerifierInterface):
        def issue_challenge(self, service_id, amount_units, pay_to):
            return PaymentRequirement(
                version="2.0", network=NETWORK_BASE_SEPOLIA, token=USDC_BASE_SEPOLIA,
                amount=str(amount_units), payTo=pay_to, nonce="nonce_crash", service_id=service_id
            )
        async def verify_and_settle(self, payload, req):
            return SettlementReceipt(facilitator_receipt_id="rec_crash_test", settled_amount_units=int(req.amount))

    app.dependency_overrides[get_data_seller_service] = lambda: CrashingDataSeller()
    app.dependency_overrides[get_payment_verifier] = lambda: ValidVerifier()
    try:
        headers = {
            HEADER_X402_PAYMENT_PAYLOAD: json.dumps({
                "authorization": {"amount": "2000"},
                "signature": "0x123",
                "buyer_address": "0x0000000000000000000000000000000000000000"
            })
        }
        res = client.post("/api/v1/seller/data", json={"symbol": "ETH"}, headers=headers)
        assert res.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        # Message must be sanitized
        body = res.json()
        assert "supersecret123" not in body["message"]
        assert body["error_code"] == "SELLER_EXECUTION_FAILED"
        assert HEADER_X402_SETTLEMENT_PROOF not in res.headers
    finally:
        app.dependency_overrides.pop(get_data_seller_service, None)
        app.dependency_overrides.pop(get_payment_verifier, None)


def test_verifier_terms_mismatch_network_token_recipient_amount_rejected(client):
    """Verify that verifier rejecting payment terms (network, token, payTo, amount) rejects execution."""
    seller_executed = False

    class TrackingService(DataSellerService):
        async def _execute_business_logic(self, payload, context):
            nonlocal seller_executed
            seller_executed = True
            return await super()._execute_business_logic(payload, context)

    class TermsCheckingVerifier(SellerPaymentVerifierInterface):
        def issue_challenge(self, service_id, amount_units, pay_to):
            return PaymentRequirement(
                version="2.0", network=NETWORK_BASE_SEPOLIA, token=USDC_BASE_SEPOLIA,
                amount=str(amount_units), payTo=pay_to, nonce="nonce_terms", service_id=service_id
            )
        async def verify_and_settle(self, payload, req):
            auth = payload.authorization if isinstance(payload.authorization, dict) else {}
            if auth.get("network") != req.network:
                raise ValueError(f"Network mismatch: {auth.get('network')} != {req.network}")
            if auth.get("token") != req.token:
                raise ValueError(f"Token mismatch: {auth.get('token')} != {req.token}")
            if auth.get("payTo") != req.payTo:
                raise ValueError(f"Recipient mismatch: {auth.get('payTo')} != {req.payTo}")
            if auth.get("amount") != req.amount:
                raise ValueError(f"Amount mismatch: {auth.get('amount')} != {req.amount}")
            return SettlementReceipt(facilitator_receipt_id="rec_ok", settled_amount_units=int(req.amount))

    app.dependency_overrides[get_data_seller_service] = lambda: TrackingService()
    app.dependency_overrides[get_payment_verifier] = lambda: TermsCheckingVerifier()
    try:
        # Case A: Wrong network
        headers_bad_net = {
            HEADER_X402_PAYMENT_PAYLOAD: json.dumps({
                "authorization": {"network": "eip155:1", "token": USDC_BASE_SEPOLIA, "payTo": "0x0000000000000000000000000000000000000001", "amount": "2000"},
                "signature": "0x123", "buyer_address": "0x0000000000000000000000000000000000000000"
            })
        }
        res_net = client.post("/api/v1/seller/data", json={"symbol": "ETH"}, headers=headers_bad_net)
        assert res_net.status_code == status.HTTP_402_PAYMENT_REQUIRED
        assert "Network mismatch" in res_net.json()["message"]
        assert not seller_executed

        # Case B: Wrong token
        headers_bad_token = {
            HEADER_X402_PAYMENT_PAYLOAD: json.dumps({
                "authorization": {"network": NETWORK_BASE_SEPOLIA, "token": "0x9999999999999999999999999999999999999999", "payTo": "0x0000000000000000000000000000000000000001", "amount": "2000"},
                "signature": "0x123", "buyer_address": "0x0000000000000000000000000000000000000000"
            })
        }
        res_tok = client.post("/api/v1/seller/data", json={"symbol": "ETH"}, headers=headers_bad_token)
        assert res_tok.status_code == status.HTTP_402_PAYMENT_REQUIRED
        assert "Token mismatch" in res_tok.json()["message"]
        assert not seller_executed

        # Case C: Wrong recipient (payTo)
        headers_bad_payto = {
            HEADER_X402_PAYMENT_PAYLOAD: json.dumps({
                "authorization": {"network": NETWORK_BASE_SEPOLIA, "token": USDC_BASE_SEPOLIA, "payTo": "0xDeadBeefDeadBeefDeadBeefDeadBeefDeadBeef", "amount": "2000"},
                "signature": "0x123", "buyer_address": "0x0000000000000000000000000000000000000000"
            })
        }
        res_pay = client.post("/api/v1/seller/data", json={"symbol": "ETH"}, headers=headers_bad_payto)
        assert res_pay.status_code == status.HTTP_402_PAYMENT_REQUIRED
        assert "Recipient mismatch" in res_pay.json()["message"]
        assert not seller_executed

        # Case D: Wrong amount (underpayment)
        headers_bad_amt = {
            HEADER_X402_PAYMENT_PAYLOAD: json.dumps({
                "authorization": {"network": NETWORK_BASE_SEPOLIA, "token": USDC_BASE_SEPOLIA, "payTo": "0x0000000000000000000000000000000000000001", "amount": "1000"},
                "signature": "0x123", "buyer_address": "0x0000000000000000000000000000000000000000"
            })
        }
        res_amt = client.post("/api/v1/seller/data", json={"symbol": "ETH"}, headers=headers_bad_amt)
        assert res_amt.status_code == status.HTTP_402_PAYMENT_REQUIRED
        assert "Amount mismatch" in res_amt.json()["message"]
        assert not seller_executed
    finally:
        app.dependency_overrides.pop(get_data_seller_service, None)
        app.dependency_overrides.pop(get_payment_verifier, None)


def test_confirmed_payment_followed_by_invalid_seller_output_fails_closed_502(client):
    """Verify that if payment settles, but seller output fails schema validation, route returns HTTP 502."""
    class CorruptDataSeller(DataSellerService):
        async def _execute_business_logic(self, payload, context) -> dict:
            # Corrupted payload missing price and volume_24h
            return {"symbol": "ETH"}

    class ValidVerifier(SellerPaymentVerifierInterface):
        def issue_challenge(self, service_id, amount_units, pay_to):
            return PaymentRequirement(
                version="2.0", network=NETWORK_BASE_SEPOLIA, token=USDC_BASE_SEPOLIA,
                amount=str(amount_units), payTo=pay_to, nonce="nonce_corrupt", service_id=service_id
            )
        async def verify_and_settle(self, payload, req):
            return SettlementReceipt(facilitator_receipt_id="rec_output_corrupt", settled_amount_units=int(req.amount))

    app.dependency_overrides[get_data_seller_service] = lambda: CorruptDataSeller()
    app.dependency_overrides[get_payment_verifier] = lambda: ValidVerifier()
    try:
        headers = {
            HEADER_X402_PAYMENT_PAYLOAD: json.dumps({
                "authorization": {"amount": "2000"},
                "signature": "0x123",
                "buyer_address": "0x0000000000000000000000000000000000000000"
            })
        }
        res = client.post("/api/v1/seller/data", json={"symbol": "ETH"}, headers=headers)
        assert res.status_code == status.HTTP_502_BAD_GATEWAY
        assert res.json()["error_code"] == "SELLER_OUTPUT_INVALID"
        assert HEADER_X402_SETTLEMENT_PROOF not in res.headers
    finally:
        app.dependency_overrides.pop(get_data_seller_service, None)
        app.dependency_overrides.pop(get_payment_verifier, None)


# ==============================================================================
# 8. FULL LOCAL BUYER-SELLER-LEDGER HANDSHAKE (Section 7.F)
# ==============================================================================

def test_end_to_end_local_buyer_seller_handshake_flow(client):
    """Test full integration: 402 challenge -> payment authorization -> settlement -> seller response -> ledger audit entry."""
    from backend.ledger.models import ledger_repo
    from backend.shared.schemas import LedgerRecordSchema
    from backend.shared.constants import LedgerStatus
    from datetime import datetime, timezone

    facilitator_receipt = "rec_e2e_local_integration_test_888"

    class LocalIntegrationVerifier(SellerPaymentVerifierInterface):
        def issue_challenge(self, service_id, amount_units, pay_to):
            return PaymentRequirement(
                version="2.0", network=NETWORK_BASE_SEPOLIA, token=USDC_BASE_SEPOLIA,
                amount=str(amount_units), payTo=pay_to, nonce="nonce_e2e", service_id=service_id
            )
        async def verify_and_settle(self, payload, req):
            return SettlementReceipt(
                tx_hash=None,
                facilitator_receipt_id=facilitator_receipt,
                settled_at=datetime.now(timezone.utc),
                settled_amount_units=int(req.amount)
            )

    app.dependency_overrides[get_payment_verifier] = lambda: LocalIntegrationVerifier()
    try:
        # Step 1: Client requests without payment header -> Receives HTTP 402
        req_res = client.post("/api/v1/seller/data", json={"symbol": "ETH"})
        assert req_res.status_code == status.HTTP_402_PAYMENT_REQUIRED
        challenge = json.loads(req_res.headers[HEADER_X402_REQUIREMENT])
        assert challenge["service_id"] == "data_001"
        assert challenge["amount"] == "2000"

        # Step 2: Buyer constructs compliant signed payment payload
        idemp_key = "idemp_e2e_integration_001"
        payment_headers = {
            HEADER_X402_PAYMENT_PAYLOAD: json.dumps({
                "authorization": {
                    "network": challenge["network"],
                    "token": challenge["token"],
                    "payTo": challenge["payTo"],
                    "amount": challenge["amount"],
                    "nonce": challenge["nonce"],
                },
                "signature": "0x_e2e_mock_sig_999",
                "buyer_address": "0x0000000000000000000000000000000000000000"
            }),
            HEADER_IDEMPOTENCY_KEY: idemp_key
        }

        # Step 3: Client sends payment payload -> Receives HTTP 200 OK + Settlement Proof
        paid_res = client.post("/api/v1/seller/data", json={"symbol": "ETH"}, headers=payment_headers)
        assert paid_res.status_code == status.HTTP_200_OK
        data = paid_res.json()
        assert data["symbol"] == "ETH"
        assert data["price"] == 2650.50
        assert HEADER_X402_SETTLEMENT_PROOF in paid_res.headers
        settlement_proof = paid_res.headers[HEADER_X402_SETTLEMENT_PROOF]
        assert settlement_proof == facilitator_receipt

        # Step 4: Record in audit ledger
        req_id = f"req_{idemp_key}"
        ledger_record = LedgerRecordSchema(
            request_id=req_id,
            buyer_id="buyer_001",
            seller_id="seller_data_001",
            service_id="data_001",
            listed_price="0.002000",
            amount_paid="0.002000",
            status=LedgerStatus.PAID,
            latency_ms=25.0,
            tx_hash=settlement_proof,
            error_reason=None
        )
        ledger_repo.record_transaction(ledger_record)

        # Step 5: Query audit ledger API to verify record is persistently visible
        ledger_api_res = client.get(f"/api/v1/ledger/{req_id}")
        assert ledger_api_res.status_code == status.HTTP_200_OK
        stored = ledger_api_res.json()
        assert stored["request_id"] == req_id
        assert stored["status"] == "paid"
        assert stored["tx_hash"] == facilitator_receipt
        assert stored["amount_paid"] == "0.002000"
    finally:
        app.dependency_overrides.pop(get_payment_verifier, None)


# ==============================================================================
# 9. ADVANCED PAYMENT BOUNDARY & SECURITY INVARIANT TESTS (Section 11)
# ==============================================================================

def test_service_id_mismatch_fails_closed(client):
    """Verify that a payment payload signed for a different service_id is rejected and never executes seller."""
    seller_executed = False

    class TrackingDataService(DataSellerService):
        async def _execute_business_logic(self, payload, context):
            nonlocal seller_executed
            seller_executed = True
            return await super()._execute_business_logic(payload, context)

    class ServiceIdCheckingVerifier(SellerPaymentVerifierInterface):
        def issue_challenge(self, service_id, amount_units, pay_to):
            return PaymentRequirement(
                version="2.0", network=NETWORK_BASE_SEPOLIA, token=USDC_BASE_SEPOLIA,
                amount=str(amount_units), payTo=pay_to, nonce="nonce_svc", service_id=service_id
            )
        async def verify_and_settle(self, payload, req):
            auth = payload.authorization if isinstance(payload.authorization, dict) else {}
            payload_svc = auth.get("service_id")
            if payload_svc and payload_svc != req.service_id:
                raise ValueError(f"Service ID mismatch: {payload_svc} != {req.service_id}")
            return SettlementReceipt(facilitator_receipt_id="rec_svc_ok", settled_amount_units=int(req.amount))

    app.dependency_overrides[get_data_seller_service] = lambda: TrackingDataService()
    app.dependency_overrides[get_payment_verifier] = lambda: ServiceIdCheckingVerifier()
    try:
        mismatched_payload = {
            HEADER_X402_PAYMENT_PAYLOAD: json.dumps({
                "authorization": {
                    "network": NETWORK_BASE_SEPOLIA,
                    "token": USDC_BASE_SEPOLIA,
                    "payTo": "0x0000000000000000000000000000000000000001",
                    "amount": "2000",
                    "service_id": "inference_001",  # Wrong service! Calling /data which is data_001
                },
                "signature": "0x123",
                "buyer_address": "0x0000000000000000000000000000000000000000"
            })
        }
        res = client.post("/api/v1/seller/data", json={"symbol": "BTC"}, headers=mismatched_payload)
        assert res.status_code == status.HTTP_402_PAYMENT_REQUIRED
        assert "Service ID mismatch" in res.json()["message"]
        assert not seller_executed
    finally:
        app.dependency_overrides.pop(get_data_seller_service, None)
        app.dependency_overrides.pop(get_payment_verifier, None)


def test_replay_or_duplicate_nonce_fails_closed(client):
    """Verify that submitting an already-spent nonce is rejected by the verifier and prevents duplicate seller execution."""
    seller_run_count = 0
    seen_nonces = set()

    class TrackingInferenceService(InferenceSellerService):
        async def _execute_business_logic(self, payload, context):
            nonlocal seller_run_count
            seller_run_count += 1
            return await super()._execute_business_logic(payload, context)

    class ReplayCheckingVerifier(SellerPaymentVerifierInterface):
        def issue_challenge(self, service_id, amount_units, pay_to):
            return PaymentRequirement(
                version="2.0", network=NETWORK_BASE_SEPOLIA, token=USDC_BASE_SEPOLIA,
                amount=str(amount_units), payTo=pay_to, nonce="nonce_replay_test", service_id=service_id
            )
        async def verify_and_settle(self, payload, req):
            auth = payload.authorization if isinstance(payload.authorization, dict) else {}
            nonce = auth.get("nonce", "default_nonce")
            if nonce in seen_nonces:
                raise ValueError(f"Replay detected: nonce '{nonce}' has already been spent.")
            seen_nonces.add(nonce)
            return SettlementReceipt(facilitator_receipt_id=f"rec_nonce_{nonce}", settled_amount_units=int(req.amount))

    app.dependency_overrides[get_inference_seller_service] = lambda: TrackingInferenceService()
    app.dependency_overrides[get_payment_verifier] = lambda: ReplayCheckingVerifier()
    try:
        replay_headers = {
            HEADER_X402_PAYMENT_PAYLOAD: json.dumps({
                "authorization": {
                    "network": NETWORK_BASE_SEPOLIA,
                    "token": USDC_BASE_SEPOLIA,
                    "payTo": "0x0000000000000000000000000000000000000003",
                    "amount": "4000",
                    "nonce": "nonce_spent_once"
                },
                "signature": "0x_sig_replay_1",
                "buyer_address": "0x0000000000000000000000000000000000000000"
            })
        }
        # First call: succeeds
        res1 = client.post("/api/v1/seller/inference", json={"prompt": "Hello"}, headers=replay_headers)
        assert res1.status_code == status.HTTP_200_OK
        assert seller_run_count == 1

        # Second call (replay with exact same nonce): fails closed
        res2 = client.post("/api/v1/seller/inference", json={"prompt": "Hello"}, headers=replay_headers)
        assert res2.status_code == status.HTTP_402_PAYMENT_REQUIRED
        assert "Replay detected" in res2.json()["message"]
        # Invariant: seller was NOT executed a second time
        assert seller_run_count == 1
    finally:
        app.dependency_overrides.pop(get_inference_seller_service, None)
        app.dependency_overrides.pop(get_payment_verifier, None)


def test_concurrent_seller_requests_handling(client):
    """Verify that concurrent seller requests each generate unique nonces and operate independently."""
    from concurrent.futures import ThreadPoolExecutor

    def send_challenge_request(symbol: str):
        return client.post("/api/v1/seller/data", json={"symbol": symbol})

    symbols = ["ETH", "BTC", "SOL", "LINK", "AVAX"]
    with ThreadPoolExecutor(max_workers=5) as executor:
        responses = list(executor.map(send_challenge_request, symbols))

    assert len(responses) == 5
    nonces = set()
    for res in responses:
        assert res.status_code == status.HTTP_402_PAYMENT_REQUIRED
        req = json.loads(res.headers[HEADER_X402_REQUIREMENT])
        assert req["service_id"] == "data_001"
        nonces.add(req["nonce"])

    # All generated nonces in concurrent requests must be distinct
    assert len(nonces) == 5


def test_no_credential_or_private_key_leakage_in_error_responses(client):
    """Verify that under any payment error or failure, secrets/private keys are never leaked in responses."""
    class CrashingVerifier(SellerPaymentVerifierInterface):
        def issue_challenge(self, service_id, amount_units, pay_to):
            return PaymentRequirement(
                version="2.0", network=NETWORK_BASE_SEPOLIA, token=USDC_BASE_SEPOLIA,
                amount=str(amount_units), payTo=pay_to, nonce="nonce_sec", service_id=service_id
            )
        async def verify_and_settle(self, payload, req):
            # Simulate an internal DB/RPC exception that might contain private credentials
            raise RuntimeError("Database connection string postgres://admin:SuperSecretPassword123@db:5432/db failed")

    app.dependency_overrides[get_payment_verifier] = lambda: CrashingVerifier()
    try:
        headers = {
            HEADER_X402_PAYMENT_PAYLOAD: json.dumps({
                "authorization": {"amount": "2000"},
                "signature": "0x123",
                "buyer_address": "0x0000000000000000000000000000000000000000"
            })
        }
        res = client.post("/api/v1/seller/data", json={"symbol": "BTC"}, headers=headers)
        assert res.status_code == status.HTTP_402_PAYMENT_REQUIRED
        raw_text = res.text
        assert "SuperSecretPassword123" not in raw_text
        assert "postgres://" not in raw_text
    finally:
        app.dependency_overrides.pop(get_payment_verifier, None)
