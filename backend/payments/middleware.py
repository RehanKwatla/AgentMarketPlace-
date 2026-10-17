"""[IMPLEMENTED] ASGI Protocol Middleware for Official x402 v2 Header Interoperability.

Bridges official x402 v2 wire headers (PAYMENT-REQUIRED, PAYMENT-SIGNATURE, PAYMENT-RESPONSE)
with legacy transport headers (X-402-Requirement, X-402-Payment-Payload, X-402-Settlement-Proof).

Design principles:
1. Zero Modification to Seller Microservices: Seller routes natively binding
   Header(..., alias="X-402-Payment-Payload") automatically receive decoded JSON payloads
   when official PAYMENT-SIGNATURE headers are provided by clients.
2. Dual Header Emission: Responses from seller endpoints automatically emit both
   canonical official headers (PAYMENT-REQUIRED, PAYMENT-RESPONSE) and legacy headers
   (X-402-Requirement, X-402-Settlement-Proof) to support heterogeneous clients.
3. Strict Fail-Closed Security:
   - Malformed, tampered, expired, or invalid official signatures fail closed (HTTP 400 or 402).
   - Conflicting official and legacy payment headers are detected and rejected (HTTP 400).
   - Duplicate ambiguous headers are detected and rejected.
4. Truthful Settlement Representation:
   - A transaction hash (0x... 64/66 chars) alone NEVER sets confirmed_on_chain=True without verified
     receipt and matching on-chain transfer event evidence.
   - When live RPC is unqueried or unavailable, settlements remain explicitly confirmed_on_chain=False
     (settlement_type='unverified_transaction_hash' or 'local_authorization_receipt').
"""
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from starlette.types import ASGIApp, Receive, Scope, Send

from backend.payments.x402_adapter import (
    OFFICIAL_X402_AVAILABLE,
    OfficialSettleResponse,
    x402_adapter,
    x402_http,
)
from backend.shared.constants import NETWORK_BASE_SEPOLIA
from backend.shared.schemas import PaymentRequirement

logger = logging.getLogger(__name__)


