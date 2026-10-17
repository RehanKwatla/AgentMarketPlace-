"""Seller Microservice Routes enforcing x402 v2 challenge flow, verification, and lifecycle execution."""
import base64
import json
import logging
from typing import Optional, Tuple

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
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
    ServiceCategory,
)
from backend.registry.service import registry_service
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

# Import official x402 schemas and HTTP utilities if available
try:
    from x402.schemas import (
        PaymentRequired as OfficialPaymentRequired,
        PaymentRequirements as OfficialPaymentRequirements,
        SettleResponse as OfficialSettleResponse,
    )
    from x402 import http as x402_http
except ImportError:
    OfficialPaymentRequired = None
    OfficialPaymentRequirements = None
    OfficialSettleResponse = None
    x402_http = None

# Official HTTP Header constants
HEADER_PAYMENT_REQUIRED = "PAYMENT-REQUIRED"
HEADER_PAYMENT_SIGNATURE = "PAYMENT-SIGNATURE"
HEADER_PAYMENT_RESPONSE = "PAYMENT-RESPONSE"
HEADER_X_PAYMENT = "X-PAYMENT"
HEADER_X_PAYMENT_RESPONSE = "X-PAYMENT-RESPONSE"

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
    """Build compliant HTTP 402 Payment Required response with official and legacy x402 challenge."""
    legacy_requirement = {
        "version": "2.0",
        "network": NETWORK_BASE_SEPOLIA,
        "token": USDC_BASE_SEPOLIA,
        "amount": str(amount_units),
        "payTo": pay_to,
        "nonce": nonce,
        "service_id": service_id,
    }
    legacy_json = json.dumps(legacy_requirement)

    # Official x402 v2 challenge encoding
    official_b64 = None
    if OfficialPaymentRequired is not None and OfficialPaymentRequirements is not None and x402_http is not None:
        try:
            req_spec = OfficialPaymentRequirements(
                scheme="exact",
                network=NETWORK_BASE_SEPOLIA,
                asset=USDC_BASE_SEPOLIA,
                amount=str(amount_units),
                pay_to=pay_to,
                max_timeout_seconds=60,
                extra={
                    "nonce": nonce,
                    "service_id": service_id,
                },
            )
            ch = OfficialPaymentRequired(
                x402_version=2,
                accepts=[req_spec],
            )
            official_b64 = x402_http.encode_payment_required_header(ch)
        except Exception as enc_err:
            logger.warning("Failed to encode official PaymentRequired challenge: %s", enc_err)

    if not official_b64:
        # Fallback to standard base64 of the requirements dictionary
        fallback_dict = {
            "x402Version": 2,
            "accepts": [{
                "scheme": "exact",
                "network": NETWORK_BASE_SEPOLIA,
                "asset": USDC_BASE_SEPOLIA,
                "amount": str(amount_units),
                "payTo": pay_to,
                "maxTimeoutSeconds": 60,
                "extra": {"nonce": nonce, "service_id": service_id},
            }],
        }
        official_b64 = base64.b64encode(json.dumps(fallback_dict).encode("utf-8")).decode("utf-8")

    expose_headers = (
        f"{HEADER_PAYMENT_REQUIRED}, {HEADER_PAYMENT_RESPONSE}, "
        f"{HEADER_X_PAYMENT}, {HEADER_X_PAYMENT_RESPONSE}, "
        f"{HEADER_X402_REQUIREMENT}, {HEADER_X402_SETTLEMENT_PROOF}"
    )

    return JSONResponse(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        content={"detail": "Payment Required via x402 v2 protocol."},
        headers={
            HEADER_X402_REQUIREMENT: legacy_json,
            HEADER_PAYMENT_REQUIRED: official_b64,
            HEADER_X_PAYMENT: official_b64,
            "Access-Control-Expose-Headers": expose_headers,
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


def _extract_and_decode_payment_payload(
    payment_signature: Optional[str] = None,
    x_payment: Optional[str] = None,
    x_402_payment_payload: Optional[str] = None,
) -> Tuple[Optional[PaymentPayload], Optional[str]]:
    """Extract and decode payment payload from official or legacy x402 headers.

    Priority order:
    1. PAYMENT-SIGNATURE (official v2 standard)
    2. X-PAYMENT (official v2 alternative)
    3. X-402-Payment-Payload (project internal legacy)

    Returns:
        (PaymentPayload, raw_header_str)
        If no header was provided or all are empty: returns (None, None).
        If a header was provided but cannot be decoded or validated: raises ValueError.
    """
    raw_header = None
    is_official_header = False

    if payment_signature is not None and payment_signature.strip():
        raw_header = payment_signature.strip()
        is_official_header = True
    elif x_payment is not None and x_payment.strip():
        raw_header = x_payment.strip()
        is_official_header = True
    elif x_402_payment_payload is not None and x_402_payment_payload.strip():
        raw_header = x_402_payment_payload.strip()
        is_official_header = False

    if not raw_header:
        return None, None

    # Step A: If official header or looks like base64, try official SDK decoder
    if is_official_header:
        if x402_http is not None:
            try:
                official_obj = x402_http.decode_payment_signature_header(raw_header)
                if hasattr(official_obj, "payload") and isinstance(official_obj.payload, dict):
                    inner = official_obj.payload
                    auth = dict(inner.get("authorization", {}))
                    if hasattr(official_obj, "accepted") and official_obj.accepted:
                        if hasattr(official_obj.accepted, "network") and official_obj.accepted.network:
                            auth["network"] = official_obj.accepted.network
                        if hasattr(official_obj.accepted, "asset") and official_obj.accepted.asset:
                            auth["token"] = official_obj.accepted.asset
                        if hasattr(official_obj.accepted, "pay_to") and official_obj.accepted.pay_to:
                            if "to" not in auth and "payTo" not in auth:
                                auth["payTo"] = official_obj.accepted.pay_to
                                auth["to"] = official_obj.accepted.pay_to
                    sig = inner.get("signature", "")
                    buyer = (
                        inner.get("buyer_address")
                        or auth.get("buyer_address")
                        or auth.get("from")
                        or "0x0000000000000000000000000000000000000000"
                    )
                    return PaymentPayload(
                        authorization=auth,
                        signature=sig,
                        buyer_address=buyer,
                    ), raw_header
            except Exception:
                # Could be plain JSON passed in official header; fall through to JSON attempt
                pass

    # Step B: Try JSON decoding (e.g. legacy X-402-Payment-Payload or unencoded JSON payload)
    try:
        parsed = json.loads(raw_header)
        if isinstance(parsed, dict):
            # Check if it has an official outer wrapper: {"payload": {"authorization": ..., "signature": ...}}
            if "payload" in parsed and isinstance(parsed["payload"], dict):
                inner = parsed["payload"]
                auth = inner.get("authorization", {})
                sig = inner.get("signature", "")
                buyer = (
                    inner.get("buyer_address")
                    or auth.get("buyer_address")
                    or auth.get("from")
                    or "0x0000000000000000000000000000000000000000"
                )
                return PaymentPayload(
                    authorization=auth,
                    signature=sig,
                    buyer_address=buyer,
                ), raw_header
            # Direct application PaymentPayload
            return PaymentPayload.model_validate(parsed), raw_header
    except (json.JSONDecodeError, ValidationError):
        pass

    # Step C: If not official header, but might be base64-encoded payload
    if not is_official_header and x402_http is not None:
        try:
            official_obj = x402_http.decode_payment_signature_header(raw_header)
            if hasattr(official_obj, "payload") and isinstance(official_obj.payload, dict):
                inner = official_obj.payload
                auth = inner.get("authorization", {})
                sig = inner.get("signature", "")
                buyer = (
                    inner.get("buyer_address")
                    or auth.get("buyer_address")
                    or auth.get("from")
                    or "0x0000000000000000000000000000000000000000"
                )
                return PaymentPayload(
                    authorization=auth,
                    signature=sig,
                    buyer_address=buyer,
                ), raw_header
        except Exception:
            pass

    # If all parsing attempts fail on a non-empty header -> invalid
    raise ValueError("Payment payload header is invalid, malformed, or unparseable.")


async def _verify_and_execute_seller(
    service_id: str,
    amount_units: int,
    pay_to: str,
    payload: any,
    payment_signature: Optional[str],
    x_payment: Optional[str],
    x_402_payment_payload: Optional[str],
    context: SellerExecutionContext,
    service: any,
    verifier: Optional[SellerPaymentVerifierInterface],
) -> JSONResponse:
    """Standardized seller execution handler with fail-closed payment authorization.
    
    Safety Invariants:
    1. If no payment payload or empty string -> Return HTTP 402 challenge with official & legacy headers.
    2. If payment payload provided:
       - Validate & decode via official base64 or legacy JSON schema.
       - If malformed -> Return HTTP 400 Bad Request (PAYMENT_PAYLOAD_INVALID).
       - If no verifier available -> Fail closed (HTTP 503 Service Unavailable).
       - If verifier available -> Invoke payment verification.
       - Only execute seller business logic AFTER verified, genuine settlement proof.
       - Attach both X-402-Settlement-Proof and official PAYMENT-RESPONSE / X-PAYMENT-RESPONSE headers.
       - Never fabricate fake receipts.
    """
    nonce = f"nonce_{context.request_id[:16]}"

    # 1. Extract and decode payment payload header
    try:
        payment_payload, raw_header = _extract_and_decode_payment_payload(
            payment_signature=payment_signature,
            x_payment=x_payment,
            x_402_payment_payload=x_402_payment_payload,
        )
    except ValueError as val_err:
        logger.warning(
            "Rejected malformed payment payload for service %s (req=%s): %s",
            service_id, context.request_id, val_err
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error_code": "PAYMENT_PAYLOAD_INVALID",
                "message": "The provided payment payload header is invalid or malformed.",
                "service_id": service_id,
                "request_id": context.request_id,
            },
        )

    # 2. Challenge with HTTP 402 if payment payload is missing or empty
    if payment_payload is None:
        return _build_402_challenge(
            service_id=service_id,
            amount_units=amount_units,
            pay_to=pay_to,
            nonce=nonce,
        )

    # 3. Verify Payment
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
        if settlement_proof:
            logger.warning(
                "Seller execution failed after payment settlement confirmed (service=%s, req=%s, proof=%s): %s",
                service_id, context.request_id, settlement_proof, exc
            )
        return _handle_seller_exception(exc, service_id=service_id, request_id=context.request_id)

    # 5. Formulate Success Response with Verified Settlement Evidence (Dual-Header)
    response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content=output.model_dump(),
    )

    if settlement_proof:
        # Legacy header
        response.headers[HEADER_X402_SETTLEMENT_PROOF] = settlement_proof

        # Official x402 v2 settlement proof headers (base64 encoded SettleResponse)
        try:
            is_hex_tx = settlement_proof.startswith("0x") and len(settlement_proof) in (64, 66)
            extra_payload = {
                "settlement_type": "unverified_transaction_hash" if is_hex_tx else "local_authorization_receipt",
                "confirmed_on_chain": False,
                "authorization_id": settlement_proof,
                "verification_status": "unconfirmed_offline_rpc_unavailable" if is_hex_tx else "local_authorization",
            }
            if OfficialSettleResponse is not None and x402_http is not None:
                settle_obj = OfficialSettleResponse(
                    success=True,
                    transaction=settlement_proof,
                    network=NETWORK_BASE_SEPOLIA,
                    amount=str(amount_units),
                    extra=extra_payload,
                )
                encoded_settle = x402_http.encode_payment_response_header(settle_obj)
            else:
                settle_dict = {
                    "success": True,
                    "transaction": settlement_proof,
                    "network": NETWORK_BASE_SEPOLIA,
                    "amount": str(amount_units),
                    "extra": extra_payload,
                }
                encoded_settle = base64.b64encode(json.dumps(settle_dict).encode("utf-8")).decode("utf-8")

            response.headers[HEADER_PAYMENT_RESPONSE] = encoded_settle
            response.headers[HEADER_X_PAYMENT_RESPONSE] = encoded_settle
        except Exception as enc_err:
            logger.warning("Failed to encode official PAYMENT-RESPONSE header: %s", enc_err)

        response.headers["Access-Control-Expose-Headers"] = (
            f"{HEADER_PAYMENT_REQUIRED}, {HEADER_PAYMENT_RESPONSE}, "
            f"{HEADER_X_PAYMENT}, {HEADER_X_PAYMENT_RESPONSE}, "
            f"{HEADER_X402_REQUIREMENT}, {HEADER_X402_SETTLEMENT_PROOF}"
        )

    return response


