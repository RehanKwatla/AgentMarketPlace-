# AGENTICA — PHASE 5 SELLER & PROVIDER HARDENING AUDIT

**Phase:** 5.7 Seller and Provider Hardening  
**Status:** ACCEPTED  
**Date:** 2026-10-17  
**Module Owner:** Member 2 (`backend/sellers/`) & Application Security  
**Evidence Classification:** VERIFIED BY AUTOMATED TESTS & VERIFIED BY CODE INSPECTION  

---

## 1. Executive Summary

This document audits the reliability, input/output validation, secret sanitization, and network security boundaries of AGENTICA's seller microservices (`data_001`, `scraping_001`, `inference_001`). 

All 100 dedicated seller unit, integration, and security tests in `backend/tests/` passed without failure (`100 passed in 3.05s`).

Key verified boundaries:
- **Zero Silent Fallbacks:** When configured for `SELLER_PROVIDER_MODE=live`, missing API keys (`GEMINI_API_KEY`, `GROQ_API_KEY`) or network errors fail closed with explicit diagnostic errors (`ProviderConfigurationError`). The system **never** silently substitutes mock or fake responses in live mode.
- **SSRF Boundary Protections:** The scraping provider implements multi-layer defense against Server-Side Request Forgery, including scheme whitelisting, private IP range blocking, integer/hex IP decoding, mixed DNS answer set rejection, redirect re-validation, and custom socket-level IP pinning to prevent DNS rebinding.
- **Fail-Closed Verification:** If the payment verifier is unreachable or returns malformed data, seller execution halts with HTTP 503 or 402; no provider workload is executed without valid payment proof.
- **Strict Error Sanitization:** Private keys, signing keys, and vendor authorization headers are redacted from error responses and logs.

---

## 2. Provider Operating Modes

In `backend/sellers/providers.py` and `backend/shared/config.py`:
- `SELLER_PROVIDER_MODE=fake` (Default for local testing and CI):
  - Deterministic fake data generation.
  - No external HTTP or LLM API calls.
  - 100% offline reproducible demo.
- `SELLER_PROVIDER_MODE=live`:
  - `inference_001` connects directly to Google Gemini (`gemini-3.8-flash`) or Groq Cloud (`qwen/qwen3.8-27b`).
  - `data_001` queries configured financial market providers.
  - `scraping_001` dispatches real web fetches through `SafeScrapingFetcher`.
  - If required vendor keys are absent, raises `ProviderConfigurationError` immediately.

---

## 3. Server-Side Request Forgery (SSRF) Hardening

The scraping provider `SafeScrapingFetcher` implements defense-in-depth protections:

### 3.1 Scheme & Hostname Validation
- Only `http` and `https` schemes are permitted. Schemes like `file://`, `gopher://`, `ftp://`, `ldap://` are rejected.
- Target hostnames cannot be empty or local unqualified names.

### 3.2 IP Address Confinement
Before connecting, the target IP is checked against forbidden ranges:
- Loopback (`127.0.0.0/8`, `::1`)
- Private networks (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `fc00::/7`)
- Cloud instance metadata service (`169.254.169.254`, `fe80::/10`)
- Carrier-Grade NAT (`100.64.0.0/10`)
- Broadcast and multicast addresses (`224.0.0.0/4`, `255.255.255.255`)
- Integer, octal, and hexadecimal IP representations (e.g. `2130706433` for `127.0.0.1`) are canonicalized and blocked.

### 3.3 DNS Rebinding Protection via Socket IP Pinning
- In standard HTTP clients, time-of-check to time-of-use (TOCTOU) allows DNS rebinding where an initial public IP changes to an internal IP on the actual TCP connection.
- `SafeScrapingFetcher` utilizes a custom transport (`PinnedNetworkBackend` / `PinnedTransport`) that resolves DNS once, validates all returned A/AAAA records, and pins the TCP socket connection directly to the verified IP address while preserving HTTP `Host` and TLS SNI headers.
- Mixed DNS answer sets (containing both public and private IPs) are rejected outright.
- HTTP 3xx redirects are intercepted and independently re-pinned and re-validated through the entire security pipeline.

> [!NOTE]
> SSRF protections are implemented and covered by the specified automated tests; residual risk remains subject to further application security review. The system is not represented as "immune."

---

## 4. Input & Output Contract Validation

In `backend/sellers/base.py`:
- `BaseSellerService` enforces Pydantic input models on every request before invoking any provider logic.
- Upon provider return, outputs are validated against the service's Pydantic response model.
- If a provider produces an invalid response schema, the seller service raises `SellerOutputValidationError` and returns HTTP 502, preventing invalid data from entering the marketplace.

---

## 5. Automated Test Verification Results

All tests across seller suites:
```
backend/tests/test_sellers_foundation.py (11 tests) PASSED
backend/tests/test_sellers_payment_integration.py (21 tests) PASSED
backend/tests/test_sellers_providers.py (28 tests) PASSED
backend/tests/test_sellers_x402_compatibility.py (14 tests) PASSED
backend/tests/test_sellers.py (26 tests) PASSED
[100 passed in 3.05s]
```

**Gate Status:** PHASE 5 GATE F (SECURITY - Seller & Provider Hardening) — **PASSED**.
