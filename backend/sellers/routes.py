"""Seller Microservice Routes enforcing x402 v2 challenge flow, verification, and lifecycle execution."""
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, Response, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from backend.shared.config import Settings, get_settings
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
from backend.sellers.schemas import (
    DataSellerInput,
    DataSellerOutput,
    ScrapingSellerInput,
    ScrapingSellerOutput,
    InferenceSellerInput,
    InferenceSellerOutput,
)
from backend.sellers.common import (
    SellerExecutionContext,
    SellerBaseException,
    SellerInputValidationError,
    SellerExecutionTimeoutError,
    SellerOutputValidationError,
    SellerExecutionError,
)
from backend.sellers.data_seller import DataSellerService
from backend.sellers.scraping_seller import ScrapingSellerService
from backend.sellers.inference_seller import InferenceSellerService
from backend.sellers.dependencies import (
    get_data_seller_service,
    get_scraping_seller_service,
    get_inference_seller_service,
    get_seller_execution_context,
)

# Try importing Member 1's payment helper and verifier if available
try:
    from backend.payments import verify_seller_payment, get_seller_payment_verifier
except ImportError:
    verify_seller_payment = None
    get_seller_payment_verifier = None

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/seller", tags=["Sellers"])


def get_payment_verifier() -> Optional[SellerPaymentVerifierInterface]:
    """Dependency provider returning Member 1's concrete SellerPaymentVerifierInterface.
    
    Checks in priority order:
    1. Member 1's get_seller_payment_verifier() if implemented in backend.payments.
    2. Member 1's seller_payment_verifier singleton if exported in backend.payments.
    3. Member 1's seller_payment_verifier singleton if implemented in backend.payments.settlement.
    4. Defaults to None (fail-closed) when not yet configured or in test environments.
    """
    if get_seller_payment_verifier is not None:
        try:
            v = get_seller_payment_verifier()
            if v is not None:
                return v
        except Exception:
            pass
    try:
        from backend.payments import seller_payment_verifier
        if isinstance(seller_payment_verifier, SellerPaymentVerifierInterface):
            return seller_payment_verifier
    except (ImportError, AttributeError):
        pass
    try:
        from backend.payments.settlement import seller_payment_verifier
        if isinstance(seller_payment_verifier, SellerPaymentVerifierInterface):
            return seller_payment_verifier
    except (ImportError, AttributeError):
        pass
    return None


def _build_402_challenge(
    service_id: str,
    amount_units: int,
    pay_to: str,
    nonce: str,
) -> JSONResponse:
    """Build compliant HTTP 402 Payment Required response with x402 v2 challenge."""
    requirement = {
        "version": "2.0",
        "network": NETWORK_BASE_SEPOLIA,
        "token": USDC_BASE_SEPOLIA,
        "amount": str(amount_units),
        "payTo": pay_to,
        "nonce": nonce,
        "service_id": service_id,
    }
    req_json = json.dumps(requirement)
    return JSONResponse(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        content={"detail": "Payment Required via x402 v2 protocol."},
        headers={
            HEADER_X402_REQUIREMENT: req_json,
            "Access-Control-Expose-Headers": f"{HEADER_X402_REQUIREMENT}, {HEADER_X402_SETTLEMENT_PROOF}",
        },
    )


def _handle_seller_exception(exc: Exception, service_id: str, request_id: str) -> JSONResponse:
    """Format safe HTTP error response from domain exceptions without leaking credentials."""
    if isinstance(exc, SellerInputValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error_code": exc.error_code,
                "message": exc.message,
                "service_id": service_id,
                "request_id": request_id,
            },
        )
    elif isinstance(exc, SellerExecutionTimeoutError):
        return JSONResponse(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            content={
                "error_code": exc.error_code,
                "message": exc.message,
                "service_id": service_id,
                "request_id": request_id,
                "retryable": True,
            },
        )
    elif isinstance(exc, SellerOutputValidationError):
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "error_code": exc.error_code,
                "message": "Service produced output violating declared schema.",
                "service_id": service_id,
                "request_id": request_id,
            },
        )
    elif isinstance(exc, SellerExecutionError):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error_code": exc.error_code,
                "message": "Internal execution error occurred within seller logic.",
                "service_id": service_id,
                "request_id": request_id,
            },
        )
    elif isinstance(exc, SellerBaseException):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error_code": exc.error_code,
                "message": exc.message,
                "service_id": service_id,
                "request_id": request_id,
            },
        )
    else:
        logger.exception("Unexpected error in seller route: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error_code": "INTERNAL_SELLER_ERROR",
                "message": "An unexpected error occurred while executing the service.",
                "service_id": service_id,
                "request_id": request_id,
            },
        )