@router.post(
    "/data",
    response_model=DataSellerOutput,
    summary="Data Seller Endpoint",
)
async def handle_data_service(
    payload: DataSellerInput,
    service_id: Optional[str] = Query(None, description="Registered service ID (e.g. data_001, data_002, data_003)"),
    payment_signature: Optional[str] = Header(None, alias=HEADER_PAYMENT_SIGNATURE),
    x_payment: Optional[str] = Header(None, alias=HEADER_X_PAYMENT),
    x_402_payment_payload: Optional[str] = Header(None, alias=HEADER_X402_PAYMENT_PAYLOAD),
    x_service_id: Optional[str] = Header(None, alias="X-Service-Id"),
    context: SellerExecutionContext = Depends(get_seller_execution_context),
    service: DataSellerService = Depends(get_data_seller_service),
    verifier: Optional[SellerPaymentVerifierInterface] = Depends(get_payment_verifier),
    settings: Settings = Depends(get_settings),
):
    target_id = service_id or x_service_id or "data_001"
    reg_svc = registry_service.get_service(target_id)
    if reg_svc and reg_svc.category == ServiceCategory.DATA:
        svc_id = reg_svc.service_id
        amount_units = reg_svc.price_atomic
        pay_to = reg_svc.pay_to or settings.data_seller_pay_to
    else:
        svc_id = "data_001"
        amount_units = 2000
        pay_to = settings.data_seller_pay_to

    return await _verify_and_execute_seller(
        service_id=svc_id,
        amount_units=amount_units,
        pay_to=pay_to,
        payload=payload,
        payment_signature=payment_signature,
        x_payment=x_payment,
        x_402_payment_payload=x_402_payment_payload,
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
    service_id: Optional[str] = Query(None, description="Registered service ID (e.g. scraping_001, scraping_002, scraping_003)"),
    payment_signature: Optional[str] = Header(None, alias=HEADER_PAYMENT_SIGNATURE),
    x_payment: Optional[str] = Header(None, alias=HEADER_X_PAYMENT),
    x_402_payment_payload: Optional[str] = Header(None, alias=HEADER_X402_PAYMENT_PAYLOAD),
    x_service_id: Optional[str] = Header(None, alias="X-Service-Id"),
    context: SellerExecutionContext = Depends(get_seller_execution_context),
    service: ScrapingSellerService = Depends(get_scraping_seller_service),
    verifier: Optional[SellerPaymentVerifierInterface] = Depends(get_payment_verifier),
    settings: Settings = Depends(get_settings),
):
    target_id = service_id or x_service_id or "scraping_001"
    reg_svc = registry_service.get_service(target_id)
    if reg_svc and reg_svc.category == ServiceCategory.SCRAPING:
        svc_id = reg_svc.service_id
        amount_units = reg_svc.price_atomic
        pay_to = reg_svc.pay_to or settings.scraping_seller_pay_to
    else:
        svc_id = "scraping_001"
        amount_units = 3000
        pay_to = settings.scraping_seller_pay_to

    return await _verify_and_execute_seller(
        service_id=svc_id,
        amount_units=amount_units,
        pay_to=pay_to,
        payload=payload,
        payment_signature=payment_signature,
        x_payment=x_payment,
        x_402_payment_payload=x_402_payment_payload,
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
    service_id: Optional[str] = Query(None, description="Registered service ID (e.g. inference_001, inference_002, inference_003)"),
    payment_signature: Optional[str] = Header(None, alias=HEADER_PAYMENT_SIGNATURE),
    x_payment: Optional[str] = Header(None, alias=HEADER_X_PAYMENT),
    x_402_payment_payload: Optional[str] = Header(None, alias=HEADER_X402_PAYMENT_PAYLOAD),
    x_service_id: Optional[str] = Header(None, alias="X-Service-Id"),
    context: SellerExecutionContext = Depends(get_seller_execution_context),
    service: InferenceSellerService = Depends(get_inference_seller_service),
    verifier: Optional[SellerPaymentVerifierInterface] = Depends(get_payment_verifier),
    settings: Settings = Depends(get_settings),
):
    target_id = service_id or x_service_id or "inference_001"
    reg_svc = registry_service.get_service(target_id)
    if reg_svc and reg_svc.category == ServiceCategory.INFERENCE:
        svc_id = reg_svc.service_id
        amount_units = reg_svc.price_atomic
        pay_to = reg_svc.pay_to or settings.inference_seller_pay_to
    else:
        svc_id = "inference_001"
        amount_units = 4000
        pay_to = settings.inference_seller_pay_to

    return await _verify_and_execute_seller(
        service_id=svc_id,
        amount_units=amount_units,
        pay_to=pay_to,
        payload=payload,
        payment_signature=payment_signature,
        x_payment=x_payment,
        x_402_payment_payload=x_402_payment_payload,
        context=context,
        service=service,
        verifier=verifier,
    )
