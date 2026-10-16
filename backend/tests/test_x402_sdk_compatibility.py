"""Official x402 Protocol & SDK Compatibility Test Suite (Phase 2A).

Validates:
1. Installation and runtime presence of x402, web3, and eth-account.
2. Official x402 schemas (PaymentRequired, PaymentRequirements, PaymentPayload, SettleResponse).
3. Official wire format encoding and decoding (PAYMENT-REQUIRED, PAYMENT-SIGNATURE, PAYMENT-RESPONSE).
4. Bidirectional schema and header translation in X402Adapter.
5. Real ECDSA/EIP-712 signing and cryptographic verification using eth_account.
6. Fail-closed security boundaries on corrupted or invalid payloads.
"""
import pytest

x402 = pytest.importorskip("x402", reason="Official x402 SDK not installed")
web3 = pytest.importorskip("web3", reason="web3 package not installed")
eth_account = pytest.importorskip("eth_account", reason="eth_account package not installed")

from eth_account import Account
from eth_account.messages import encode_defunct

from backend.shared.constants import (
    NETWORK_BASE_SEPOLIA,
    USDC_BASE_SEPOLIA,
    HEADER_X402_REQUIREMENT,
    HEADER_X402_PAYMENT_PAYLOAD,
    HEADER_X402_SETTLEMENT_PROOF,
)
from backend.shared.schemas import PaymentRequirement
from backend.payments.x402_adapter import (
    X402Adapter,
    HEADER_OFFICIAL_PAYMENT_REQUIRED,
    HEADER_OFFICIAL_PAYMENT_SIGNATURE,
    HEADER_OFFICIAL_PAYMENT_RESPONSE,
    OFFICIAL_X402_AVAILABLE,
)
from backend.payments.errors import PaymentEngineError

from x402 import (
    PaymentRequired as OfficialPaymentRequired,
    PaymentRequirements as OfficialPaymentRequirements,
    PaymentPayload as OfficialPaymentPayload,
    SettleResponse as OfficialSettleResponse,
)
import x402.http as x402_http


def test_official_x402_dependencies_installed_and_versioned():
    """Verify that official x402, web3, and eth-account packages are installed with valid versions."""
    assert OFFICIAL_X402_AVAILABLE is True
    assert hasattr(x402, "__version__") or hasattr(x402, "X402_VERSION")
    assert web3.__version__ >= "6.19.0"
    assert eth_account.__version__ >= "0.11.0"


def test_official_payment_requirement_schema_and_wire_roundtrip():
    """Test translating application PaymentRequirement to official PaymentRequired and roundtripping."""
    adapter = X402Adapter(test_mode=True)
    req = PaymentRequirement(
        network=NETWORK_BASE_SEPOLIA,
        token=USDC_BASE_SEPOLIA,
        payTo="0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        amount="2000",
        nonce="nonce_test_official_01",
        service_id="data_001",
    )

    # 1. Translate to official PaymentRequired
    official_pr = adapter.to_official_payment_required(req)
    assert isinstance(official_pr, OfficialPaymentRequired)
    assert official_pr.x402_version == 2
    assert len(official_pr.accepts) == 1
    assert official_pr.accepts[0].network == NETWORK_BASE_SEPOLIA
    assert official_pr.accepts[0].asset == USDC_BASE_SEPOLIA
    assert official_pr.accepts[0].amount == "2000"
    assert official_pr.accepts[0].pay_to == "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"

    # 2. Encode to official base64 wire header
    wire_header = adapter.encode_official_requirement(req)
    assert isinstance(wire_header, str)
    assert len(wire_header) > 20

    # 3. Decode back from official base64 header
    decoded_req = adapter.decode_official_requirement(wire_header)
    assert decoded_req.network == req.network
    assert decoded_req.token == req.token
    assert decoded_req.amount == req.amount
    assert decoded_req.payTo == req.payTo
    assert decoded_req.nonce == req.nonce
    assert decoded_req.service_id == req.service_id


def test_official_payment_payload_schema_and_wire_roundtrip():
    """Test translating application payment payload to official PaymentPayload and roundtripping."""
    adapter = X402Adapter(test_mode=True)
    req = PaymentRequirement(
        network=NETWORK_BASE_SEPOLIA,
        token=USDC_BASE_SEPOLIA,
        payTo="0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        amount="3000",
        nonce="nonce_payload_roundtrip_01",
        service_id="scraping_001",
    )
    app_payload = adapter.create_payment_payload(req, idempotency_key="idemp_payload_001")

    # 1. Translate to official PaymentPayload
    official_pl = adapter.to_official_payment_payload(app_payload, req)
    assert isinstance(official_pl, OfficialPaymentPayload)
    assert official_pl.x402_version == 2
    assert official_pl.accepted.amount == "3000"

    # 2. Encode to official base64 PAYMENT-SIGNATURE header
    wire_sig = adapter.encode_official_payload(app_payload, req)
    assert isinstance(wire_sig, str)

    # 3. Decode back from official base64 header
    recovered_payload, accepted_req = adapter.decode_official_payload(wire_sig)
    assert recovered_payload["signature"] == app_payload["signature"]
    assert accepted_req.amount == "3000"
    assert accepted_req.token == USDC_BASE_SEPOLIA


