"""x402 v2 Payment Protocol Adapter with Official SDK Compatibility (Member 1)."""
import json
import logging
import time
import uuid
from typing import Any, Dict, Optional, Tuple

import httpx

from backend.shared.config import get_settings
from backend.shared.constants import (
    HEADER_IDEMPOTENCY_KEY,
    HEADER_X402_PAYMENT_PAYLOAD,
    HEADER_X402_REQUIREMENT,
    HEADER_X402_SETTLEMENT_PROOF,
    NETWORK_BASE_SEPOLIA,
    USDC_BASE_SEPOLIA,
)
from backend.shared.schemas import PaymentRequirement, ServiceDefinition
from backend.payments.policy import PaymentPolicyVerifier
from backend.payments.errors import (
    PaymentPolicyViolationError,
    SettlementTimeoutError,
    PaymentEngineError,
)

# Official x402 SDK schemas and wire protocol utilities
try:
    from x402 import (
        PaymentRequired as OfficialPaymentRequired,
        PaymentRequirements as OfficialPaymentRequirements,
        PaymentPayload as OfficialPaymentPayload,
        SettleResponse as OfficialSettleResponse,
    )
    import x402.http as x402_http
    OFFICIAL_X402_AVAILABLE = True
    HEADER_OFFICIAL_PAYMENT_REQUIRED = x402_http.PAYMENT_REQUIRED_HEADER
    HEADER_OFFICIAL_PAYMENT_SIGNATURE = x402_http.PAYMENT_SIGNATURE_HEADER
    HEADER_OFFICIAL_PAYMENT_RESPONSE = x402_http.PAYMENT_RESPONSE_HEADER
    HEADER_OFFICIAL_X_PAYMENT = x402_http.X_PAYMENT_HEADER
    HEADER_OFFICIAL_X_PAYMENT_RESPONSE = x402_http.X_PAYMENT_RESPONSE_HEADER
except ImportError:  # pragma: no cover
    OFFICIAL_X402_AVAILABLE = False
    OfficialPaymentRequired = None
    OfficialPaymentRequirements = None
    OfficialPaymentPayload = None
    OfficialSettleResponse = None
    x402_http = None
    HEADER_OFFICIAL_PAYMENT_REQUIRED = "PAYMENT-REQUIRED"
    HEADER_OFFICIAL_PAYMENT_SIGNATURE = "PAYMENT-SIGNATURE"
    HEADER_OFFICIAL_PAYMENT_RESPONSE = "PAYMENT-RESPONSE"
    HEADER_OFFICIAL_X_PAYMENT = "X-PAYMENT"
    HEADER_OFFICIAL_X_PAYMENT_RESPONSE = "X-PAYMENT-RESPONSE"

logger = logging.getLogger(__name__)