class X402ProtocolMiddleware:
    """ASGI Middleware providing seamless bidirectional translation between official x402 v2
    wire headers and legacy application transport headers.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # ---------------------------------------------------------------------
        # 1. Incoming Request Header Adaptation & Conflict Detection
        # ---------------------------------------------------------------------
        headers: List[Tuple[bytes, bytes]] = list(scope.get("headers", []))
        sig_bytes: Optional[bytes] = None
        legacy_bytes: Optional[bytes] = None
        sig_count = 0
        legacy_count = 0

        for name, value in headers:
            lower_name = name.lower()
            if lower_name in (b"payment-signature", b"x-payment"):
                sig_bytes = value
                sig_count += 1
            elif lower_name == b"x-402-payment-payload":
                legacy_bytes = value
                legacy_count += 1

        # Reject duplicate ambiguous headers (e.g. Multiple contradictory signature headers)
        if sig_count > 1 or legacy_count > 1:
            logger.warning("Duplicate ambiguous payment headers detected in request.")
            new_headers = [(k, v) for k, v in headers if k.lower() != b"x-402-payment-payload"]
            new_headers.append((b"x-402-payment-payload", b"DUPLICATE_AMBIGUOUS_PAYMENT_HEADERS"))
            scope = dict(scope, headers=new_headers)
            await self.app(scope, receive, send)
            return

        # Conflict check if BOTH official PAYMENT-SIGNATURE and legacy X-402-Payment-Payload are supplied
        if sig_bytes and legacy_bytes:
            try:
                sig_str = sig_bytes.decode("utf-8").strip()
                official_dict, _ = x402_adapter.decode_official_payload(sig_str)
                legacy_dict = json.loads(legacy_bytes.decode("utf-8"))

                off_auth = official_dict.get("authorization", {})
                leg_auth = legacy_dict.get("authorization", {})

                off_val = str(off_auth.get("value") if off_auth.get("value") is not None else (off_auth.get("amount") or ""))
                leg_val = str(leg_auth.get("value") if leg_auth.get("value") is not None else (leg_auth.get("amount") or ""))
                off_to = str(off_auth.get("to") or off_auth.get("payTo") or "").lower()
                leg_to = str(leg_auth.get("to") or leg_auth.get("payTo") or "").lower()
                off_nonce = str(off_auth.get("nonce") or "")
                leg_nonce = str(leg_auth.get("nonce") or "")

                if (off_val and leg_val and off_val != leg_val) or \
                   (off_to and leg_to and off_to != leg_to) or \
                   (off_nonce and leg_nonce and off_nonce != leg_nonce):
                    logger.warning("Conflicting terms between official PAYMENT-SIGNATURE and legacy payload.")
                    new_headers = [(k, v) for k, v in headers if k.lower() != b"x-402-payment-payload"]
                    new_headers.append((b"x-402-payment-payload", b"CONFLICTING_PAYMENT_HEADERS_DETECTED"))
                    scope = dict(scope, headers=new_headers)
            except Exception as conf_err:
                logger.warning("Failed during dual payment header consistency validation: %s", conf_err)
                new_headers = [(k, v) for k, v in headers if k.lower() != b"x-402-payment-payload"]
                new_headers.append((b"x-402-payment-payload", b"MALFORMED_DUAL_PAYMENT_HEADERS"))
                scope = dict(scope, headers=new_headers)

        # If client provided official PAYMENT-SIGNATURE without legacy X-402-Payment-Payload:
        elif sig_bytes and not legacy_bytes:
            try:
                sig_str = sig_bytes.decode("utf-8").strip()
                payload_dict, _ = x402_adapter.decode_official_payload(sig_str)
                json_bytes = json.dumps(payload_dict).encode("utf-8")
                headers.append((b"x-402-payment-payload", json_bytes))
                scope = dict(scope, headers=headers)
            except Exception as decode_err:
                logger.warning("Malformed official payment signature header: %s", decode_err)
                # Inject a malformed string so downstream route fails closed with HTTP 400 Bad Request
                headers.append((b"x-402-payment-payload", b"MALFORMED_OFFICIAL_SIGNATURE"))
                scope = dict(scope, headers=headers)

        # ---------------------------------------------------------------------
        # 2. Outgoing Response Header Adaptation & Truthful Settlement Representation
        # ---------------------------------------------------------------------
        async def response_bridge_send(message: Any) -> None:
            if message["type"] == "http.response.start":
                status_code = message.get("status", 200)
                resp_headers: List[Tuple[bytes, bytes]] = list(message.get("headers", []))
                header_map: Dict[bytes, Tuple[int, bytes, bytes]] = {
                    h[0].lower(): (idx, h[0], h[1]) for idx, h in enumerate(resp_headers)
                }

                # Case A: HTTP 402 Challenge — augment with official PAYMENT-REQUIRED header
                if status_code == 402:
                    if b"x-402-requirement" in header_map and b"payment-required" not in header_map:
                        _, _, req_bytes = header_map[b"x-402-requirement"]
                        try:
                            req_dict = json.loads(req_bytes.decode("utf-8"))
                            req_obj = PaymentRequirement(**req_dict)
                            official_val = x402_adapter.encode_official_requirement(req_obj)
                            val_bytes = official_val.encode("utf-8")
                            resp_headers.append((b"payment-required", val_bytes))
                            resp_headers.append((b"x-payment", val_bytes))
                        except Exception as req_err:
                            logger.debug("Failed to encode official payment-required header: %s", req_err)

                # Case B: HTTP 200 Settlement — augment with official PAYMENT-RESPONSE header
                elif status_code == 200:
                    if b"x-402-settlement-proof" in header_map and b"payment-response" not in header_map:
                        _, _, proof_bytes = header_map[b"x-402-settlement-proof"]
                        proof_str = proof_bytes.decode("utf-8").strip()
                        if OFFICIAL_X402_AVAILABLE and proof_str:
                            try:
                                # TRUTHFULNESS RULE:
                                # Never declare confirmed_on_chain=True based only on 0x+64 hex format check.
                                # Live RPC query with verified receipt and matching on-chain transfer event
                                # evidence is strictly required for on-chain confirmation.
                                # Since ASGI middleware operates without live RPC verification, confirmed_on_chain
                                # remains strictly False.
                                is_hex_tx = proof_str.startswith("0x") and len(proof_str) in (64, 66)
                                sr = OfficialSettleResponse(
                                    success=True,
                                    transaction=proof_str,
                                    network=NETWORK_BASE_SEPOLIA,
                                    extra={
                                        "settlement_type": "unverified_transaction_hash" if is_hex_tx else "local_authorization_receipt",
                                        "confirmed_on_chain": False,
                                        "authorization_id": proof_str,
                                        "verification_status": "unconfirmed_offline_rpc_unavailable" if is_hex_tx else "local_authorization",
                                    }
                                )
                                official_resp = x402_http.encode_payment_response_header(sr)
                                val_bytes = official_resp.encode("utf-8")
                                resp_headers.append((b"payment-response", val_bytes))
                                resp_headers.append((b"x-payment-response", val_bytes))
                            except Exception as resp_err:
                                logger.debug("Failed to encode official payment-response header: %s", resp_err)

                # Update CORS exposed headers to expose both official and legacy headers
                if b"access-control-expose-headers" in header_map:
                    idx, orig_name, orig_val = header_map[b"access-control-expose-headers"]
                    extra_exposed = b", PAYMENT-REQUIRED, PAYMENT-SIGNATURE, PAYMENT-RESPONSE, X-PAYMENT, X-PAYMENT-RESPONSE"
                    resp_headers[idx] = (orig_name, orig_val + extra_exposed)

                message = dict(message, headers=resp_headers)

            await send(message)

        await self.app(scope, receive, response_bridge_send)