def test_official_settle_response_schema_and_wire_roundtrip():
    """Test official SettleResponse construction, base64 header encoding, and proof extraction."""
    adapter = X402Adapter(test_mode=True)
    expected_tx = "0x" + "b" * 64
    settle_resp = OfficialSettleResponse(
        success=True,
        transaction=expected_tx,
        network=NETWORK_BASE_SEPOLIA,
        amount="2000",
        payer="0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
    )

    encoded_hdr = x402_http.encode_payment_response_header(settle_resp)
    assert isinstance(encoded_hdr, str)

    # Test extraction via adapter
    headers = {HEADER_OFFICIAL_PAYMENT_RESPONSE: encoded_hdr}
    extracted_proof = adapter.extract_settlement_proof(headers)
    assert extracted_proof == expected_tx


def test_adapter_handles_official_and_custom_challenge_headers():
    """Verify adapter seamlessly parses challenges from official SDK header and custom header."""
    adapter = X402Adapter(test_mode=True)
    req = PaymentRequirement(
        network=NETWORK_BASE_SEPOLIA,
        token=USDC_BASE_SEPOLIA,
        payTo="0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        amount="5000",
        nonce="nonce_challenge_001",
        service_id="inference_001",
    )

    # Case A: Official PAYMENT-REQUIRED base64 header
    official_hdr = adapter.encode_official_requirement(req)
    parsed_official = adapter.parse_challenge_from_headers({HEADER_OFFICIAL_PAYMENT_REQUIRED: official_hdr})
    assert parsed_official.amount == "5000"
    assert parsed_official.service_id == "inference_001"

    # Case B: Custom application X-402-Requirement JSON header
    custom_hdr = req.model_dump_json()
    parsed_custom = adapter.parse_challenge_from_headers({HEADER_X402_REQUIREMENT: custom_hdr})
    assert parsed_custom.amount == "5000"
    assert parsed_custom.nonce == "nonce_challenge_001"


def test_adapter_emits_both_official_and_custom_payment_headers():
    """Verify build_payment_headers emits both PAYMENT-SIGNATURE and X-402-Payment-Payload."""
    adapter = X402Adapter(test_mode=True)
    req = PaymentRequirement(
        network=NETWORK_BASE_SEPOLIA,
        token=USDC_BASE_SEPOLIA,
        payTo="0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        amount="2000",
        nonce="nonce_headers_test",
        service_id="data_001",
    )
    payload = adapter.create_payment_payload(req, idempotency_key="key_headers_001")

    headers = adapter.build_payment_headers(payload, req, idempotency_key="key_headers_001")

    # Must contain custom header for internal Member 2 compatibility
    assert HEADER_X402_PAYMENT_PAYLOAD in headers
    # Must contain official header for official x402 compatibility
    assert HEADER_OFFICIAL_PAYMENT_SIGNATURE in headers
    # Must contain idempotency key
    assert headers["Idempotency-Key"] == "key_headers_001"


def test_live_signing_and_signature_verification_with_eth_account():
    """Test live ECDSA signing with a real eth_account private key and verify signature recovery."""
    test_account = Account.create()
    test_key_hex = test_account.key.hex()
    if not test_key_hex.startswith("0x"):
        test_key_hex = f"0x{test_key_hex}"

    adapter = X402Adapter(test_mode=False)
    adapter.buyer_address = test_account.address
    adapter.buyer_private_key = test_key_hex

    req = PaymentRequirement(
        network=NETWORK_BASE_SEPOLIA,
        token=USDC_BASE_SEPOLIA,
        payTo="0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        amount="2000",
        nonce="nonce_live_sig_001",
        service_id="data_001",
    )

    payload = adapter.create_payment_payload(req, idempotency_key="key_live_test")
    signature = payload["signature"]

    # Verify signature format
    assert signature.startswith("0x")
    assert len(signature) == 132  # 65 bytes = 130 hex chars + 0x

    # Verify cryptographic recovery of the signer address
    import json
    msg_str = json.dumps(payload["authorization"], sort_keys=True)
    msg = encode_defunct(text=msg_str)
    recovered_signer = Account.recover_message(msg, signature=signature)
    assert recovered_signer.lower() == test_account.address.lower()


def test_malformed_official_header_fails_closed():
    """Verify that corrupt or invalid official headers fail closed with PaymentEngineError."""
    adapter = X402Adapter(test_mode=True)

    with pytest.raises(PaymentEngineError) as exc_info:
        adapter.decode_official_requirement("not-valid-base64-content!@#$")
    assert "Failed to decode official x402" in str(exc_info.value)

    with pytest.raises(PaymentEngineError) as exc_info:
        adapter.decode_official_payload("corrupt-signature-header-value")
    assert "Failed to decode official x402" in str(exc_info.value)
