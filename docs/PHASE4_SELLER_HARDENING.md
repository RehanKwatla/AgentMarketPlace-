# AGENTICA — PHASE 4 SELLER & PROVIDER HARDENING REPORT
**Document:** `docs/PHASE4_SELLER_HARDENING.md`  
**Date:** 17 October 2026  
**Auditor:** Member 2 (Seller Subsystem & Security Engineer)  
**Status:** COMPLETE (Stage 5 Master Plan)  
**Classification:** VERIFIED BY AUTOMATED TESTS & LIVE SMOKE VERIFICATION  

---

## 1. Executive Summary

This report documents the security, resource bounding, and multi-provider architecture of the Seller Subsystem. The seller microservices host three paid services:
1. `data_001`: Financial market data feed (2,000 base units = 0.002 USDC).
2. `scraping_001`: Clean web content extractor with DNS-pinning SSRF protection (3,000 base units = 0.003 USDC).
3. `inference_001`: Multi-LLM provider service supporting Google Gemini and Groq Cloud (4,000 base units = 0.004 USDC).

---

## 2. Multi-Provider Architecture

Located in `backend/sellers/providers/`:

```
backend/sellers/providers/
├── config.py                  # Pydantic ProviderSettings with environment configuration
├── data/                      # Concrete data providers (mock / live)
├── scraping/                  # Hardened web scraping engine
│   ├── fetcher.py             # HTTP fetcher with redirect re-validation
│   ├── parser.py              # Readability extraction, tag stripping, prompt injection defense
│   ├── safety.py              # Comprehensive IP & URL destination safety filter
│   └── transport.py           # Custom PinnedAsyncHTTPTransport defeating DNS rebinding
└── inference/                 # Multi-model LLM engine
    ├── configured_provider.py # Dynamic Gemini & Groq router with timeout handling
    └── fake.py                # Deterministic fake provider for offline testing
```

---

## 3. Advanced SSRF Defense & DNS Rebinding Immunity

Web scraping microservices face severe Server-Side Request Forgery (SSRF) and DNS rebinding risks. The `scraping_001` service implements a multi-layer defense in depth:

### 3.1 Pre-Flight Destination Verification (`backend/sellers/providers/scraping/safety.py`)
- **Scheme Enforcement:** Allows only `http://` and `https://`. Rejects `file://`, `ftp://`, `gopher://`, `data:`.
- **IP Address Blacklisting:**
  - Loopback: `127.0.0.0/8`, `::1`
  - RFC1918 Private: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`
  - Link-Local & Cloud Metadata: `169.254.0.0/16`, `fe80::/10`, `metadata.google.internal`
  - Carrier-grade NAT: `100.64.0.0/10`
  - IPv4-Mapped IPv6: `::ffff:127.0.0.1`
  - Integer / Hex IP encodings: `2130706433` (0x7f000001) normalized and blocked.
- **Mixed DNS Set Rejection:** If a hostname resolves to both a public IP and a private IP, it is strictly rejected.

### 3.2 DNS-Pinning Transport (`backend/sellers/providers/scraping/transport.py`)
To prevent **Time-of-Check to Time-of-Use (TOCTOU) DNS Rebinding**:
1. Pre-flight resolves domain name once via DNS.
2. Verified public IP is pinned.
3. Socket connection routes directly to the pinned IP address.
4. TLS SNI and Certificate verification check the original host name.
5. Peer socket address is validated upon connection; any mismatch terminates immediately.
6. HTTP redirects re-run the full verification and pinning pipeline.

---

## 4. Multi-LLM Inference Providers

Implemented in `backend/sellers/providers/inference/configured_provider.py`:
- **Supported Providers & Default Models:**
  - Google Gemini: `gemini-3.8-flash` (with automated thinking budget handling)
  - Groq Cloud: `qwen/qwen3.8-27b`, `llama-3.3-70b-versatile`
- **Fail-Closed Live Mode:**
  - If `provider_mode = "live"` and an API key is missing, it **fails closed** immediately (`ProviderConfigurationError`).
  - It NEVER silently falls back to fake outputs in live mode, avoiding false confidence.
- **Deterministic Offline Mode:**
  - When `provider_mode = "fake"`, deterministic context-aware responses are generated for unit and CI test suites without external API calls or latency.

---

## 5. Input Validation, Resource Limits & Secret Sanitization

1. **Input Bounding:**
   - Inference prompt: max 10,000 characters, whitespace stripped, `max_tokens <= 2000`.
   - Data symbol: alphanumeric ticker string, max 16 chars.
   - Scraping URL: max 2,048 characters, max response length 50,000 characters.
2. **Execution Timeouts:**
   - Seller execution is bounded via `asyncio.wait_for`:
     - Data: 5.0 seconds
     - Scraping: 10.0 seconds
     - Inference: 15.0 seconds
   - Timeouts cancel cooperative coroutines and return standardized HTTP 504 `SELLER_TIMEOUT`.
3. **Secret Sanitization:**
   `_handle_seller_exception()` in `backend/sellers/routes.py` redacts internal exceptions, database URLs, and API tokens, ensuring error responses leak zero server internals.

---

## 6. Test Evidence Matrix (`backend/tests/test_sellers_providers.py`)

All 29 provider tests passed:
- `test_url_syntax_and_scheme_restrictions`: PASSED
- `test_ip_address_destination_safety`: PASSED
- `test_destination_resolution_and_integer_ip_blocking`: PASSED
- `test_safe_scraping_fetcher_redirect_to_private_target_blocked`: PASSED
- `test_safe_scraping_content_extraction_and_prompt_injection_safety`: PASSED
- `test_dns_rebinding_simulation_prevented_by_pinning`: PASSED
- `test_mixed_dns_answer_set_strictly_rejected`: PASSED
- `test_pinned_transport_https_sni_and_cert_verification`: PASSED
- `test_gemini_inference_provider_mocked`: PASSED
- `test_groq_inference_provider_mocked`: PASSED
- `test_live_mode_never_falls_back_to_fake_silently`: PASSED
- `test_seller_concurrency_bounding`: PASSED
