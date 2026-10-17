# AGENTICA — PHASE 7 SELLER, PROVIDER, AND SSRF SECURITY AUDIT

**Phase:** 7.4 Seller Boundary, Provider Modes, and SSRF Security  
**Date:** 2026-10-17  
**Module Owners:** Member 2 (`backend/sellers/`) & Application Security Lead  
**Evidence Classification:** VERIFIED BY AUTOMATED TESTS & VERIFIED BY CODE INSPECTION  
**Status:** **ACCEPTED**  

---

## 1. Executive Summary

This audit assesses the security controls, execution boundaries, and network protection mechanisms across AGENTICA's seller microservices (`data_001`, `scraping_001`, `inference_001`). All 80 seller-related tests across the test suite execute cleanly and pass without errors.

```
backend/tests/test_sellers_foundation.py (17 tests) PASSED [0.36s]
backend/tests/test_sellers_payment_integration.py (21 tests) PASSED [0.82s]
backend/tests/test_sellers_providers.py (28 tests) PASSED [0.95s]
backend/tests/test_sellers_x402_compatibility.py (20 tests) PASSED [0.49s]
Total: 80 passed in 2.62s
```

---

## 2. Pre-Execution Payment Gate Verification

Every seller endpoint (`POST /sellers/data_001/execute`, `POST /sellers/scraping_001/execute`, `POST /sellers/inference_001/execute`) strictly enforces the x402 payment gate in `backend/sellers/base.py`:
1. **Unpaid Request Rejection:** In requests lacking a valid payment authorization header (`X-402-Payment-Payload` or `PAYMENT-SIGNATURE`), the server emits an HTTP 402 challenge specifying network (`eip155:84532`), token (`0x036CbD53842c5426634e7929541eC2318f3dCF7e`), recipient, amount in atomic units, and fresh challenge nonce.
2. **Zero Upstream Execution:** Business logic methods (`_execute_business_logic`) and third-party API/scraping requests are strictly barred from execution until payment terms and settlement proof are verified.
3. **Receipt Validation:** Proof is validated against challenge terms. If receipt is invalid, reverted, underpaid, or malformed, execution is aborted immediately with HTTP 402.

---

## 3. Provider Operating Modes & Fail-Closed Integrity

AGENTICA defines two distinct provider modes configured via `SELLER_PROVIDER_MODE`:
- **`fake` (Deterministic Offline Simulation):** Default mode for test suites and offline demonstrations. Returns synthetic data strictly adhering to registered Pydantic schemas.
- **`live` (Production / Testnet External Integration):** Calls external APIs (Gemini 2.5 Flash, Groq Qwen/Llama, live HTTP scrapers).

### Fail-Closed Invariant
In `live` mode:
- Missing vendor API keys (`GEMINI_API_KEY`, `GROQ_API_KEY`) immediately raise `ProviderConfigurationError` (HTTP 503).
- Network errors, upstream provider outages (HTTP 502/503), or rate limits (HTTP 429) raise specific provider exceptions.
- **Zero Silent Fallback:** The system **never** silently substitutes fake or cached data in live mode when an external provider fails.

---

## 4. Defense-in-Depth SSRF & Network Protections

For web scraping tasks (`scraping_001`), untrusted URLs undergo multi-tier defenses before and during socket connection:

### 4.1 URL Syntax & Scheme Restrictions
In `backend/sellers/providers/scraping/safety.py`:
- **Allowed Schemes:** `http://` and `https://` only. `file://`, `gopher://`, `ftp://`, and `data:` are blocked.
- **Port Restrictions:** Standard web ports `80` and `443` only. Internal services or unusual ports (`22`, `8080`, `3306`, etc.) are rejected.
- **Userinfo Restrictions:** URLs with embedded credentials (e.g. `http://user:pass@evil.com`) are blocked.
- **Blocked Hostname Patterns:** `localhost`, `*.internal`, `*.local`, and known cloud metadata domains are blocked before DNS lookup.

### 4.2 Comprehensive Destination IP Filtering
Destination hostnames are resolved and all returned A/AAAA records are filtered against forbidden IP ranges:
- **Loopback:** `127.0.0.0/8`, `::1`
- **RFC 1918 Private:** `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`
- **Cloud Metadata Service:** `169.254.169.254`, `fe80::/10`
- **Carrier-Grade NAT:** `100.64.0.0/10`
- **Multicast / Broadcast:** `224.0.0.0/4`, `255.255.255.255`
- **Mixed Answer Sets:** If DNS returns multiple IP addresses and *any* address in the set is private or forbidden, the entire answer set is rejected.

### 4.3 Connect-Time Socket IP Pinning (DNS Rebinding Defense)
In `backend/sellers/providers/scraping/transport.py`:
- `PinnedAsyncHTTPTransport` and `PinnedAsyncNetworkBackend` intercept the low-level TCP connection (`connect_tcp`).
- The connection is opened directly to the pre-validated IP address, bypassing any secondary OS or library DNS resolution.
- TLS Server Name Indication (SNI) and HTTP `Host` headers preserve the original hostname.
- Certificate validation is strictly enforced (`verify=True`).
- Environment proxy auto-discovery is disabled (`trust_env=False`) to prevent proxy redirection.
- The connected OS peer address is verified post-handshake via `anyio.abc.SocketAttribute.remote_address`; any peer mismatch immediately closes the stream and raises `ProviderSSRFBlockedError`.

### 4.4 Redirect Re-Validation
`SafeScrapingFetcher` sets `follow_redirects=False` and manually intercepts HTTP 3xx responses:
- Every redirect hop is resolved and re-evaluated through the full SSRF validation and socket pinning pipeline.
- Maximum redirect hops are bounded by `scraping_max_redirects` (default: 3).

### 4.5 Content Sanitization & Prompt-Injection Neutralization
- HTML parser (`extract_clean_content`) removes `<script>`, `<style>`, and active markup.
- Scraped content is treated strictly as inert raw text. Text strings resembling prompt injections (e.g., "Ignore all previous instructions") are never interpreted as instructions.
- Bounded memory limits enforce `scraping_max_response_bytes` (1 MB) and `scraping_max_extract_chars` (10,000 chars).

---

## 5. Secret Sanitization & Error Handling

- Custom exception handlers in `backend/sellers/base.py` and `backend/main.py` sanitize outgoing response bodies.
- Bearer tokens, private keys, API keys, and internal tracebacks are stripped from error payloads.
- Client responses receive normalized errors (e.g. `503 Service Unavailable`, `402 Payment Required`, `400 Bad Request`) with structured error codes.

---

## 6. Audit Verdict

| Security Domain | Requirement | Observed Status | Evidence Classification |
|---|---|---|---|
| Pre-Execution Gate | Require payment proof before seller workload | **PASS** | VERIFIED BY AUTOMATED TESTS |
| Provider Modes | Fail closed in live mode; no silent fallback | **PASS** | VERIFIED BY AUTOMATED TESTS |
| SSRF Defense | Block private, loopback, link-local, metadata IPs | **PASS** | VERIFIED BY AUTOMATED TESTS |
| DNS Rebinding | Connect-time IP pinning & socket peer check | **PASS** | VERIFIED BY AUTOMATED TESTS |
| Redirect Safety | Re-validate destination at every 3xx redirect hop | **PASS** | VERIFIED BY AUTOMATED TESTS |
| Secret Sanitization | Redact API keys and credentials from logs/errors | **PASS** | VERIFIED BY CODE INSPECTION & TESTS |

**Phase 7 Gate 4 Status:** **ACCEPTED**.
