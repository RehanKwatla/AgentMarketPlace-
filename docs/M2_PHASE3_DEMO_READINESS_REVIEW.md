# M2 Phase 3: Demo Readiness & Test Execution Review

**Reviewer:** Member 2 — Seller Agents Technical Lead  
**Scope:** Seller subsystem demonstration readiness, integration tests, and scenario separation  
**Date:** 2026-10-17  
**Status:** COMPLETE — SELLER-VERIFIED  

---

## 1. Executive Summary

This review establishes the seller demonstration checklist and validates that all demo scenarios clearly separate mocked testnet behavior from live on-chain operations, preventing any misrepresentation of settlement or provider states.

---

## 2. Demo Scenario Breakdown & Status

| Scenario | Description | Execution Status | Evidence / Mock Boundary |
|----------|-------------|------------------|--------------------------|
| 1. Unpaid HTTP 402 Challenge | Client sends request without payment header. Server returns HTTP 402 with official `PAYMENT-REQUIRED` and legacy `X-402-Requirement`. | VERIFIED | `test_missing_payment_header_returns_official_and_legacy_challenge` |
| 2. Malformed Payment Rejection | Client sends corrupted or non-base64 payment payload. Server returns HTTP 400 `PAYMENT_PAYLOAD_INVALID`. | VERIFIED | `test_malformed_base64_payment_header_rejected_400` |
| 3. Payment Verification Gate | Client sends valid payment signature. Verifier validates signature, recipient, amount, and returns verified receipt. | VERIFIED (MOCKED) | Verified via `SellerPaymentVerifierInterface` mock and `test_valid_payment_via_official_payment_signature_header_success`. |
| 4. Successful Seller Execution | Lifecycle executes after confirmed payment. Server returns HTTP 200 with result, `X-402-Settlement-Proof`, and official base64 `PAYMENT-RESPONSE`. | VERIFIED | `test_scraping_seller_official_x402_flow`, `test_inference_seller_official_x402_flow` |
| 5. Seller Execution Failure After Payment | Payment settles, but seller service times out or output fails schema. Server returns HTTP 504 / 502 with NO settlement proof headers, while server audit log records confirmed settlement. | VERIFIED | `test_confirmed_payment_followed_by_seller_timeout_leaves_no_fake_proof`, `test_confirmed_payment_followed_by_invalid_seller_output_fails_closed_502` |
| 6. SSRF & DNS Rebinding Defense | Client asks Scraping Seller to scrape private IP or DNS-rebinding target. Scraping engine detects and blocks destination via connect-time IP pinning. | VERIFIED | `test_dns_rebinding_simulation_prevented_by_pinning`, `test_mixed_dns_answer_set_strictly_rejected` |
| 7. Fake Inference Execution | Inference Seller executes prompt synthesis via deterministic local engine in FAKE mode. | VERIFIED | `test_fake_inference_provider_outputs` |
| 8. Live Inference Execution (Mocked) | Inference Seller executes prompt synthesis via Gemini or Groq adapter using mocked upstream HTTP responses. | VERIFIED (MOCKED) | `test_gemini_inference_provider_mocked`, `test_groq_inference_provider_mocked` |
| 9. Live Inference Execution (Production) | Inference Seller invokes live Google Gemini / Groq API endpoints using live environment API keys. | PENDING AUTHORIZATION | Requires user-supplied API keys and authorization. |
| 10. Live Base Sepolia Settlement | End-to-end payment with real on-chain transfer of testnet USDC on Base Sepolia (`eip155:84532`). | PENDING AUTHORIZATION | Requires funded testnet wallet and user authorization. |

---

## 3. Strict Demo Truthfulness Guarantees

1. **Zero Fabricated Hashes:** No demonstration script or test fixture uses mock transaction hashes presented as real blockchain transactions.
2. **Clear Boundary Marking:** All demonstration scripts must explicitly declare whether they are running in `[MOCKED TESTNET / FAKE PROVIDER]` mode or `[LIVE PRODUCTION]` mode.
3. **No Unilateral Live Network Activity:** Live network calls to external LLMs or blockchain RPCs are strictly gated behind environment variables and explicit user authorization.
