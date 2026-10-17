# AGENTICA — PHASE 6 SELLER BOUNDARY & SECURITY AUDIT

**Phase:** 6.4 Seller Boundary, Provider Modes, and SSRF Review  
**Status:** **ACCEPTED**  
**Date:** 2026-10-17  
**Module Owner:** Member 2 (`backend/sellers/`) & Application Security  
**Evidence Classification:** VERIFIED BY AUTOMATED TESTS & VERIFIED BY CODE INSPECTION  

---

## 1. Executive Summary

This audit evaluates the execution boundaries, provider operating modes, input/output validation, secret sanitization, and SSRF protections across AGENTICA's seller microservices (`data_001`, `scraping_001`, `inference_001`). All 80 dedicated tests in `backend/tests/` passed cleanly (`80 passed in 2.59s`).

### Key Verified Capabilities:
1. **Pre-Execution Payment Gate:** Seller endpoints in `backend/sellers/routes.py` require verified payment before dispatching any provider workload. Requests without payment receive HTTP 402 challenges with zero provider execution.
2. **Explicit Provider Modes & Zero Silent Fallbacks:** In `SELLER_PROVIDER_MODE=live`, missing vendor API keys (`GEMINI_API_KEY`, `GROQ_API_KEY`) or network errors fail closed immediately with `ProviderConfigurationError`. The system **never** silently substitutes fake or cached data in live mode.
3. **Defense-in-Depth SSRF Protections:** `SafeScrapingFetcher` validates URL schemes (HTTP/HTTPS only), blocks private, loopback, link-local, carrier-grade NAT, and cloud metadata (169.254.169.254) addresses, validates DNS answers, re-validates all HTTP 3xx redirects, and enforces socket-level IP pinning (`PinnedNetworkBackend`) to prevent DNS rebinding.
4. **Secret Sanitization:** Exception handlers in `backend/sellers/base.py` redact authorization headers, bearer tokens, and private keys from client responses and logs.

---

## 2. Provider Operating Modes

| Setting | Mode | Behavior | Fallback Policy |
|---|---|---|---|
| `SELLER_PROVIDER_MODE=fake` | Deterministic Offline | Returns synthetic data matching registered schemas | Default for tests and demos |
| `SELLER_PROVIDER_MODE=live` | Production / Live | Calls external Gemini Flash 3.8, Groq Qwen, or financial APIs | **Fails closed on error. Zero fallback to fake.** |

---

## 3. SSRF & Network Boundary Protections

In `backend/sellers/providers.py`:
- **Allowed Schemes:** `http://` and `https://` only. Schemes like `file://`, `gopher://`, `ftp://` are rejected.
- **Blocked IP Ranges:**
  - Loopback (`127.0.0.0/8`, `::1`)
  - RFC 1918 Private (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`)
  - Cloud Instance Metadata (`169.254.169.254`, `fe80::/10`)
  - Carrier-Grade NAT (`100.64.0.0/10`)
  - Multicast/Broadcast (`224.0.0.0/4`, `255.255.255.255`)
- **DNS Rebinding Prevention (Socket IP Pinning):**
  - Resolves host DNS once and validates all returned A/AAAA records against the IP filter.
  - Rejects mixed answer sets containing both public and private addresses.
  - Connects the underlying TCP socket directly to the verified pinned IP address while preserving HTTP `Host` headers and TLS Server Name Indication (SNI).
  - Intercepts all HTTP 3xx redirects and re-runs the entire DNS resolution, IP check, and socket pinning pipeline.

> [!NOTE]
> SSRF protections are implemented and verified by automated tests covering tested vectors. Residual risk remains subject to external penetration testing and ongoing application security reviews.

---

## 4. Automated Test Evidence

```
backend/tests/test_sellers_foundation.py (11 tests) PASSED
backend/tests/test_sellers_payment_integration.py (21 tests) PASSED
backend/tests/test_sellers_providers.py (28 tests) PASSED
backend/tests/test_sellers_x402_compatibility.py (20 tests) PASSED
[80 passed in 2.59s]
```

**Gate Status:** PHASE 6 GATE D (SELLER & DEPLOYMENT SAFETY) — **PASSED**.
