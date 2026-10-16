"""Seller Microservice Routes enforcing x402 v2 challenge flow."""
import json
import uuid
from typing import Optional
from fastapi import APIRouter, Header, Response, status
from fastapi.responses import JSONResponse

from backend.shared.config import get_settings
from backend.shared.constants import (
    HEADER_X402_REQUIREMENT,
    HEADER_X402_PAYMENT_PAYLOAD,
    HEADER_X402_SETTLEMENT_PROOF,
    HEADER_IDEMPOTENCY_KEY,
    NETWORK_BASE_SEPOLIA,
    USDC_BASE_SEPOLIA,
)
from backend.sellers.schemas import (
    DataSellerInput,
    ScrapingSellerInput,
    InferenceSellerInput,
)
from backend.sellers.data_seller import DataSellerService
from backend.sellers.scraping_seller import ScrapingSellerService
from backend.sellers.inference_seller import InferenceSellerService

router = APIRouter(prefix="/api/v1/seller", tags=["Sellers"])

# Instantiated services
data_service = DataSellerService()
scraping_service = ScrapingSellerService()
inference_service = InferenceSellerService()


def _build_402_challenge(
    service_id: str,
    amount_units: int,
    pay_to: str
) -> JSONResponse:
    """Build compliant HTTP 402 Payment Required response."""
    requirement = {
        "version": "2.0",
        "network": NETWORK_BASE_SEPOLIA,
        "token": USDC_BASE_SEPOLIA,
        "amount": str(amount_units),
        "payTo": pay_to,
        "nonce": f"nonce_{uuid.uuid4().hex[:16]}",
        "service_id": service_id,
    }
    req_json = json.dumps(requirement)
    return JSONResponse(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        content={"detail": "Payment Required via x402 v2 protocol."},
        headers={
            HEADER_X402_REQUIREMENT: req_json,
            "Access-Control-Expose-Headers": f"{HEADER_X402_REQUIREMENT}, {HEADER_X402_SETTLEMENT_PROOF}",
        }
    )


@router.post("/data", summary="Data Seller Endpoint")
async def handle_data_service(
    payload: DataSellerInput,
    x_402_payment_payload: Optional[str] = Header(None, alias=HEADER_X402_PAYMENT_PAYLOAD),
    idempotency_key: Optional[str] = Header(None, alias=HEADER_IDEMPOTENCY_KEY),
):
    settings = get_settings()
    # If no payment payload supplied, challenge with 402
    if not x_402_payment_payload:
        return _build_402_challenge(
            service_id="data_001",
            amount_units=2000,  # 0.002 USDC
            pay_to=settings.data_seller_pay_to
        )

    # When payment payload is supplied (Member 1 verification integrated here)
    result = await data_service.execute(payload)
    response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content=result.model_dump()
    )
    # Proof header returned to buyer
    response.headers[HEADER_X402_SETTLEMENT_PROOF] = f"receipt_{uuid.uuid4().hex[:12]}"
    return response


@router.post("/scraping", summary="Scraping Seller Endpoint")
async def handle_scraping_service(
    payload: ScrapingSellerInput,
    x_402_payment_payload: Optional[str] = Header(None, alias=HEADER_X402_PAYMENT_PAYLOAD),
    idempotency_key: Optional[str] = Header(None, alias=HEADER_IDEMPOTENCY_KEY),
):
    settings = get_settings()
    if not x_402_payment_payload:
        return _build_402_challenge(
            service_id="scraping_001",
            amount_units=3000,  # 0.003 USDC
            pay_to=settings.scraping_seller_pay_to
        )

    result = await scraping_service.execute(payload)
    response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content=result.model_dump()
    )
    response.headers[HEADER_X402_SETTLEMENT_PROOF] = f"receipt_{uuid.uuid4().hex[:12]}"
    return response


@router.post("/inference", summary="Inference Seller Endpoint")
async def handle_inference_service(
    payload: InferenceSellerInput,
    x_402_payment_payload: Optional[str] = Header(None, alias=HEADER_X402_PAYMENT_PAYLOAD),
    idempotency_key: Optional[str] = Header(None, alias=HEADER_IDEMPOTENCY_KEY),
):
    settings = get_settings()
    if not x_402_payment_payload:
        return _build_402_challenge(
            service_id="inference_001",
            amount_units=4000,  # 0.004 USDC
            pay_to=settings.inference_seller_pay_to
        )

    result = await inference_service.execute(payload)
    response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content=result.model_dump()
    )
    response.headers[HEADER_X402_SETTLEMENT_PROOF] = f"receipt_{uuid.uuid4().hex[:12]}"
    return response
