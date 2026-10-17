"""[IMPLEMENTED] FastAPI Dependencies and Integration Helpers for Sellers (Member 1).

Provides Member 2 seller microservices with turnkey, plug-and-play x402 payment
verification dependencies and helpers without altering underlying seller business logic.
"""
import json
import logging
from typing import Optional
from fastapi import Header, HTTPException, status
from fastapi.responses import JSONResponse

from backend.shared.constants import (
    HEADER_X402_PAYMENT_PAYLOAD,
    HEADER_X402_SETTLEMENT_PROOF,
    HEADER_X402_REQUIREMENT,
    HEADER_IDEMPOTENCY_KEY,
)
from backend.shared.schemas import PaymentRequirement, PaymentPayload
from backend.payments.settlement import SellerPaymentVerifier, seller_payment_verifier
from backend.payments.interfaces import SellerPaymentVerifierInterface
from backend.payments.errors import SettlementVerificationError

logger = logging.getLogger(__name__)


def get_seller_payment_verifier() -> SellerPaymentVerifierInterface:
    """FastAPI Dependency providing the singleton SellerPaymentVerifier instance."""
    return seller_payment_verifier


async def verify_seller_payment(
    service_id: str,
    amount_units: int,
    pay_to: str,
    payment_payload_header: Optional[str],
    verifier: Optional[SellerPaymentVerifierInterface] = None,
) -> Optional[str]:
    """Turnkey verification helper for Member 2 seller endpoints.

    Behavior:
    1. If payment_payload_header is None/empty:
       Returns None so the route can immediately issue a standard HTTP 402 challenge.
    2. If payment_payload_header is provided:
       Parses the payload, issues requirement, and verifies payment.
       - If valid: Returns the settlement proof string (e.g. 'rec_auth_...').
       - If invalid: Raises HTTPException(402, detail=...) failing closed.
    """
    if not payment_payload_header:
        return None

    actual_verifier = verifier or seller_payment_verifier

    # 1. Issue current challenge requirement for this service
    requirement = actual_verifier.issue_challenge(
        service_id=service_id,
        amount_units=amount_units,
        pay_to=pay_to,
    )

    # 2. Parse incoming payload
    try:
        raw_data = json.loads(payment_payload_header)
        payload = PaymentPayload.model_validate(raw_data)
    except Exception as parse_err:
        logger.warning(f"Malformed X-402-Payment-Payload header: {parse_err}")
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Invalid x402 payment payload format: {parse_err}",
        )

    # 3. Verify and settle
    try:
        receipt = await actual_verifier.verify_and_settle(payload, requirement)
        proof = receipt.facilitator_receipt_id or receipt.tx_hash
        if not proof:
            raise SettlementVerificationError("Settlement verification produced no valid receipt identifier.")
        return proof
    except SettlementVerificationError as verify_err:
        logger.warning(f"x402 payment verification failed for {service_id}: {verify_err}")
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Payment settlement verification rejected: {verify_err}",
        )
