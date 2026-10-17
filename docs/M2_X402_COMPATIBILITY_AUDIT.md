# M2 Phase 2.5 — Official x402 Seller Compatibility Audit

**Subsystem:** Member 2 — Seller Agents  
**Auditor:** Member 2 Technical Lead  
**Target Gate:** Phase 2.5 — Official x402 Seller Compatibility  
**Date:** 2026-10-17  
**Branch:** `M2`  

---

## 1. Executive Summary

This audit assesses the compatibility between the existing Member 2 Seller microservice routes (`backend/sellers/routes.py`) and the official x402 v2 protocol implementation merged from Member 1 (`backend/payments/`).

Prior to Phase 2.5, the Seller subsystem communicated strictly using custom HTTP headers:
- Challenge: `X-402-Requirement` containing raw JSON
- Authorization: `X-402-Payment-Payload` containing raw JSON
- Settlement Proof: `X-402-Settlement-Proof` containing plain text receipt/hash

With Member 1's integration of the official `x402==2.25.0` Python SDK, the payment engine now supports both the official base64 wire protocol and application headers. However, Seller routes still only inspect `X-402-Payment-Payload` and emit `X-402-Requirement`, making them unable to serve standard x402 clients that present only official headers (`PAYMENT-SIGNATURE` / `PAYMENT-REQUIRED` / `PAYMENT-RESPONSE`).

This audit documents the observed contracts, protocol mismatches, file modification scope, and test requirements to establish complete bidirectional compatibility without breaking existing functionality or modifying out-of-scope modules.

---

## 2. SDK & Version Evidence

Repository and environment inspection confirms the following installed dependencies:

| Package | Version | Import Path | Protocol Support |
| :--- | :--- | :--- | :--- |
| **`x402`** | `2.25.0` | `x402` / `x402.http` | Official x402 v2 wire protocol & schemas (`PaymentRequired`, `PaymentPayload`, `SettleResponse`) |
| **`web3`** | `8.0.0` | `web3.Web3` | EVM contract interaction, transfer log decoding, Base Sepolia RPC |
| **`eth-account`** | `0.14.0` | `eth_account.Account` | EIP-712 / ECDSA signature generation and cryptographic recovery |

### Verified Official Headers (`x402.http`):
- `PAYMENT_REQUIRED_HEADER = "PAYMENT-REQUIRED"`
- `PAYMENT_SIGNATURE_HEADER = "PAYMENT-SIGNATURE"`
- `PAYMENT_RESPONSE_HEADER = "PAYMENT-RESPONSE"`
- `X_PAYMENT_HEADER = "X-PAYMENT"`
- `X_PAYMENT_RESPONSE_HEADER = "X-PAYMENT-RESPONSE"`

### Verified Official Wire Encoding Functions:
- `x402_http.encode_payment_required_header(pr: PaymentRequired) -> str`
- `x402_http.decode_payment_required_header(header_value: str) -> PaymentRequired`
- `x402_http.encode_payment_signature_header(pl: PaymentPayload) -> str`
- `x402_http.decode_payment_signature_header(header_value: str) -> PaymentPayload`
- `x402_http.encode_payment_response_header(sr: SettleResponse) -> str`
- `x402_http.decode_payment_response_header(header_value: str) -> SettleResponse`

---

## 3. Current Seller Request / Response Behavior

### 3.1 Unpaid Request Flow (Current):
1. Client calls `POST /api/v1/seller/data`, `/scraping`, or `/inference` without payment headers.
2. Endpoint checks `x_402_payment_payload` header.
3. If missing or whitespace, returns `HTTP 402 Payment Required` with:
   - Header: `X-402-Requirement: {"version": "2.0", "network": "eip155:84532", ...}` (raw JSON)
   - Header: `Access-Control-Expose-Headers: X-402-Requirement, X-402-Settlement-Proof`
   - Body: `{"detail": "Payment Required via x402 v2 protocol."}`

### 3.2 Paid Request Flow (Current):
1. Client calls `POST` with `X-402-Payment-Payload: {"authorization": {...}, "signature": "...", "buyer_address": "..."}`.
2. Endpoint parses JSON into `backend.shared.schemas.PaymentPayload`.
3. Calls verifier via `get_payment_verifier()` (`SellerPaymentVerifierInterface.verify_and_settle`).
4. On success, executes `service.execute_lifecycle(payload, context)`.
5. Returns `HTTP 200 OK` with:
   - Header: `X-402-Settlement-Proof: <receipt_or_tx_hash>`
   - Body: Service JSON output.

### 3.3 Protocol Mismatches Identified:

