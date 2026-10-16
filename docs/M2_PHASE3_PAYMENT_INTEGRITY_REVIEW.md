# M2 Phase 3: Payment Integrity & Official x402 Security Review

**Reviewer:** Member 2 — Seller Agents Technical Lead  
**Scope:** `backend/sellers/routes.py`, `backend/sellers/common.py`, and seller payment integration  
**Date:** 2026-10-17  
**Status:** COMPLETE — SELLER-VERIFIED  

---

## 1. Executive Summary

This audit reviewed the seller subsystem's integration with the official x402 v2 protocol and Member 1's payment engine. The objective is to verify that payment verification strictly gates seller execution, settlement semantics are accurately handled without fabrication, and error responses maintain strict separation between payment settlement and delivery status.

---

## 2. Review Findings by Protocol Feature

### 2.1 Challenge Generation (HTTP 402)
- **Official x402 v2:** Emits `PAYMENT-REQUIRED` header containing base64-encoded `OfficialPaymentRequired` (`x402.schemas.PaymentRequired`) with `accepts` containing scheme (`exact`), network (`eip155:84532`), token (`0x036CbD53842c5426634e7929541eC2318f3dCF7e`), amount, recipient address (`payTo`), and request nonce. Also mirrors into `X-PAYMENT` for v2 client compatibility.
- **Legacy Compatibility:** Emits `X-402-Requirement` containing JSON string with identical fields.
- **CORS Expose Headers:** `Access-Control-Expose-Headers` exposes all official and legacy headers (`PAYMENT-REQUIRED`, `PAYMENT-RESPONSE`, `X-PAYMENT`, `X-PAYMENT-RESPONSE`, `X-402-Requirement`, `X-402-Settlement-Proof`).
- **Verdict:** Compliant with official x402 v2 and project contracts.

### 2.2 Payment Payload Extraction & Ingestion
- **Priority Order:**
  1. `PAYMENT-SIGNATURE` (official v2 standard)
  2. `X-PAYMENT` (official v2 alternative)
  3. `X-402-Payment-Payload` (internal project legacy)
- **Decoding & Validation:**
  - Base64 payload decoded using `x402.http.decode_payment_signature_header`.
  - JSON payload validated using `PaymentPayload.model_validate`.
  - Malformed or corrupt headers return `HTTP 400 Bad Request` with `PAYMENT_PAYLOAD_INVALID`.
  - Missing headers fail closed with `HTTP 402 Payment Required`.
- **Verdict:** Robust fail-closed ingestion.

### 2.3 Critical Invariant A: Payment-Gated Execution
- **Strict Ordering:**
  1. Header extraction and schema validation.
  2. Payment verification via `verify_seller_payment` or `verifier.verify_and_settle(payment_payload, requirement)`.
  3. Receipt and proof validation: verifies `receipt.tx_hash` or `receipt.facilitator_receipt_id` is a non-empty string.
  4. Business logic execution (`service.execute_lifecycle()`) is strictly reachable ONLY after Step 3 succeeds.
- **Fail-Closed on Missing Verifier:**
  - If no verifier is configured/injected: returns `HTTP 503 Service Unavailable` with `PAYMENT_VERIFIER_UNAVAILABLE`. Seller logic is never executed.
- **Verdict:** Invariant A is strictly preserved.

### 2.4 Critical Invariant B: Settlement Semantics
- **Verification vs Settlement:**
  - In Member 1's architecture, `SellerPaymentVerifierInterface.verify_and_settle()` accepts `(PaymentPayload, PaymentRequirement)` and returns `SettlementReceipt`.
  - In live mode, settlement receipts contain either an on-chain transaction hash (`tx_hash`) or facilitator settlement receipt ID (`facilitator_receipt_id`).
  - Sellers treat proof as an opaque receipt identifier. If proof is missing or empty, execution fails closed with `HTTP 402 PAYMENT_AUTHORIZATION_FAILED`.
  - Sellers never fabricate mock transaction hashes (e.g. `0x1234...fake`).
- **Settlement Proof Header Emission:**
  - When settlement is verified and seller executes successfully:
    - Legacy `X-402-Settlement-Proof` is attached.
    - Official base64 `PAYMENT-RESPONSE` and `X-PAYMENT-RESPONSE` (`OfficialSettleResponse`) are attached.
- **Verdict:** Invariant B is strictly preserved.

### 2.5 Critical Invariant C: Error Responses & Delivery State Separation
- **No Accidental Settlement Proof on Failure:**
  - If seller business logic throws an exception (e.g. timeout, upstream error, or output schema violation), `_handle_seller_exception` is called.
  - The returned `JSONResponse` (HTTP 500, 502, 504) does NOT include `PAYMENT-RESPONSE` or `X-402-Settlement-Proof`.
- **Separation of Payment State vs Delivery State:**
  - If payment settled successfully before the seller crashed, the audit logger explicitly emits a warning recording the confirmed `settlement_proof`, `service_id`, and `request_id`.
  - The HTTP response returns `SELLER_TIMEOUT`, `SELLER_OUTPUT_INVALID`, or `SELLER_EXECUTION_FAILED` (5xx), cleanly signaling seller delivery failure rather than payment failure.
- **Verdict:** Invariant C is strictly preserved.

---

## 3. Test Coverage Summary

- `test_missing_payment_header_returns_official_and_legacy_challenge`: Verified.
- `test_malformed_base64_payment_header_rejected_400`: Verified.
- `test_corrupted_json_in_payment_header_rejected_400`: Verified.
- `test_invalid_payment_fails_closed_402`: Verified.
- `test_missing_verifier_fails_closed_503`: Verified.
- `test_valid_payment_via_official_payment_signature_header_success`: Verified.
- `test_valid_payment_via_official_x_payment_header_success`: Verified.
- `test_pending_payment_with_empty_proof_fails_closed`: Verified.
- `test_replayed_payment_nonce_fails_closed`: Verified.
- `test_seller_execution_failure_attaches_no_proof`: Verified.
