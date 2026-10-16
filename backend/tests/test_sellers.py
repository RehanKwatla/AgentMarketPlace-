"""Tests for Seller Microservices and x402 Challenge Protocol."""
import json
from fastapi import status
from backend.shared.constants import (
    HEADER_X402_REQUIREMENT,
    HEADER_X402_PAYMENT_PAYLOAD,
    HEADER_X402_SETTLEMENT_PROOF,
    NETWORK_BASE_SEPOLIA,
)


def test_data_seller_402_challenge(client):
    response = client.post(
        "/api/v1/seller/data",
        json={"symbol": "ETH"}
    )
    assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED
    assert HEADER_X402_REQUIREMENT in response.headers

    req = json.loads(response.headers[HEADER_X402_REQUIREMENT])
    assert req["version"] == "2.0"
    assert req["network"] == NETWORK_BASE_SEPOLIA
    assert req["service_id"] == "data_001"
    assert req["amount"] == "2000"
    assert "nonce" in req
    assert "payTo" in req


def test_scraping_seller_402_challenge(client):
    response = client.post(
        "/api/v1/seller/scraping",
        json={"url": "https://ethereum.org"}
    )
    assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED
    assert HEADER_X402_REQUIREMENT in response.headers

    req = json.loads(response.headers[HEADER_X402_REQUIREMENT])
    assert req["service_id"] == "scraping_001"
    assert req["amount"] == "3000"


def test_inference_seller_402_challenge(client):
    response = client.post(
        "/api/v1/seller/inference",
        json={"prompt": "Summarize market dynamics", "max_tokens": 100}
    )
    assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED
    assert HEADER_X402_REQUIREMENT in response.headers

    req = json.loads(response.headers[HEADER_X402_REQUIREMENT])
    assert req["service_id"] == "inference_001"
    assert req["amount"] == "4000"


def test_seller_input_validation_error(client):
    # Missing required field "symbol"
    response = client.post("/api/v1/seller/data", json={})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_seller_paid_execution_without_verifier_fails_closed(client):
    """Verify route returns HTTP 503 Service Unavailable when concrete verifier is not configured."""
    headers = {
        HEADER_X402_PAYMENT_PAYLOAD: json.dumps({
            "authorization": {"amount": "2000"},
            "signature": "0x123",
            "buyer_address": "0x0000000000000000000000000000000000000000"
        })
    }
    response = client.post(
        "/api/v1/seller/data",
        json={"symbol": "ETH"},
        headers=headers
    )
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    err = response.json()
    assert err["error_code"] == "PAYMENT_VERIFIER_UNAVAILABLE"