async def _verify_and_execute_seller(
    service_id: str,
    amount_units: int,
    pay_to: str,
    payload: any,
    raw_payment_payload: Optional[str],
    context: SellerExecutionContext,
    service: any,
    verifier: Optional[SellerPaymentVerifierInterface],
) -> JSONResponse:
    """Standardized seller execution handler with fail-closed payment authorization.
    
    Safety Invariants:
    1. If no payment payload or empty string -> Return HTTP 402 challenge.
    2. If payment payload provided:
       - Validate JSON & PaymentPayload schema.
       - If no verifier available -> Fail closed (HTTP 503 Service Unavailable).
       - If verifier available -> Invoke payment verification.
       - Only execute seller business logic AFTER verified, genuine settlement proof.
       - Only attach X-402-Settlement-Proof if actual settlement receipt/tx_hash is returned.
       - Never fabricate fake receipts (e.g. receipt_<random_uuid>).
    """
    # 1. Challenge with HTTP 402 if payment payload is missing or empty
    nonce = f"nonce_{context.request_id[:16]}"
    if not raw_payment_payload or not raw_payment_payload.strip():
        return _build_402_challenge(
            service_id=service_id,
            amount_units=amount_units,
            pay_to=pay_to,
            nonce=nonce,
        )

    # 2. Validate Payment Payload Structure (Fail-closed on malformed JSON / schema)
    try:
        parsed_json = json.loads(raw_payment_payload)
        payment_payload = PaymentPayload.model_validate(parsed_json)
    except (json.JSONDecodeError, ValidationError) as val_err:
        logger.warning(
            "Rejected malformed payment payload for service %s (req=%s): %s",
            service_id, context.request_id, val_err
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error_code": "PAYMENT_PAYLOAD_INVALID",
                "message": "The provided X-402-Payment-Payload header is invalid or malformed.",
                "service_id": service_id,
                "request_id": context.request_id,
            },
        )

    # 3. Verify Payment
    settlement_proof: Optional[str] = None
    if verify_seller_payment is not None:
        try:
            verified_evidence = await verify_seller_payment(
                service_id=service_id,
                amount_units=amount_units,
                pay_to=pay_to,
                payment_payload_header=raw_payment_payload,
                verifier=verifier,
            )
            if not verified_evidence or not isinstance(verified_evidence, str) or not verified_evidence.strip():
                logger.warning(
                    "verify_seller_payment returned empty proof for service %s (req=%s)",
                    service_id, context.request_id
                )
                return JSONResponse(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    content={
                        "error_code": "PAYMENT_AUTHORIZATION_FAILED",
                        "message": "Payment authorization rejected: unconfirmed settlement proof.",
                        "service_id": service_id,
                        "request_id": context.request_id,
                    },
                )
            settlement_proof = verified_evidence.strip()
        except HTTPException as http_exc:
            return JSONResponse(
                status_code=http_exc.status_code,
                content={
                    "error_code": "PAYMENT_AUTHORIZATION_FAILED",
                    "message": f"Payment authorization rejected: {http_exc.detail}",
                    "service_id": service_id,
                    "request_id": context.request_id,
                },
            )
        except Exception as exc:
            logger.warning("verify_seller_payment failed for service %s (req=%s): %s", service_id, context.request_id, exc)
            return JSONResponse(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                content={
                    "error_code": "PAYMENT_AUTHORIZATION_FAILED",
                    "message": "Payment authorization verification failed.",
                    "service_id": service_id,
                    "request_id": context.request_id,
                },
            )
    else:
        # Fallback to direct SellerPaymentVerifierInterface
        if verifier is None:
            logger.error(
                "Payment verification unavailable for service %s (req=%s). Concrete verifier not configured.",
                service_id, context.request_id
            )
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "error_code": "PAYMENT_VERIFIER_UNAVAILABLE",
                    "message": (
                        "Payment verification engine is pending Member 1 integration. "
                        "Cannot process paid call without verified settlement."
                    ),
                    "service_id": service_id,
                    "request_id": context.request_id,
                },
            )

        requirement = PaymentRequirement(
            version="2.0",
            network=NETWORK_BASE_SEPOLIA,
            token=USDC_BASE_SEPOLIA,
            amount=str(amount_units),
            payTo=pay_to,
            nonce=nonce,
            service_id=service_id,
        )

        try:
            receipt = await verifier.verify_and_settle(payment_payload, requirement)
        except Exception as verif_err:
            err_str = str(verif_err)
            if any(s in err_str.lower() for s in ["password", "secret", "private", "postgres", "mysql", "redis", "mongodb"]):
                logger.warning(
                    "Payment verification failed for service %s (req=%s) with internal system error (redacted)",
                    service_id, context.request_id
                )
                safe_msg = "Internal verification system error."
            else:
                logger.warning(
                    "Payment verification failed for service %s (req=%s): %s",
                    service_id, context.request_id, err_str
                )
                safe_msg = err_str

            return JSONResponse(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                content={
                    "error_code": "PAYMENT_AUTHORIZATION_FAILED",
                    "message": f"Payment authorization rejected: {safe_msg}",
                    "service_id": service_id,
                    "request_id": context.request_id,
                },
            )

        if receipt is None:
            logger.warning(
                "Payment verification returned no receipt for service %s (req=%s)",
                service_id, context.request_id
            )
            return JSONResponse(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                content={
                    "error_code": "PAYMENT_AUTHORIZATION_FAILED",
                    "message": "Payment authorization rejected: no settlement receipt produced.",
                    "service_id": service_id,
                    "request_id": context.request_id,
                },
            )

        proof = getattr(receipt, "tx_hash", None) or getattr(receipt, "facilitator_receipt_id", None)
        if not proof or not isinstance(proof, str) or not proof.strip():
            logger.warning(
                "Payment verification returned empty/invalid proof for service %s (req=%s)",
                service_id, context.request_id
            )
            return JSONResponse(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                content={
                    "error_code": "PAYMENT_AUTHORIZATION_FAILED",
                    "message": "Payment authorization rejected: unconfirmed settlement proof.",
                    "service_id": service_id,
                    "request_id": context.request_id,
                },
            )
        settlement_proof = str(proof).strip()

    # 4. Execute Service via BaseSellerService lifecycle only AFTER verified settlement
    try:
        output, metrics = await service.execute_lifecycle(payload, context=context)
    except Exception as exc:
        return _handle_seller_exception(exc, service_id=service_id, request_id=context.request_id)

    # 5. Formulate Success Response with Verified Settlement Evidence
    response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content=output.model_dump(),
    )

    if settlement_proof:
        response.headers[HEADER_X402_SETTLEMENT_PROOF] = settlement_proof

    return response