| Protocol Dimension | Official x402 v2 Standard | Current Seller Implementation | Compatibility Impact |
| :--- | :--- | :--- | :--- |
| **Challenge Header (HTTP 402)** | `PAYMENT-REQUIRED: <base64>` and `X-PAYMENT: <base64>` | `X-402-Requirement: <raw_json>` | Official SDK clients cannot parse challenge without custom adapter fallback. |
| **Payment Payload Header** | `PAYMENT-SIGNATURE: <base64>` or `X-PAYMENT: <base64>` | `X-402-Payment-Payload: <raw_json>` | Official clients sending `PAYMENT-SIGNATURE` receive HTTP 402 challenge loop. |
| **Settlement Proof Header** | `PAYMENT-RESPONSE: <base64>` and `X-PAYMENT-RESPONSE: <base64>` | `X-402-Settlement-Proof: <plain_text>` | Official clients looking for `PAYMENT-RESPONSE` cannot extract settlement proof. |
| **CORS Exposed Headers** | Must expose official headers: `PAYMENT-REQUIRED`, `PAYMENT-RESPONSE`, `X-PAYMENT`, `X-PAYMENT-RESPONSE` | Only exposes `X-402-Requirement, X-402-Settlement-Proof` | Browser-based clients cannot read settlement or challenge headers across origins. |

---

## 4. Scope and Ownership of Required Changes

In strict accordance with Section 1 Ownership Rules:

| Component | Target File | Description of Required Change | Ownership |
| :--- | :--- | :--- | :--- |
| **Seller Routes** | `backend/sellers/routes.py` | Add dual-header challenge generation (`PAYMENT-REQUIRED`, `X-PAYMENT`, `X-402-Requirement`). | **Member 2** |
| **Seller Routes** | `backend/sellers/routes.py` | Extract payment authorization from `PAYMENT-SIGNATURE`, `X-PAYMENT`, or `X-402-Payment-Payload`. | **Member 2** |
| **Seller Routes** | `backend/sellers/routes.py` | Attach dual settlement proof headers (`PAYMENT-RESPONSE`, `X-PAYMENT-RESPONSE`, `X-402-Settlement-Proof`). | **Member 2** |
| **Seller Common/Helper** | `backend/sellers/common.py` or new helper | Add wire decoding/encoding helpers for official x402 formats with fail-closed safety. | **Member 2** |
| **Seller Tests** | `backend/tests/test_sellers_x402_compatibility.py` | New comprehensive test suite validating official-header-only, dual-header, and failure paths. | **Member 2** |
| **Payments / Buyer** | `backend/payments/`, `backend/buyer/` | **NO CHANGES**. Fully respected as external ownership. | Member 1 / 3 |

---

## 5. Required Test Plan (Stage 3 Coverage)

The test suite must verify:
- **Scenario A (Missing Header):** Returns HTTP 402 with both `PAYMENT-REQUIRED` (base64) and `X-402-Requirement` (JSON). Seller logic never runs.
- **Scenario B (Malformed Header):** Corrupt base64 or unparseable payload fails closed with HTTP 400 `PAYMENT_PAYLOAD_INVALID`.
- **Scenario C (Invalid Payment):** Rejected payment authorization returns HTTP 402 `PAYMENT_AUTHORIZATION_FAILED`.
- **Scenario D (Verifier Unavailable):** Missing verifier returns HTTP 503 `PAYMENT_VERIFIER_UNAVAILABLE`.
- **Scenario E (Verifier Exception):** Unexpected verifier crash returns HTTP 402/500 with sanitized message.
- **Scenario F (Valid Payment):** Official `PAYMENT-SIGNATURE` is accepted, verified, seller executes, returns HTTP 200 with `PAYMENT-RESPONSE` and `X-402-Settlement-Proof`.
- **Scenario G (Pending Payment):** Unsettled payment is rejected and never treated as final settlement.
- **Scenario H (Replay Protection):** Nonce reuse or signature replay fails closed.
- **Scenario I (Seller Failure):** Seller timeout (504) or crash (500) never attaches settlement proof headers.
- **Scenario J (Dual-Header & Official-Only):** Works seamlessly whether client sends official-only, custom-only, or both headers.
- **Scenario K (Zero Regression):** All existing 157 automated tests continue to pass.

---

## 6. Unresolved Questions & Coordination Items

1. **Facilitator URL Configuration:** In live Base Sepolia testnet mode, is facilitator verification required, or does `SellerPaymentVerifier` verify on-chain RPC logs directly?
   - *Current status:* In test/development mode (`ENVIRONMENT=development`), `SellerPaymentVerifier(test_mode=True)` verifies authorization terms and accepts valid signatures. In live mode, Base Sepolia RPC and transfer logs are checked.
2. **Backward Compatibility Guarantee:** Existing tests in `test_sellers.py` and `test_sellers_payment_integration.py` use `X-402-Payment-Payload`.
   - *Resolution:* Dual-header strategy ensures 100% backward compatibility while providing 100% official standard support.

---

## 7. Audit Verdict

**GATE STATUS: READY TO IMPLEMENT (Stage 0 Audit Complete)**  
The contracts, schemas, headers, and encoding formats are fully identified and verified via active package inspection. No blocking interface ambiguity remains. Proceed to Stage 1.
