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


def test_seller_paid_execution_stub(client):
    # Simulated payment payload header
    headers = {
        HEADER_X402_PAYMENT_PAYLOAD: json.dumps({"sig": "0x123", "buyer": "0xBuyer"})
    }
    response = client.post(
        "/api/v1/seller/data",
        json={"symbol": "ETH"},
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    assert HEADER_X402_SETTLEMENT_PROOF in response.headers
    data = response.json()
    assert data["symbol"] == "ETH"
    assert data["price"] > 0
    assert "volume_24h" in data