@router.post(
    "/data",
    response_model=DataSellerOutput,
    summary="Data Seller Endpoint",
)
async def handle_data_service(
    payload: DataSellerInput,
    x_402_payment_payload: Optional[str] = Header(None, alias=HEADER_X402_PAYMENT_PAYLOAD),
    context: SellerExecutionContext = Depends(get_seller_execution_context),
    service: DataSellerService = Depends(get_data_seller_service),
    verifier: Optional[SellerPaymentVerifierInterface] = Depends(get_payment_verifier),
    settings: Settings = Depends(get_settings),
):
    return await _verify_and_execute_seller(
        service_id="data_001",
        amount_units=2000,  # 0.002 USDC
        pay_to=settings.data_seller_pay_to,
        payload=payload,
        raw_payment_payload=x_402_payment_payload,
        context=context,
        service=service,
        verifier=verifier,
    )


@router.post(
    "/scraping",
    response_model=ScrapingSellerOutput,
    summary="Scraping Seller Endpoint",
)
async def handle_scraping_service(
    payload: ScrapingSellerInput,
    x_402_payment_payload: Optional[str] = Header(None, alias=HEADER_X402_PAYMENT_PAYLOAD),
    context: SellerExecutionContext = Depends(get_seller_execution_context),
    service: ScrapingSellerService = Depends(get_scraping_seller_service),
    verifier: Optional[SellerPaymentVerifierInterface] = Depends(get_payment_verifier),
    settings: Settings = Depends(get_settings),
):
    return await _verify_and_execute_seller(
        service_id="scraping_001",
        amount_units=3000,  # 0.003 USDC
        pay_to=settings.scraping_seller_pay_to,
        payload=payload,
        raw_payment_payload=x_402_payment_payload,
        context=context,
        service=service,
        verifier=verifier,
    )


@router.post(
    "/inference",
    response_model=InferenceSellerOutput,
    summary="Inference Seller Endpoint",
)
async def handle_inference_service(
    payload: InferenceSellerInput,
    x_402_payment_payload: Optional[str] = Header(None, alias=HEADER_X402_PAYMENT_PAYLOAD),
    context: SellerExecutionContext = Depends(get_seller_execution_context),
    service: InferenceSellerService = Depends(get_inference_seller_service),
    verifier: Optional[SellerPaymentVerifierInterface] = Depends(get_payment_verifier),
    settings: Settings = Depends(get_settings),
):
    return await _verify_and_execute_seller(
        service_id="inference_001",
        amount_units=4000,  # 0.004 USDC
        pay_to=settings.inference_seller_pay_to,
        payload=payload,
        raw_payment_payload=x_402_payment_payload,
        context=context,
        service=service,
        verifier=verifier,
    )