def test_seller_paid_execution_malformed_payload(client):
    """Verify route rejects malformed JSON or invalid PaymentPayload with HTTP 400."""
    headers = {
        HEADER_X402_PAYMENT_PAYLOAD: "not_valid_json_payload"
    }
    response = client.post(
        "/api/v1/seller/data",
        json={"symbol": "ETH"},
        headers=headers
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    err = response.json()
    assert err["error_code"] == "PAYMENT_PAYLOAD_INVALID"


def test_seller_paid_execution_arbitrary_unstructured_payload_rejected(client):
    """Verify route rejects arbitrary or unstructured JSON payloads that fail PaymentPayload schema."""
    # Arbitrary dict lacking authorization, signature, buyer_address
    headers = {
        HEADER_X402_PAYMENT_PAYLOAD: json.dumps({"arbitrary_key": "unverified_data", "price": 100})
    }
    response = client.post("/api/v1/seller/data", json={"symbol": "BTC"}, headers=headers)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error_code"] == "PAYMENT_PAYLOAD_INVALID"

    # Empty JSON object
    headers_empty = {
        HEADER_X402_PAYMENT_PAYLOAD: "{}"
    }
    response = client.post("/api/v1/seller/scraping", json={"url": "https://example.com"}, headers=headers_empty)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error_code"] == "PAYMENT_PAYLOAD_INVALID"


def test_all_seller_routes_fail_closed_without_verifier(client):
    """Verify scraping and inference routes fail closed with HTTP 503 when verifier is unavailable."""
    valid_payload_header = {
        HEADER_X402_PAYMENT_PAYLOAD: json.dumps({
            "authorization": {"amount": "3000"},
            "signature": "0x123",
            "buyer_address": "0x0000000000000000000000000000000000000000"
        })
    }
    # Scraping route
    res_scraping = client.post(
        "/api/v1/seller/scraping",
        json={"url": "https://base.org"},
        headers=valid_payload_header
    )
    assert res_scraping.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert res_scraping.json()["error_code"] == "PAYMENT_VERIFIER_UNAVAILABLE"

    # Inference route
    valid_payload_header[HEADER_X402_PAYMENT_PAYLOAD] = json.dumps({
        "authorization": {"amount": "4000"},
        "signature": "0x123",
        "buyer_address": "0x0000000000000000000000000000000000000000"
    })
    res_inf = client.post(
        "/api/v1/seller/inference",
        json={"prompt": "Analyze", "max_tokens": 50},
        headers=valid_payload_header
    )
    assert res_inf.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert res_inf.json()["error_code"] == "PAYMENT_VERIFIER_UNAVAILABLE"


def test_seller_paid_execution_with_mock_verifier(client):
    """[MOCK-BASED PAYMENT TEST] Verify route executes seller and attaches settlement proof when mock verifier authorizes payment."""
    from backend.main import app
    from backend.sellers.routes import get_payment_verifier
    from backend.payments.interfaces import SellerPaymentVerifierInterface
    from backend.shared.schemas import PaymentPayload, PaymentRequirement, SettlementReceipt

    class MockSellerPaymentVerifier(SellerPaymentVerifierInterface):
        def issue_challenge(self, service_id: str, amount_units: int, pay_to: str) -> PaymentRequirement:
            return PaymentRequirement(
                version="2.0",
                network="eip155:84532",
                token="0x036CbD53842c5426634e7929541eC2318f3dCF7e",
                amount=str(amount_units),
                payTo=pay_to,
                nonce="nonce_test_123",
                service_id=service_id
            )

        async def verify_and_settle(self, payload: PaymentPayload, requirement: PaymentRequirement) -> SettlementReceipt:
            # Return valid mock settlement receipt
            return SettlementReceipt(
                facilitator_receipt_id="rec_fac_999888",
                settled_amount_units=int(requirement.amount)
            )

    app.dependency_overrides[get_payment_verifier] = lambda: MockSellerPaymentVerifier()

    try:
        headers = {
            HEADER_X402_PAYMENT_PAYLOAD: json.dumps({
                "authorization": {"amount": "2000"},
                "signature": "0x123",
                "buyer_address": "0x0000000000000000000000000000000000000000"
            })
        }
        response = client.post(
            "/api/v1/seller/data",
            json={"symbol": "ETH"},
            headers=headers
        )
        assert response.status_code == status.HTTP_200_OK
        assert HEADER_X402_SETTLEMENT_PROOF in response.headers
        assert response.headers[HEADER_X402_SETTLEMENT_PROOF] == "rec_fac_999888"
        data = response.json()
        assert data["symbol"] == "ETH"
        assert data["price"] > 0
    finally:
        app.dependency_overrides.pop(get_payment_verifier, None)


def test_seller_paid_execution_verifier_rejection(client):
    """[MOCK-BASED PAYMENT TEST] Verify route returns HTTP 402 and aborts business logic when mock verifier rejects authorization."""
    from backend.main import app
    from backend.sellers.routes import get_payment_verifier
    from backend.payments.interfaces import SellerPaymentVerifierInterface
    from backend.shared.schemas import PaymentPayload, PaymentRequirement, SettlementReceipt

    class RejectingPaymentVerifier(SellerPaymentVerifierInterface):
        def issue_challenge(self, service_id: str, amount_units: int, pay_to: str) -> PaymentRequirement:
            return PaymentRequirement(
                version="2.0",
                network="eip155:84532",
                token="0x036CbD53842c5426634e7929541eC2318f3dCF7e",
                amount=str(amount_units),
                payTo=pay_to,
                nonce="nonce_test_123",
                service_id=service_id
            )

        async def verify_and_settle(self, payload: PaymentPayload, requirement: PaymentRequirement) -> SettlementReceipt:
            raise ValueError("Signature expired or budget exceeded on facilitator")

    app.dependency_overrides[get_payment_verifier] = lambda: RejectingPaymentVerifier()

    try:
        headers = {
            HEADER_X402_PAYMENT_PAYLOAD: json.dumps({
                "authorization": {"amount": "2000"},
                "signature": "0x123",
                "buyer_address": "0x0000000000000000000000000000000000000000"
            })
        }
        response = client.post(
            "/api/v1/seller/data",
            json={"symbol": "ETH"},
            headers=headers
        )
        assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED
        err = response.json()
        assert err["error_code"] == "PAYMENT_AUTHORIZATION_FAILED"
        assert "Signature expired" in err["message"]
    finally:
        app.dependency_overrides.pop(get_payment_verifier, None)


def test_mock_based_verifier_exception_fails_with_402(client):
    """[MOCK-BASED PAYMENT TEST] Verify unexpected verifier exception fails closed with HTTP 402 and aborts business logic."""
    from backend.main import app
    from backend.sellers.routes import get_payment_verifier
    from backend.payments.interfaces import SellerPaymentVerifierInterface
    from backend.shared.schemas import PaymentPayload, PaymentRequirement, SettlementReceipt

    class CrashingPaymentVerifier(SellerPaymentVerifierInterface):
        def issue_challenge(self, service_id: str, amount_units: int, pay_to: str) -> PaymentRequirement:
            return PaymentRequirement(
                version="2.0", network="eip155:84532", token="0x036CbD53842c5426634e7929541eC2318f3dCF7e",
                amount=str(amount_units), payTo=pay_to, nonce="nonce_err", service_id=service_id
            )

        async def verify_and_settle(self, payload: PaymentPayload, requirement: PaymentRequirement) -> SettlementReceipt:
            raise RuntimeError("Facilitator node RPC network connection dropped")

    app.dependency_overrides[get_payment_verifier] = lambda: CrashingPaymentVerifier()

    try:
        headers = {
            HEADER_X402_PAYMENT_PAYLOAD: json.dumps({
                "authorization": {"amount": "2000"},
                "signature": "0x123",
                "buyer_address": "0x0000000000000000000000000000000000000000"
            })
        }
        response = client.post(
            "/api/v1/seller/data",
            json={"symbol": "ETH"},
            headers=headers
        )
        assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED
        err = response.json()
        assert err["error_code"] == "PAYMENT_AUTHORIZATION_FAILED"
        assert "Facilitator node RPC network connection dropped" in err["message"]
    finally:
        app.dependency_overrides.pop(get_payment_verifier, None)


def test_mock_based_seller_failure_does_not_attach_settlement_proof(client):
    """[MOCK-BASED PAYMENT TEST] Verify that when seller execution fails after payment, no settlement proof header is attached."""
    from backend.main import app
    from backend.sellers.dependencies import get_data_seller_service
    from backend.sellers.routes import get_payment_verifier
    from backend.sellers.data_seller import DataSellerService
    from backend.sellers.schemas import DataSellerInput, DataSellerOutput
    from backend.payments.interfaces import SellerPaymentVerifierInterface
    from backend.shared.schemas import PaymentPayload, PaymentRequirement, SettlementReceipt

    class CrashingSellerService(DataSellerService):
        async def _execute_business_logic(self, payload: DataSellerInput, context) -> DataSellerOutput:
            raise RuntimeError("Downstream data feed crashed")

    class MockVerifier(SellerPaymentVerifierInterface):
        def issue_challenge(self, service_id, amount_units, pay_to):
            return PaymentRequirement(
                version="2.0", network="eip155:84532", token="0x036CbD53842c5426634e7929541eC2318f3dCF7e",
                amount=str(amount_units), payTo=pay_to, nonce="nonce_crash", service_id=service_id
            )
        async def verify_and_settle(self, payload, req):
            return SettlementReceipt(facilitator_receipt_id="rec_settled_123", settled_amount_units=int(req.amount))

    app.dependency_overrides[get_data_seller_service] = lambda: CrashingSellerService()
    app.dependency_overrides[get_payment_verifier] = lambda: MockVerifier()

    try:
        headers = {
            HEADER_X402_PAYMENT_PAYLOAD: json.dumps({
                "authorization": {"amount": "2000"},
                "signature": "0x123",
                "buyer_address": "0x0000000000000000000000000000000000000000"
            })
        }
        response = client.post("/api/v1/seller/data", json={"symbol": "ETH"}, headers=headers)
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        # CRITICAL SAFETY CHECK: No settlement proof header may be returned on seller failure
        assert HEADER_X402_SETTLEMENT_PROOF not in response.headers
    finally:
        app.dependency_overrides.pop(get_data_seller_service, None)
        app.dependency_overrides.pop(get_payment_verifier, None)


def test_mock_based_scraping_and_inference_paid_execution(client):
    """[MOCK-BASED PAYMENT TEST] Verify scraping and inference seller routes execute and settle properly with mock verifier."""
    from backend.main import app
    from backend.sellers.routes import get_payment_verifier
    from backend.payments.interfaces import SellerPaymentVerifierInterface
    from backend.shared.schemas import PaymentPayload, PaymentRequirement, SettlementReceipt

    class MockVerifier(SellerPaymentVerifierInterface):
        def issue_challenge(self, service_id, amount_units, pay_to):
            return PaymentRequirement(
                version="2.0", network="eip155:84532", token="0x036CbD53842c5426634e7929541eC2318f3dCF7e",
                amount=str(amount_units), payTo=pay_to, nonce="nonce_ok", service_id=service_id
            )
        async def verify_and_settle(self, payload, req):
            return SettlementReceipt(facilitator_receipt_id=f"rec_{req.service_id}", settled_amount_units=int(req.amount))

    app.dependency_overrides[get_payment_verifier] = lambda: MockVerifier()

    try:
        # Scraping execution
        scraping_headers = {
            HEADER_X402_PAYMENT_PAYLOAD: json.dumps({
                "authorization": {"amount": "3000"},
                "signature": "0x123",
                "buyer_address": "0x0000000000000000000000000000000000000000"
            })
        }
        res_scraping = client.post(
            "/api/v1/seller/scraping",
            json={"url": "https://ethereum.org"},
            headers=scraping_headers
        )
        assert res_scraping.status_code == status.HTTP_200_OK
        assert res_scraping.headers[HEADER_X402_SETTLEMENT_PROOF] == "rec_scraping_001"
        assert res_scraping.json()["url"] == "https://ethereum.org"

        # Inference execution
        inf_headers = {
            HEADER_X402_PAYMENT_PAYLOAD: json.dumps({
                "authorization": {"amount": "4000"},
                "signature": "0x123",
                "buyer_address": "0x0000000000000000000000000000000000000000"
            })
        }
        res_inf = client.post(
            "/api/v1/seller/inference",
            json={"prompt": "Summarize", "max_tokens": 100},
            headers=inf_headers
        )
        assert res_inf.status_code == status.HTTP_200_OK
        assert res_inf.headers[HEADER_X402_SETTLEMENT_PROOF] == "rec_inference_001"
        assert "Analytical Synthesis" in res_inf.json()["response"]
    finally:
        app.dependency_overrides.pop(get_payment_verifier, None)




def test_seller_route_dependency_override(client):
    """[MOCK-BASED PAYMENT TEST] Verify route leverages FastAPI dependency injection and respects overrides."""
    from backend.main import app
    from backend.sellers.dependencies import get_data_seller_service
    from backend.sellers.routes import get_payment_verifier
    from backend.sellers.data_seller import DataSellerService
    from backend.sellers.schemas import DataSellerInput, DataSellerOutput
    from backend.payments.interfaces import SellerPaymentVerifierInterface
    from backend.shared.schemas import PaymentPayload, PaymentRequirement, SettlementReceipt

    class CustomDataSellerService(DataSellerService):
        async def _execute_business_logic(self, payload: DataSellerInput, context) -> DataSellerOutput:
            return DataSellerOutput(
                symbol="OVERRIDE",
                price=9999.99,
                volume_24h=100.0,
                timestamp="2026-10-16T12:00:00Z"
            )

    class MockVerifier(SellerPaymentVerifierInterface):
        def issue_challenge(self, service_id, amount_units, pay_to):
            return PaymentRequirement(
                version="2.0", network="eip155:84532", token="0x036CbD53842c5426634e7929541eC2318f3dCF7e",
                amount=str(amount_units), payTo=pay_to, nonce="nonce_override", service_id=service_id
            )
        async def verify_and_settle(self, payload, req):
            return SettlementReceipt(facilitator_receipt_id="rec_override", settled_amount_units=int(req.amount))

    app.dependency_overrides[get_data_seller_service] = lambda: CustomDataSellerService()
    app.dependency_overrides[get_payment_verifier] = lambda: MockVerifier()

    try:
        headers = {
            HEADER_X402_PAYMENT_PAYLOAD: json.dumps({
                "authorization": {"amount": "2000"},
                "signature": "0x123",
                "buyer_address": "0x0000000000000000000000000000000000000000"
            })
        }
        response = client.post("/api/v1/seller/data", json={"symbol": "BTC"}, headers=headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["symbol"] == "OVERRIDE"
        assert data["price"] == 9999.99
    finally:
        app.dependency_overrides.pop(get_data_seller_service, None)
        app.dependency_overrides.pop(get_payment_verifier, None)


def test_seller_route_timeout_error_handling(client):
    """[MOCK-BASED PAYMENT TEST] Verify route returns HTTP 504 on execution timeout."""
    import asyncio
    from backend.main import app
    from backend.sellers.dependencies import get_data_seller_service
    from backend.sellers.routes import get_payment_verifier
    from backend.sellers.data_seller import DataSellerService
    from backend.sellers.schemas import DataSellerInput, DataSellerOutput
    from backend.payments.interfaces import SellerPaymentVerifierInterface
    from backend.shared.schemas import PaymentPayload, PaymentRequirement, SettlementReceipt

    class SlowDataSellerService(DataSellerService):
        def __init__(self):
            super().__init__()
            self.default_timeout_seconds = 0.05

        async def _execute_business_logic(self, payload: DataSellerInput, context) -> DataSellerOutput:
            await asyncio.sleep(0.2)
            return DataSellerOutput(symbol="LATE", price=1.0, volume_24h=1.0, timestamp="now")

    class MockVerifier(SellerPaymentVerifierInterface):
        def issue_challenge(self, service_id, amount_units, pay_to):
            return PaymentRequirement(
                version="2.0", network="eip155:84532", token="0x036CbD53842c5426634e7929541eC2318f3dCF7e",
                amount=str(amount_units), payTo=pay_to, nonce="nonce_slow", service_id=service_id
            )
        async def verify_and_settle(self, payload, req):
            return SettlementReceipt(facilitator_receipt_id="rec_slow", settled_amount_units=int(req.amount))

    app.dependency_overrides[get_data_seller_service] = lambda: SlowDataSellerService()
    app.dependency_overrides[get_payment_verifier] = lambda: MockVerifier()

    try:
        headers = {
            HEADER_X402_PAYMENT_PAYLOAD: json.dumps({
                "authorization": {"amount": "2000"},
                "signature": "0x123",
                "buyer_address": "0x0000000000000000000000000000000000000000"
            })
        }
        response = client.post("/api/v1/seller/data", json={"symbol": "ETH"}, headers=headers)
        assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT
        err = response.json()
        assert err["error_code"] == "SELLER_TIMEOUT"
        assert err["retryable"] is True
    finally:
        app.dependency_overrides.pop(get_data_seller_service, None)
        app.dependency_overrides.pop(get_payment_verifier, None)


def test_seller_route_output_validation_error_handling(client):
    """[MOCK-BASED PAYMENT TEST] Verify route returns HTTP 502 on invalid seller output schema."""
    from backend.main import app
    from backend.sellers.dependencies import get_data_seller_service
    from backend.sellers.routes import get_payment_verifier
    from backend.sellers.data_seller import DataSellerService
    from backend.sellers.schemas import DataSellerInput
    from backend.payments.interfaces import SellerPaymentVerifierInterface
    from backend.shared.schemas import PaymentPayload, PaymentRequirement, SettlementReceipt

    class BadOutputSellerService(DataSellerService):
        async def _execute_business_logic(self, payload: DataSellerInput, context) -> dict:
            # Missing required price and volume fields
            return {"symbol": "BAD"}

    class MockVerifier(SellerPaymentVerifierInterface):
        def issue_challenge(self, service_id, amount_units, pay_to):
            return PaymentRequirement(
                version="2.0", network="eip155:84532", token="0x036CbD53842c5426634e7929541eC2318f3dCF7e",
                amount=str(amount_units), payTo=pay_to, nonce="nonce_bad", service_id=service_id
            )
        async def verify_and_settle(self, payload, req):
            return SettlementReceipt(facilitator_receipt_id="rec_bad", settled_amount_units=int(req.amount))

    app.dependency_overrides[get_data_seller_service] = lambda: BadOutputSellerService()
    app.dependency_overrides[get_payment_verifier] = lambda: MockVerifier()

    try:
        headers = {
            HEADER_X402_PAYMENT_PAYLOAD: json.dumps({
                "authorization": {"amount": "2000"},
                "signature": "0x123",
                "buyer_address": "0x0000000000000000000000000000000000000000"
            })
        }
        response = client.post("/api/v1/seller/data", json={"symbol": "ETH"}, headers=headers)
        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        err = response.json()
        assert err["error_code"] == "SELLER_OUTPUT_INVALID"
    finally:
        app.dependency_overrides.pop(get_data_seller_service, None)
        app.dependency_overrides.pop(get_payment_verifier, None)


def test_mock_based_verifier_none_receipt_fails_closed(client):
    """[MOCK-BASED PAYMENT TEST] Verify route fails closed with HTTP 402 if verifier returns None instead of receipt."""
    from backend.main import app
    from backend.sellers.routes import get_payment_verifier
    from backend.payments.interfaces import SellerPaymentVerifierInterface
    from backend.shared.schemas import PaymentRequirement

    class NoneReturningVerifier(SellerPaymentVerifierInterface):
        def issue_challenge(self, service_id, amount_units, pay_to):
            return PaymentRequirement(
                version="2.0", network="eip155:84532", token="0x036CbD53842c5426634e7929541eC2318f3dCF7e",
                amount=str(amount_units), payTo=pay_to, nonce="nonce_none", service_id=service_id
            )
        async def verify_and_settle(self, payload, req):
            return None  # No settlement receipt returned

    app.dependency_overrides[get_payment_verifier] = lambda: NoneReturningVerifier()

    try:
        headers = {
            HEADER_X402_PAYMENT_PAYLOAD: json.dumps({
                "authorization": {"amount": "2000"},
                "signature": "0x123",
                "buyer_address": "0x0000000000000000000000000000000000000000"
            })
        }
        response = client.post("/api/v1/seller/data", json={"symbol": "ETH"}, headers=headers)
        assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED
        err = response.json()
        assert err["error_code"] == "PAYMENT_AUTHORIZATION_FAILED"
        assert "no settlement receipt produced" in err["message"]
        assert HEADER_X402_SETTLEMENT_PROOF not in response.headers
    finally:
        app.dependency_overrides.pop(get_payment_verifier, None)


def test_seller_logic_never_executed_on_unauthorized_payment(client):
    """[MOCK-BASED PAYMENT TEST] Verify seller business logic is NEVER called on any unauthorized payment state."""
    from backend.main import app
    from backend.sellers.dependencies import get_data_seller_service
    from backend.sellers.routes import get_payment_verifier
    from backend.sellers.data_seller import DataSellerService
    from backend.sellers.schemas import DataSellerInput, DataSellerOutput
    from backend.payments.interfaces import SellerPaymentVerifierInterface
    from backend.shared.schemas import PaymentRequirement

    execution_count = 0

    class SpyDataSellerService(DataSellerService):
        async def _execute_business_logic(self, payload: DataSellerInput, context) -> DataSellerOutput:
            nonlocal execution_count
            execution_count += 1
            return DataSellerOutput(symbol="SPY", price=100.0, volume_24h=1.0, timestamp="now")

    class RejectingVerifier(SellerPaymentVerifierInterface):
        def issue_challenge(self, service_id, amount_units, pay_to):
            return PaymentRequirement(
                version="2.0", network="eip155:84532", token="0x036CbD53842c5426634e7929541eC2318f3dCF7e",
                amount=str(amount_units), payTo=pay_to, nonce="nonce_spy", service_id=service_id
            )
        async def verify_and_settle(self, payload, req):
            raise PermissionError("Unverified signature")

    app.dependency_overrides[get_data_seller_service] = lambda: SpyDataSellerService()

    try:
        # Case 1: Missing payment header
        client.post("/api/v1/seller/data", json={"symbol": "ETH"})
        assert execution_count == 0

        # Case 2: Malformed payload header
        client.post("/api/v1/seller/data", json={"symbol": "ETH"}, headers={HEADER_X402_PAYMENT_PAYLOAD: "invalid_json"})
        assert execution_count == 0

        # Case 3: Verifier unavailable (None)
        valid_hdr = {
            HEADER_X402_PAYMENT_PAYLOAD: json.dumps({
                "authorization": {"amount": "2000"},
                "signature": "0x123",
                "buyer_address": "0x0000000000000000000000000000000000000000"
            })
        }
        client.post("/api/v1/seller/data", json={"symbol": "ETH"}, headers=valid_hdr)
        assert execution_count == 0

        # Case 4: Verifier rejects payment
        app.dependency_overrides[get_payment_verifier] = lambda: RejectingVerifier()
        client.post("/api/v1/seller/data", json={"symbol": "ETH"}, headers=valid_hdr)
        assert execution_count == 0
    finally:
        app.dependency_overrides.pop(get_data_seller_service, None)
        app.dependency_overrides.pop(get_payment_verifier, None)


def test_scraping_and_inference_dependency_overrides(client):
    """[MOCK-BASED PAYMENT TEST] Verify scraping and inference seller services respect FastAPI dependency overrides."""
    from backend.main import app
    from backend.sellers.dependencies import get_scraping_seller_service, get_inference_seller_service
    from backend.sellers.routes import get_payment_verifier
    from backend.sellers.scraping_seller import ScrapingSellerService
    from backend.sellers.inference_seller import InferenceSellerService
    from backend.sellers.schemas import ScrapingSellerOutput, InferenceSellerOutput
    from backend.payments.interfaces import SellerPaymentVerifierInterface
    from backend.shared.schemas import PaymentRequirement, SettlementReceipt

    class CustomScrapingService(ScrapingSellerService):
        async def _execute_business_logic(self, payload, context):
            return ScrapingSellerOutput(url=payload.url, title="OVERRIDE_TITLE", content="custom_content", word_count=2)

    class CustomInferenceService(InferenceSellerService):
        async def _execute_business_logic(self, payload, context):
            return InferenceSellerOutput(response="CUSTOM_LLM_OUTPUT", model_used="custom-model", tokens_generated=3)

    class MockVerifier(SellerPaymentVerifierInterface):
        def issue_challenge(self, service_id, amount_units, pay_to):
            return PaymentRequirement(
                version="2.0", network="eip155:84532", token="0x036CbD53842c5426634e7929541eC2318f3dCF7e",
                amount=str(amount_units), payTo=pay_to, nonce="nonce_ov", service_id=service_id
            )
        async def verify_and_settle(self, payload, req):
            return SettlementReceipt(facilitator_receipt_id="rec_ov", settled_amount_units=int(req.amount))

    app.dependency_overrides[get_scraping_seller_service] = lambda: CustomScrapingService()
    app.dependency_overrides[get_inference_seller_service] = lambda: CustomInferenceService()
    app.dependency_overrides[get_payment_verifier] = lambda: MockVerifier()

    try:
        headers = {
            HEADER_X402_PAYMENT_PAYLOAD: json.dumps({
                "authorization": {"amount": "3000"},
                "signature": "0x123",
                "buyer_address": "0x0000000000000000000000000000000000000000"
            })
        }
        res_scraping = client.post("/api/v1/seller/scraping", json={"url": "https://test.com"}, headers=headers)
        assert res_scraping.status_code == status.HTTP_200_OK
        assert res_scraping.json()["title"] == "OVERRIDE_TITLE"

        headers[HEADER_X402_PAYMENT_PAYLOAD] = json.dumps({
            "authorization": {"amount": "4000"},
            "signature": "0x123",
            "buyer_address": "0x0000000000000000000000000000000000000000"
        })
        res_inf = client.post("/api/v1/seller/inference", json={"prompt": "Test", "max_tokens": 50}, headers=headers)
        assert res_inf.status_code == status.HTTP_200_OK
        assert res_inf.json()["response"] == "CUSTOM_LLM_OUTPUT"
    finally:
        app.dependency_overrides.pop(get_scraping_seller_service, None)
        app.dependency_overrides.pop(get_inference_seller_service, None)
        app.dependency_overrides.pop(get_payment_verifier, None)


def test_seller_route_internal_exception_sanitization(client):
    """[MOCK-BASED PAYMENT TEST] Verify unhandled internal exceptions are sanitized and do not leak sensitive details."""
    from backend.main import app
    from backend.sellers.dependencies import get_data_seller_service
    from backend.sellers.routes import get_payment_verifier
    from backend.sellers.data_seller import DataSellerService
    from backend.payments.interfaces import SellerPaymentVerifierInterface
    from backend.shared.schemas import PaymentRequirement, SettlementReceipt

    class SensitiveCrashingSellerService(DataSellerService):
        async def _execute_business_logic(self, payload, context):
            # Raise exception containing sensitive internal secret
            raise RuntimeError("Database connection string: postgres://user:SECRET_PASS_999@db:5432")

    class MockVerifier(SellerPaymentVerifierInterface):
        def issue_challenge(self, service_id, amount_units, pay_to):
            return PaymentRequirement(
                version="2.0", network="eip155:84532", token="0x036CbD53842c5426634e7929541eC2318f3dCF7e",
                amount=str(amount_units), payTo=pay_to, nonce="nonce_sens", service_id=service_id
            )
        async def verify_and_settle(self, payload, req):
            return SettlementReceipt(facilitator_receipt_id="rec_sens", settled_amount_units=int(req.amount))

    app.dependency_overrides[get_data_seller_service] = lambda: SensitiveCrashingSellerService()
    app.dependency_overrides[get_payment_verifier] = lambda: MockVerifier()

    try:
        headers = {
            HEADER_X402_PAYMENT_PAYLOAD: json.dumps({
                "authorization": {"amount": "2000"},
                "signature": "0x123",
                "buyer_address": "0x0000000000000000000000000000000000000000"
            })
        }
        response = client.post("/api/v1/seller/data", json={"symbol": "ETH"}, headers=headers)
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        err = response.json()
        assert err["error_code"] == "SELLER_EXECUTION_FAILED"
        # CRITICAL SECURITY SANITIZATION: Sensitive connection string or password is NOT leaked in HTTP JSON!
        assert "SECRET_PASS_999" not in err["message"]
        assert "SECRET_PASS_999" not in json.dumps(err)
        assert err["message"] == "Internal execution error occurred within seller logic."
    finally:
        app.dependency_overrides.pop(get_data_seller_service, None)
        app.dependency_overrides.pop(get_payment_verifier, None)



