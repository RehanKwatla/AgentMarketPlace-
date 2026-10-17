# M2 Phase 3: Seller Subsystem Demo Checklist & Walkthrough Script

**Author:** Member 2 — Seller Agents Technical Lead  
**Repository:** `C:\AgentMarket`  
**Date:** 2026-10-17  
**Stage:** Stage 6 (Demo Readiness)  

---

## 1. Demo Scenario Overview

This script guides presenters through a complete, verifiable demonstration of the Seller microservices, highlighting:
1. HTTP 402 challenge flow with official and legacy headers.
2. Verified paid execution returning genuine settlement evidence.
3. Provider failure / timeout handling with zero fabricated settlement proofs.
4. Provider mode switching (Fake vs Live Gemini/Groq).

---

## 2. Step-by-Step Demo Walkthrough

### Step 1: Health & Registry Discovery
- **Action:** Query the service catalog to locate the three seller services:
  ```bash
  curl -s http://localhost:8000/api/v1/services | jq .
  ```
- **Observed Result:**
  - `data_001` (price: 0.002 USDC / 2000 units)
  - `scraping_001` (price: 0.003 USDC / 3000 units)
  - `inference_001` (price: 0.004 USDC / 4000 units)

### Step 2: Unpaid Request (402 Payment Challenge)
- **Action:** Call the Data Seller endpoint without payment headers:
  ```bash
  curl -i -X POST http://localhost:8000/api/v1/seller/data \
    -H "Content-Type: application/json" \
    -d '{"symbol": "ETH"}'
  ```
- **Key Points to Highlight:**
  - Status code: `402 Payment Required`.
  - Header: `PAYMENT-REQUIRED` (official Base64-encoded `PaymentRequired`).
  - Header: `X-PAYMENT` (official alternative).
  - Header: `X-402-Requirement` (legacy JSON).
  - Header: `Access-Control-Expose-Headers` containing all x402 headers.
  - **Security Guarantee:** Seller data logic was NOT executed.

### Step 3: Verified Paid Execution (Dual-Header Delivery)
- **Action:** Submit task through Buyer Agent or seller route with signed `PAYMENT-SIGNATURE`:
  ```bash
  curl -i -X POST http://localhost:8000/api/v1/seller/data \
    -H "Content-Type: application/json" \
    -H "PAYMENT-SIGNATURE: <base64_signed_payload>" \
    -d '{"symbol": "ETH"}'
  ```
- **Key Points to Highlight:**
  - Status code: `200 OK`.
  - Content: Valid JSON with `symbol`, `price`, `volume_24h`, and `timestamp`.
  - Header: `PAYMENT-RESPONSE` (official Base64-encoded `SettleResponse`).
  - Header: `X-PAYMENT-RESPONSE`.
  - Header: `X-402-Settlement-Proof` containing confirmed transaction hash or facilitator receipt.

### Step 4: Scraping Seller SSRF Defense Demo
- **Action:** Attempt to call Scraping Seller targeting a loopback or internal address:
  ```bash
  curl -i -X POST http://localhost:8000/api/v1/seller/scraping \
    -H "Content-Type: application/json" \
    -d '{"url": "http://169.254.169.254/latest/meta-data/"}'
  ```
- **Key Points to Highlight:**
  - Request rejected immediately with `422 Unprocessable Entity` or `400 Bad Request`.
  - Destination IP is flagged as prohibited cloud metadata.
  - Socket connect is blocked before any network packet is dispatched.

### Step 5: Provider Failure Isolation
- **Action:** Demonstrate error behavior when an upstream provider times out or fails post-settlement:
- **Key Points to Highlight:**
  - Returns normalized HTTP 500 or 504 error.
  - **Critical Invariant:** No `PAYMENT-RESPONSE` or `X-402-Settlement-Proof` header is attached to the error response.
  - Settlement proof is never fabricated on failed service delivery.

---

## 3. Demo Verification Checklist

- [ ] Backend runs smoothly on `http://localhost:8000`.
- [ ] `GET /health` returns `{"status": "healthy"}`.
- [ ] All three seller endpoints return HTTP 402 with official headers when called unpaid.
- [ ] Data, Scraping, and Inference endpoints produce schema-valid JSON on authorized requests.
- [ ] Scraping seller blocks private IPs (`127.0.0.1`, `10.0.0.1`, `169.254.169.254`).
- [ ] Error messages do not leak internal API keys or passwords.
- [ ] Full regression suite (171 tests) passes before demo.