class X402Adapter:
    """Encapsulates HTTP 402 challenge negotiation, official x402 SDK translation,

    EIP-712 signing, and settlement proof capture.
    """

    def __init__(
        self,
        policy_verifier: Optional[PaymentPolicyVerifier] = None,
        timeout_seconds: Optional[float] = None,
        test_mode: Optional[bool] = None,
        signature_scheme: str = "personal_sign",
    ):
        settings = get_settings()
        self.policy_verifier = policy_verifier or PaymentPolicyVerifier()
        self.timeout_seconds = timeout_seconds or settings.x402_client_timeout_seconds
        self.buyer_address = settings.buyer_wallet_address
        self.buyer_private_key = settings.buyer_private_key
        if test_mode is not None:
            self.test_mode = test_mode
        else:
            self.test_mode = settings.environment.lower() in ("test", "testing", "dev", "development")
        self.signature_scheme = signature_scheme

    # -------------------------------------------------------------------------
    # Official x402 SDK Schema & Header Translation Methods
    # -------------------------------------------------------------------------

    def to_official_payment_required(self, requirement: PaymentRequirement) -> Any:
        """Translate application PaymentRequirement to official x402 PaymentRequired object."""
        if not OFFICIAL_X402_AVAILABLE:
            raise PaymentEngineError("Official x402 SDK is not installed in the active environment.")
        return OfficialPaymentRequired(
            x402_version=2,
            accepts=[
                OfficialPaymentRequirements(
                    scheme="exact",
                    network=requirement.network,
                    asset=requirement.token,
                    amount=str(requirement.amount),
                    pay_to=requirement.payTo,
                    max_timeout_seconds=int(self.timeout_seconds or 60),
                    extra={
                        "nonce": requirement.nonce,
                        "service_id": requirement.service_id,
                        "name": "USDC",
                        "version": "2",
                        "assetTransferMethod": "eip3009",
                    }
                )
            ]
        )

    def from_official_payment_required(self, pr: Any) -> PaymentRequirement:
        """Translate official x402 PaymentRequired object to application PaymentRequirement."""
        if not hasattr(pr, "accepts") or not pr.accepts:
            raise PaymentEngineError("Official x402 PaymentRequired contains no accepted requirements.")
        req = pr.accepts[0]
        extra = getattr(req, "extra", {}) or {}
        nonce = extra.get("nonce", "") if isinstance(extra, dict) else ""
        service_id = extra.get("service_id", "") if isinstance(extra, dict) else ""
        return PaymentRequirement(
            network=req.network,
            token=req.asset,
            amount=req.amount,
            payTo=req.pay_to,
            nonce=nonce or f"nonce_{uuid.uuid4().hex[:16]}",
            service_id=service_id,
        )

    def to_official_payment_payload(
        self,
        payload_dict: Dict[str, Any],
        requirement: PaymentRequirement
    ) -> Any:
        """Translate application payment payload to official x402 PaymentPayload object conforming to ExactEIP3009Payload."""
        if not OFFICIAL_X402_AVAILABLE:
            raise PaymentEngineError("Official x402 SDK is not installed in the active environment.")
        official_req = self.to_official_payment_required(requirement).accepts[0]
        auth = payload_dict.get("authorization", payload_dict)
        sig = payload_dict.get("signature", "")

        # Reflect any custom or mismatched network/asset from authorization into the official accepted terms
        if isinstance(auth, dict):
            if auth.get("network"):
                official_req.network = auth["network"]
            if auth.get("token"):
                official_req.asset = auth["token"]

        from_addr = auth.get("from") or auth.get("from_address") or payload_dict.get("buyer_address") or self.buyer_address or "0x0000000000000000000000000000000000000000"
        to_addr = auth.get("to") or auth.get("payTo") or requirement.payTo
        val_str = str(auth.get("value") if auth.get("value") is not None else (auth.get("amount") if auth.get("amount") is not None else requirement.amount))
        valid_after_str = str(auth.get("validAfter", "0"))
        valid_before_str = str(auth.get("validBefore", str(int(time.time()) + 3600)))
        raw_nonce = str(auth.get("nonce") or requirement.nonce or uuid.uuid4().hex)

        if raw_nonce.startswith("0x") and len(raw_nonce) == 66:
            nonce_hex = raw_nonce
        else:
            n_part = uuid.uuid5(uuid.NAMESPACE_DNS, raw_nonce).hex + uuid.uuid4().hex
            nonce_hex = f"0x{n_part[:64]}"

        # Canonical EIP-3009 payload for official x402 EVM exact facilitator & client
        official_payload_inner = {
            "authorization": {
                "from": from_addr,
                "to": to_addr,
                "value": val_str,
                "validAfter": valid_after_str,
                "validBefore": valid_before_str,
                "nonce": nonce_hex,
            },
            "signature": sig,
        }

        return OfficialPaymentPayload(
            x402_version=2,
            accepted=official_req,
            payload=official_payload_inner,
            extensions={"signature": sig} if sig else None,
        )

    def from_official_payment_payload(self, pl: Any) -> Dict[str, Any]:
        """Translate official x402 PaymentPayload object to application payload dictionary."""
        payload_data = pl.payload if isinstance(pl.payload, dict) else {}
        auth = dict(payload_data.get("authorization", payload_data))
        sig = payload_data.get("signature", "")
        if not sig and pl.extensions:
            sig = pl.extensions.get("signature", "")
        # Preserve network and token from accepted requirements in application authorization
        if hasattr(pl, "accepted") and pl.accepted:
            if hasattr(pl.accepted, "network") and pl.accepted.network:
                auth["network"] = pl.accepted.network
            if hasattr(pl.accepted, "asset") and pl.accepted.asset:
                auth["token"] = pl.accepted.asset
        return {
            "authorization": auth,
            "signature": sig,
            "buyer_address": self.buyer_address,
        }

    def encode_official_requirement(self, requirement: PaymentRequirement) -> str:
        """Encode application PaymentRequirement into official base64 wire format header."""
        pr = self.to_official_payment_required(requirement)
        return x402_http.encode_payment_required_header(pr)

    def decode_official_requirement(self, header_value: str) -> PaymentRequirement:
        """Decode official base64 wire format header into application PaymentRequirement."""
        if not OFFICIAL_X402_AVAILABLE:
            raise PaymentEngineError("Official x402 SDK is not installed.")
        try:
            pr = x402_http.decode_payment_required_header(header_value)
            return self.from_official_payment_required(pr)
        except Exception as exc:
            raise PaymentEngineError(f"Failed to decode official x402 PAYMENT-REQUIRED header: {exc}")

    def encode_official_payload(
        self,
        payload_dict: Dict[str, Any],
        requirement: PaymentRequirement
    ) -> str:
        """Encode payment payload into official base64 wire format header."""
        pl = self.to_official_payment_payload(payload_dict, requirement)
        return x402_http.encode_payment_signature_header(pl)

    def decode_official_payload(self, header_value: str) -> Tuple[Dict[str, Any], PaymentRequirement]:
        """Decode official base64 wire format header into payload dictionary and accepted requirement."""
        if not OFFICIAL_X402_AVAILABLE:
            raise PaymentEngineError("Official x402 SDK is not installed.")
        try:
            pl = x402_http.decode_payment_signature_header(header_value)
            payload_dict = self.from_official_payment_payload(pl)
            req = self.from_official_payment_required(OfficialPaymentRequired(x402_version=2, accepts=[pl.accepted]))
            return payload_dict, req
        except Exception as exc:
            raise PaymentEngineError(f"Failed to decode official x402 PAYMENT-SIGNATURE header: {exc}")

    def parse_challenge_from_headers(self, headers: Any) -> PaymentRequirement:
        """Parse HTTP 402 challenge terms from either official SDK headers or custom application headers."""
        # 1. Check official PAYMENT-REQUIRED or X-PAYMENT base64 header
        official_hdr = headers.get(HEADER_OFFICIAL_PAYMENT_REQUIRED) or headers.get(HEADER_OFFICIAL_X_PAYMENT)
        if official_hdr and OFFICIAL_X402_AVAILABLE:
            try:
                return self.decode_official_requirement(official_hdr)
            except Exception as err:
                logger.warning(f"Could not parse official x402 header: {err}. Falling back to custom header.")

        # 2. Check custom application transport header X-402-Requirement
        custom_hdr = headers.get(HEADER_X402_REQUIREMENT)
        if custom_hdr:
            try:
                req_dict = json.loads(custom_hdr)
                return PaymentRequirement(**req_dict)
            except Exception as exc:
                raise PaymentEngineError(f"Malformed X-402-Requirement header: {exc}")

        raise PaymentEngineError(
            f"Seller returned HTTP 402 but omitted required challenge header "
            f"('{HEADER_OFFICIAL_PAYMENT_REQUIRED}' or '{HEADER_X402_REQUIREMENT}')"
        )

    def build_payment_headers(
        self,
        payment_payload: Dict[str, Any],
        requirement: PaymentRequirement,
        idempotency_key: str,
    ) -> Dict[str, str]:
        """Build headers containing both official SDK header and custom application header for full compatibility."""
        custom_header_val = json.dumps(payment_payload)
        headers = {
            HEADER_X402_PAYMENT_PAYLOAD: custom_header_val,
            HEADER_IDEMPOTENCY_KEY: idempotency_key,
        }

        # Include official base64 PAYMENT-SIGNATURE header if SDK is available
        if OFFICIAL_X402_AVAILABLE:
            try:
                official_val = self.encode_official_payload(payment_payload, requirement)
                headers[HEADER_OFFICIAL_PAYMENT_SIGNATURE] = official_val
            except Exception as err:
                logger.debug(f"Could not encode official payment signature header: {err}")

        return headers

    def extract_settlement_proof(self, headers: Any) -> Optional[str]:
        """Extract settlement proof from official PAYMENT-RESPONSE or custom X-402-Settlement-Proof."""
        # 1. Check official response header
        official_resp = (
            headers.get(HEADER_OFFICIAL_PAYMENT_RESPONSE)
            or headers.get(HEADER_OFFICIAL_X_PAYMENT_RESPONSE)
        )
        if official_resp and OFFICIAL_X402_AVAILABLE:
            try:
                settle_resp = x402_http.decode_payment_response_header(official_resp)
                if settle_resp and settle_resp.transaction:
                    return settle_resp.transaction
                return official_resp
            except Exception:
                return official_resp

        # 2. Check custom application header
        return headers.get(HEADER_X402_SETTLEMENT_PROOF)

    # -------------------------------------------------------------------------
    # Core EIP-712 Signing and Payment Execution
    # -------------------------------------------------------------------------

    def create_payment_payload(
        self,
        requirement: PaymentRequirement,
        idempotency_key: str
    ) -> Dict[str, Any]:
        """Construct compliant EIP-712 / EIP-3009 payment authorization payload for Base Sepolia USDC."""
        now = int(time.time())
        valid_until = now + 3600  # 1 hour validity

        raw_nonce = requirement.nonce or uuid.uuid4().hex
        if raw_nonce.startswith("0x") and len(raw_nonce) == 66:
            nonce_hex = raw_nonce
        else:
            n_part = uuid.uuid5(uuid.NAMESPACE_DNS, raw_nonce).hex + uuid.uuid4().hex
            nonce_hex = f"0x{n_part[:64]}"

        # Dual-compatible authorization dictionary containing both canonical EIP-3009 fields
        # and existing application contract fields
        authorization = {
            "network": requirement.network,
            "token": requirement.token,
            "payTo": requirement.payTo,
            "amount": requirement.amount,
            "from": self.buyer_address,
            "to": requirement.payTo,
            "value": requirement.amount,
            "nonce": nonce_hex,
            "validAfter": now - 60,
            "validBefore": valid_until,
            "idempotencyKey": idempotency_key,
        }

        signature = self._sign_authorization(authorization)

        return {
            "authorization": authorization,
            "signature": signature,
            "buyer_address": self.buyer_address,
        }

    def build_eip3009_message(
        self,
        authorization: Dict[str, Any],
        requirement: Optional[PaymentRequirement] = None
    ) -> Dict[str, Any]:
        """Construct official EIP-3009 TransferWithAuthorization structured typed data for Base Sepolia USDC.

        Conforms exactly to official x402 EVM exact mechanism specification:
        - Domain: name="USDC", version="2", chainId=84532, verifyingContract=USDC_BASE_SEPOLIA
        - Types: TransferWithAuthorization(address from,address to,uint256 value,uint256 validAfter,uint256 validBefore,bytes32 nonce)
        """
        from_addr = (
            authorization.get("from")
            or authorization.get("from_address")
            or self.buyer_address
            or "0x0000000000000000000000000000000000000000"
        )
        to_addr = authorization.get("to") or authorization.get("payTo") or (requirement.payTo if requirement else "")
        val = int(authorization.get("value") if authorization.get("value") is not None else (authorization.get("amount") if authorization.get("amount") is not None else (requirement.amount if requirement else 0)))
        valid_after = int(authorization.get("validAfter", 0))
        valid_before = int(authorization.get("validBefore", int(time.time()) + 3600))
        token = authorization.get("token") or (requirement.token if requirement else USDC_BASE_SEPOLIA)
        raw_nonce = str(authorization.get("nonce") or (requirement.nonce if requirement else uuid.uuid4().hex))

        if raw_nonce.startswith("0x") and len(raw_nonce) == 66:
            nonce_bytes = bytes.fromhex(raw_nonce[2:])
        else:
            nonce_hex = uuid.uuid5(uuid.NAMESPACE_DNS, raw_nonce).hex + uuid.uuid4().hex
            nonce_bytes = bytes.fromhex(nonce_hex[:64])

        chain_id = 84532
        net = authorization.get("network") or (requirement.network if requirement else NETWORK_BASE_SEPOLIA)
        if ":" in net:
            try:
                chain_id = int(net.split(":")[-1])
            except (ValueError, TypeError):
                chain_id = 84532

        return {
            "types": {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                    {"name": "verifyingContract", "type": "address"},
                ],
                "TransferWithAuthorization": [
                    {"name": "from", "type": "address"},
                    {"name": "to", "type": "address"},
                    {"name": "value", "type": "uint256"},
                    {"name": "validAfter", "type": "uint256"},
                    {"name": "validBefore", "type": "uint256"},
                    {"name": "nonce", "type": "bytes32"},
                ],
            },
            "primaryType": "TransferWithAuthorization",
            "domain": {
                "name": "USDC",
                "version": "2",
                "chainId": chain_id,
                "verifyingContract": token,
            },
            "message": {
                "from": from_addr,
                "to": to_addr,
                "value": val,
                "validAfter": valid_after,
                "validBefore": valid_before,
                "nonce": nonce_bytes,
            },
        }

    def sign_eip3009_authorization(
        self,
        authorization: Dict[str, Any],
        private_key: Optional[str] = None
    ) -> str:
        """Sign canonical EIP-3009 authorization using EIP-712 structured typed data."""
        self._validate_live_signing_credentials(authorization, private_key)
        key = private_key or self.buyer_private_key
        if not key:
            raise PaymentEngineError("Cannot sign EIP-3009 typed data: private key is not configured.")
        if not key.startswith("0x"):
            key = f"0x{key}"
        if len(key) != 66:
            raise PaymentEngineError("Invalid private key: must be a 66-character hex string (0x...).")

        try:
            from eth_account import Account
            from eth_account.messages import encode_typed_data
        except ImportError:
            raise PaymentEngineError("Cannot sign EIP-3009: 'eth_account' dependency is missing.")

        try:
            full_msg = self.build_eip3009_message(authorization)
            signable_msg = encode_typed_data(full_message=full_msg)
            signed = Account.sign_message(signable_msg, private_key=key)
            sig_hex = signed.signature.hex()
            return sig_hex if sig_hex.startswith("0x") else f"0x{sig_hex}"
        except Exception as exc:
            raise PaymentEngineError(f"EIP-3009 signing failed: {exc}")

    def recover_eip3009_signer(
        self,
        authorization: Dict[str, Any],
        signature: str
    ) -> str:
        """Cryptographically recover the signing address from an EIP-3009 signature."""
        try:
            from eth_account import Account
            from eth_account.messages import encode_typed_data
        except ImportError:
            raise PaymentEngineError("Cannot recover EIP-3009 signer: 'eth_account' is missing.")

        try:
            full_msg = self.build_eip3009_message(authorization)
            signable_msg = encode_typed_data(full_message=full_msg)
            return Account.recover_message(signable_msg, signature=signature)
        except Exception as exc:
            raise PaymentEngineError(f"EIP-3009 signer recovery failed: {exc}")

    def verify_eip3009_signature(
        self,
        authorization: Dict[str, Any],
        signature: str,
        expected_signer: str
    ) -> bool:
        """Verify that an EIP-3009 signature was produced by the expected signer."""
        try:
            recovered = self.recover_eip3009_signer(authorization, signature)
            return recovered.lower() == expected_signer.lower()
        except Exception:
            return False

    def build_eip712_message(self, authorization: Dict[str, Any]) -> Dict[str, Any]:
        """Construct canonical EIP-712 typed structured data for Base Sepolia USDC payment authorization."""
        network = authorization.get("network", NETWORK_BASE_SEPOLIA)
        token = authorization.get("token", USDC_BASE_SEPOLIA)
        pay_to = authorization.get("payTo", "")
        amount = int(authorization.get("amount", 0))
        nonce = str(authorization.get("nonce", ""))
        valid_after = int(authorization.get("validAfter", 0))
        valid_before = int(authorization.get("validBefore", 0))
        idempotency_key = str(authorization.get("idempotencyKey", ""))

        # Chain ID from network string (e.g. eip155:84532 -> 84532)
        chain_id = 84532
        if ":" in network:
            try:
                chain_id = int(network.split(":")[-1])
            except (ValueError, TypeError):
                chain_id = 84532

        return {
            "types": {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                    {"name": "verifyingContract", "type": "address"},
                ],
                "PaymentAuthorization": [
                    {"name": "network", "type": "string"},
                    {"name": "token", "type": "address"},
                    {"name": "payTo", "type": "address"},
                    {"name": "amount", "type": "uint256"},
                    {"name": "nonce", "type": "string"},
                    {"name": "validAfter", "type": "uint256"},
                    {"name": "validBefore", "type": "uint256"},
                    {"name": "idempotencyKey", "type": "string"},
                ],
            },
            "primaryType": "PaymentAuthorization",
            "domain": {
                "name": "USD Coin",
                "version": "2",
                "chainId": chain_id,
                "verifyingContract": token,
            },
            "message": {
                "network": network,
                "token": token,
                "payTo": pay_to,
                "amount": amount,
                "nonce": nonce,
                "validAfter": valid_after,
                "validBefore": valid_before,
                "idempotencyKey": idempotency_key,
            },
        }

    def sign_eip712_authorization(
        self,
        authorization: Dict[str, Any],
        private_key: Optional[str] = None
    ) -> str:
        """Sign authorization using the EIP-712 structured typed data standard."""
        self._validate_live_signing_credentials(authorization, private_key)
        key = private_key or self.buyer_private_key
        if not key:
            raise PaymentEngineError("Cannot sign EIP-712 typed data: private key is not configured.")
        if not key.startswith("0x"):
            key = f"0x{key}"
        if len(key) != 66:
            raise PaymentEngineError("Invalid private key: must be a 66-character hex string (0x...).")

        try:
            from eth_account import Account
            from eth_account.messages import encode_typed_data
        except ImportError:
            raise PaymentEngineError("Cannot sign EIP-712: 'eth_account' dependency is missing.")

        try:
            full_msg = self.build_eip712_message(authorization)
            signable_msg = encode_typed_data(full_message=full_msg)
            signed = Account.sign_message(signable_msg, private_key=key)
            sig_hex = signed.signature.hex()
            return sig_hex if sig_hex.startswith("0x") else f"0x{sig_hex}"
        except Exception as exc:
            raise PaymentEngineError(f"EIP-712 signing failed: {exc}")

    def recover_eip712_signer(
        self,
        authorization: Dict[str, Any],
        signature: str
    ) -> str:
        """Cryptographically recover the signing address from an EIP-712 signature."""
        try:
            from eth_account import Account
            from eth_account.messages import encode_typed_data
        except ImportError:
            raise PaymentEngineError("Cannot recover EIP-712 signer: 'eth_account' is missing.")

        try:
            full_msg = self.build_eip712_message(authorization)
            signable_msg = encode_typed_data(full_message=full_msg)
            return Account.recover_message(signable_msg, signature=signature)
        except Exception as exc:
            raise PaymentEngineError(f"EIP-712 signer recovery failed: {exc}")

    def verify_eip712_signature(
        self,
        authorization: Dict[str, Any],
        signature: str,
        expected_signer: str
    ) -> bool:
        """Verify that an EIP-712 signature was produced by the expected signer."""
        try:
            recovered = self.recover_eip712_signer(authorization, signature)
            return recovered.lower() == expected_signer.lower()
        except Exception:
            return False

    def _validate_live_signing_credentials(
        self,
        authorization: Dict[str, Any],
        key: Optional[str] = None
    ) -> None:
        """Enforce strict fail-closed security for live payment signing.

        Ensures placeholder addresses and missing credentials cannot be signed or paid in live mode.
        """
        if self.test_mode:
            return

        signing_key = key or self.buyer_private_key
        if not signing_key:
            raise PaymentEngineError(
                "Live payment signing failed: BUYER_PRIVATE_KEY is not configured. "
                "Live mode fails closed and strictly forbids mock signatures."
            )
        if not signing_key.startswith("0x"):
            signing_key = f"0x{signing_key}"
        if len(signing_key) != 66:
            raise PaymentEngineError(
                "Live payment signing failed: BUYER_PRIVATE_KEY must be a valid 66-character hex string (0x...). "
                "Live mode fails closed."
            )

        buyer_addr = str(authorization.get("from") or "").lower()
        if not buyer_addr or buyer_addr == "0x0000000000000000000000000000000000000000":
            if key is not None:
                try:
                    from eth_account import Account
                    buyer_addr = Account.from_key(signing_key).address.lower()
                except Exception:
                    pass
            else:
                buyer_addr = (self.buyer_address or "").lower()

        if not buyer_addr or buyer_addr == "0x0000000000000000000000000000000000000000":
            raise PaymentEngineError(
                "Live payment signing failed: BUYER_WALLET_ADDRESS is configured as the non-operational placeholder (0x000...0). "
                "Live payment execution requires an operator-supplied, funded Base Sepolia wallet address."
            )

        target_pay_to = str(authorization.get("payTo") or authorization.get("to") or "").lower()
        if target_pay_to in (
            "0x0000000000000000000000000000000000000000",
            "0x0000000000000000000000000000000000000001",
            "0x0000000000000000000000000000000000000002",
            "0x0000000000000000000000000000000000000003",
        ):
            raise PaymentEngineError(
                f"Live payment signing failed: Recipient payTo '{target_pay_to}' is a non-operational placeholder address. "
                "Live payment execution strictly forbids placeholder recipients."
            )

    def _sign_authorization(self, authorization: Dict[str, Any]) -> str:
        """Sign authorization with buyer private key if available.

        In live mode (test_mode=False), fails closed if credentials or eth_account are unavailable.
        Deterministic mock signing is strictly restricted to explicit test mode (test_mode=True).
        """
        self._validate_live_signing_credentials(authorization)

        if self.signature_scheme == "eip3009":
            return self.sign_eip3009_authorization(authorization)

        if self.signature_scheme == "eip712":
            return self.sign_eip712_authorization(authorization)

        if not self.test_mode:
            # Live Mode: Strict fail-closed verification
            if not self.buyer_private_key:
                raise PaymentEngineError(
                    "Live payment signing failed: BUYER_PRIVATE_KEY is not configured. "
                    "Live mode fails closed and strictly forbids mock signatures."
                )
            if not (self.buyer_private_key.startswith("0x") and len(self.buyer_private_key) == 66):
                raise PaymentEngineError(
                    "Live payment signing failed: BUYER_PRIVATE_KEY must be a valid 66-character hex string (0x...). "
                    "Live mode fails closed."
                )
            try:
                from eth_account import Account
                from eth_account.messages import encode_defunct
            except ImportError:  # pragma: no cover
                raise PaymentEngineError(
                    "Live payment signing failed: 'eth_account' dependency is not installed. "
                    "Live mode fails closed and strictly forbids mock signatures."
                )
            try:
                message_str = json.dumps(authorization, sort_keys=True)
                msg = encode_defunct(text=message_str)
                signed = Account.sign_message(msg, private_key=self.buyer_private_key)
                sig_hex = signed.signature.hex()
                return sig_hex if sig_hex.startswith("0x") else f"0x{sig_hex}"
            except Exception as exc:
                raise PaymentEngineError(f"Live ECDSA signing failed: {exc}. Live mode fails closed.")

        # Test Mode (test_mode=True): Allow live signing if configured, or deterministic mock
        if self.buyer_private_key and self.buyer_private_key.startswith("0x") and len(self.buyer_private_key) == 66:
            try:
                from eth_account import Account
                from eth_account.messages import encode_defunct
                message_str = json.dumps(authorization, sort_keys=True)
                msg = encode_defunct(text=message_str)
                signed = Account.sign_message(msg, private_key=self.buyer_private_key)
                sig_hex = signed.signature.hex()
                return sig_hex if sig_hex.startswith("0x") else f"0x{sig_hex}"
            except Exception:
                pass

        # Structured deterministic mock signature for Base Sepolia testnet/mock
        nonce_part = authorization.get("nonce", "nonce")
        return f"0x_mock_sig_{uuid.uuid5(uuid.NAMESPACE_DNS, str(nonce_part)).hex[:40]}"

    async def execute_paid_request(
        self,
        service: ServiceDefinition,
        input_payload: Dict[str, Any],
        idempotency_key: str,
        http_client: Optional[httpx.AsyncClient] = None
    ) -> Tuple[int, Dict[str, Any], Optional[str]]:
        """Executes full 402 challenge-response handshake with the seller microservice.

        Supports both official x402 protocol wire headers and custom application headers.

        Returns:
            Tuple of (http_status_code, response_data, settlement_proof_header)
        """
        if http_client is not None:
            client = http_client
            close_client = False
        else:
            is_local = "localhost" in service.endpoint_url or "127.0.0.1" in service.endpoint_url
            if is_local:
                try:
                    from httpx import ASGITransport
                    from backend.main import app
                    client = httpx.AsyncClient(
                        transport=ASGITransport(app=app),
                        base_url="http://localhost:8000",
                        timeout=self.timeout_seconds
                    )
                    close_client = True
                except Exception:
                    client = httpx.AsyncClient(timeout=self.timeout_seconds)
                    close_client = True
            else:
                client = httpx.AsyncClient(timeout=self.timeout_seconds)
                close_client = True

        try:
            # Step 1: Initial call to seller endpoint (expect HTTP 402)
            try:
                initial_resp = await client.post(service.endpoint_url, json=input_payload)
            except (httpx.ConnectError, httpx.NetworkError) as err:
                raise PaymentEngineError(f"Failed to connect to seller endpoint '{service.endpoint_url}': {err}")

            # If seller does not require payment (e.g. free tier), return output directly
            if initial_resp.status_code == 200:
                proof = self.extract_settlement_proof(initial_resp.headers)
                return 200, initial_resp.json(), proof

            if initial_resp.status_code != 402:
                # Seller returned error before challenge
                return initial_resp.status_code, initial_resp.json() if initial_resp.text else {}, None

            # Step 2: Intercept HTTP 402 and parse challenge from headers (official or custom)
            requirement = self.parse_challenge_from_headers(initial_resp.headers)

            # Step 3: Validate challenge terms against trusted catalog service
            self.policy_verifier.verify(requirement, service)

            # Step 4: Construct signed payment payload
            payment_payload = self.create_payment_payload(requirement, idempotency_key)

            # Step 5: Re-request with both official and custom headers
            headers = self.build_payment_headers(payment_payload, requirement, idempotency_key)

            try:
                paid_resp = await client.post(
                    service.endpoint_url,
                    json=input_payload,
                    headers=headers
                )
            except httpx.TimeoutException:
                # Crucial failure boundary: payload was sent, but response timed out
                raise SettlementTimeoutError(f"req_{idempotency_key[:16]}")
            except (httpx.ConnectError, httpx.NetworkError) as err:
                raise SettlementTimeoutError(f"req_{idempotency_key[:16]}: network drop after transmission: {err}")

            proof = self.extract_settlement_proof(paid_resp.headers)
            data = paid_resp.json() if paid_resp.text else {}
            return paid_resp.status_code, data, proof

        finally:
            if close_client:
                await client.aclose()


# Default singleton adapter
x402_adapter = X402Adapter()

