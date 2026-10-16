# M2 Phase 3 Stage 1: Seller Contract and Integration Validation Report

**Author:** Member 2 — Seller Agents Technical Lead  
**Repository:** `C:\AgentMarket`  
**Date:** 2026-10-17  
**Stage:** Stage 1 (Contract & Integration Validation)  

---

## 1. Objective

Validate that the Seller subsystem (`backend/sellers/`) strictly conforms to shared project contracts defined in `docs/API_CONTRACTS.md`, `backend/registry/service_catalog.py`, `backend/shared/schemas.py`, and `docs/M2_X402_SELLER_CONTRACT.md`.

---

## 2. Cross-Module Contract Audit Matrix

| Verification Item | Registry / Shared Contract | Seller Route Implementation | Alignment Status |
|---|---|---|---|
| **Data Seller ID** | `data_001` | `data_001` (`/api/v1/seller/data`) | **MATCH** |
| **Data Price** | `0.002 USDC` (2,000 base units) | `amount_units=2000` | **MATCH** |
| **Data Pay-To** | `settings.data_seller_pay_to` | `settings.data_seller_pay_to` | **MATCH** |
| **Data Input Schema** | `{"symbol": "string"}` | `DataSellerInput(symbol: str)` | **MATCH** |
| **Data Output Schema** | `{"symbol", "price", "volume_24h", "timestamp"}` | `DataSellerOutput` | **MATCH** |
| **Scraping Seller ID** | `scraping_001` | `scraping_001` (`/api/v1/seller/scraping`) | **MATCH** |
| **Scraping Price** | `0.003 USDC` (3,000 base units) | `amount_units=3000` | **MATCH** |
| **Scraping Pay-To** | `settings.scraping_seller_pay_to` | `settings.scraping_seller_pay_to` | **MATCH** |
| **Scraping Input Schema** | `{"url": "string"}` | `ScrapingSellerInput(url: HttpUrl, max_length)` | **MATCH** |
| **Scraping Output Schema** | `{"url", "title", "content", "word_count"}` | `ScrapingSellerOutput` | **MATCH** |
| **Inference Seller ID** | `inference_001` | `inference_001` (`/api/v1/seller/inference`) | **MATCH** |
| **Inference Price** | `0.004 USDC` (4,000 base units) | `amount_units=4000` | **MATCH** |
| **Inference Pay-To** | `settings.inference_seller_pay_to` | `settings.inference_seller_pay_to` | **MATCH** |
| **Inference Input Schema**| `{"prompt": "string", "max_tokens": int}` | `InferenceSellerInput(prompt, max_tokens, temperature)` | **MATCH** |
| **Inference Output Schema**| `{"response", "model_used", "tokens_generated"}` | `InferenceSellerOutput` | **MATCH** |

---

## 3. Protocol Flow and Safety Validation

1. **Unpaid Request Handling:**
   - Emits HTTP 402 with `PAYMENT-REQUIRED` (official Base64 `PaymentRequired`), `X-PAYMENT` (official Base64), and `X-402-Requirement` (legacy JSON).
   - Exposes all headers via `Access-Control-Expose-Headers`.
   - Seller execution is **never** invoked.

2. **Malformed Payment Header:**
   - Invalid Base64, corrupted JSON, or non-schema payloads return `HTTP 400 Bad Request` with `PAYMENT_PAYLOAD_INVALID`.
   - Seller execution is **never** invoked.

3. **Payment Verification Rejection:**
   - Verification failures return `HTTP 402 Payment Required` with `PAYMENT_AUTHORIZATION_FAILED`.
   - No settlement proof header is attached.
   - Seller execution is **never** invoked.

4. **Verifier Unavailable:**
   - If concrete verifier is `None`, returns `HTTP 503 Service Unavailable` with `PAYMENT_VERIFIER_UNAVAILABLE`.
   - Fails closed safely.

5. **Confirmed Settlement followed by Successful Execution:**
   - Verifier returns valid receipt with `tx_hash` or `facilitator_receipt_id`.
   - Seller executes lifecycle only after confirmation.
   - HTTP 200 response attaches `PAYMENT-RESPONSE`, `X-PAYMENT-RESPONSE`, and `X-402-Settlement-Proof`.

6. **Confirmed Settlement followed by Seller Execution Failure:**
   - If seller logic raises an error or times out post-settlement, returns normalized HTTP error (`500` or `504`).
   - **Crucial Invariant:** No settlement proof header is attached to the error response.
   - Prevents fabricated settlement evidence.

7. **Error Message Sanitization:**
   - Internal credentials, database URLs, and connection secrets are redacted in `_handle_seller_exception` and `_verify_and_execute_seller`.

---

## 4. Stage 1 Exit Criteria

- [x] All Seller IDs, prices, endpoints, and schemas match shared contracts.
- [x] Payment-gated execution flow verified fail-closed across all 11 test cases.
- [x] No contract mismatches requiring external module edits.
- [x] Stage 1 exit criteria successfully satisfied.
