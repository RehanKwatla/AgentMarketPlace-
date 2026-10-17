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
    payment_payload_header: Optional[str] = None,
    official_signature_header: Optional[str] = None,
    verifier: Optional[SellerPaymentVerifierInterface] = None,
) -> Optional[str]:
    """Turnkey verification helper for Member 2 seller endpoints.

    Behavior:
    1. If neither header is provided:
       Returns None so the route can immediately issue a standard HTTP 402 challenge.
    2. If either header is provided:
       Parses the payload (handling either custom JSON or official base64 PAYMENT-SIGNATURE),
       issues requirement, and verifies payment.
       - If valid: Returns the settlement proof string (e.g. 'rec_auth_...').
       - If invalid: Raises HTTPException(402, detail=...) failing closed.
    """
    raw_header = official_signature_header or payment_payload_header
    if not raw_header or not raw_header.strip():
        return None

    actual_verifier = verifier or seller_payment_verifier

    # 1. Issue current challenge requirement for this service
    requirement = actual_verifier.issue_challenge(
        service_id=service_id,
        amount_units=amount_units,
        pay_to=pay_to,
    )

    # 2. Parse incoming payload (supports custom JSON or official base64 PAYMENT-SIGNATURE wire format)
    if payment_payload_header and not official_signature_header:
        try:
            raw_data = json.loads(payment_payload_header)
            payload = PaymentPayload.model_validate(raw_data)
        except Exception as parse_err:
            try:
                from backend.payments.x402_adapter import x402_adapter
                decoded_dict, _ = x402_adapter.decode_official_payload(payment_payload_header.strip())
                payload = PaymentPayload.model_validate(decoded_dict)
            except Exception:
                logger.warning(f"Malformed payment payload JSON: {parse_err}")
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=f"Invalid x402 payment payload format: {parse_err}",
                )
    else:
        try:
            from backend.payments.x402_adapter import x402_adapter
            decoded_dict, _ = x402_adapter.decode_official_payload(raw_header.strip())
            payload = PaymentPayload.model_validate(decoded_dict)
        except Exception as decode_err:
            logger.warning(f"Malformed official payment signature header: {decode_err}")
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Invalid official x402 payment signature: {decode_err}",
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
