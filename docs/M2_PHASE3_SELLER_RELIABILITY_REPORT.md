# M2 Phase 3 Stage 3: Seller Execution Reliability Report

**Author:** Member 2 — Seller Agents Technical Lead  
**Repository:** `C:\AgentMarket`  
**Date:** 2026-10-17  
**Stage:** Stage 3 (Seller Execution Reliability)  

---

## 1. Objective

Provide an authoritative assessment of execution reliability, resource safety, concurrency bounding, input/output validation, error sanitization, timeout behavior, and network-level security protections across the Seller subsystem.

---

## 2. Core Reliability Mechanisms (`BaseSellerService`)

### A. Strict Two-Phase Schema Validation
1. **Pre-Execution Input Validation:** Incoming payloads are validated against the declared Pydantic input model (`input_model`) *before* entering concurrency-limiting semaphores and before any provider or network operations.
2. **Post-Execution Output Validation:** Returned data is validated against the declared Pydantic output model (`output_model`) *before* returning HTTP 200. Output schema violations raise `SellerOutputValidationError` (HTTP 502) and never return corrupted data.

### B. Concurrency Bounding & Semaphore Correctness
- Each seller service initializes an `asyncio.Semaphore(max_concurrency)` (default: 50 concurrent requests).
- Enforced via an async context manager (`async with self.semaphore:`).
- Guaranteed release upon normal completion, unhandled exception, domain error, or cancellation.
- Verified in `test_seller_concurrency_bounding`.

### C. Async Timeout Handling & Cancellation Limitations
- Enforced via `asyncio.wait_for(..., timeout=effective_timeout)`.
- On timeout expiry, raises `SellerExecutionTimeoutError` (HTTP 504 Gateway Timeout).
- **Critical Technical Limitation Note on `asyncio.wait_for`:**
  - While `asyncio.wait_for` cancels the wrapping asyncio task and releases the concurrency semaphore, it cannot guarantee immediate abort of synchronous blocking I/O or ongoing socket operations in lower-level C libraries if they do not yield to the event loop.
  - To mitigate this, lower-level socket operations in `httpx` and `httpcore` are configured with explicit socket connect and read timeouts (`connect=5.0s`, `read=10.0s`), ensuring operating system socket closure even if an asyncio task cancellation is delayed.

---

## 3. Scraping Security & Network Transport Defense

### A. SSRF & Anti-Rebinding Protections
1. **URL & Port Policy (`safety.py`):**
   - Strictly permits `http://` and `https://` schemes.
   - Enforces permitted ports: `80` and `443`.
   - Blocks embedded userinfo tricks (`http://user:pass@host`).
   - Blocks integer IP obfuscation (e.g. `2130706433`).
2. **IP Safety Validation:**
   - Validates all resolved IPs against RFC private, loopback, link-local, carrier-grade NAT, and cloud metadata (`169.254.169.254`, `fd00:ec2::254`, `100.100.100.200`).
   - Checks IPv4-mapped IPv6 representations (`::ffff:127.0.0.1`).
   - If a domain resolves to a mixed answer set (one public, one private), the answer set is strictly rejected.
3. **Connect-Time IP Pinning (`PinnedAsyncHTTPTransport`):**
   - Directs the TCP socket connect call directly to the validated IP, preventing secondary DNS lookup races (DNS rebinding / TOCTOU).
   - Preserves original hostname for TLS SNI and server certificate validation.
   - Verifies the OS connected peer address via `anyio.abc.SocketAttribute.remote_address`.
   - Prohibits cross-target connection reuse (`max_keepalive_connections=0`).
4. **Per-Redirect Independent Pinning:**
   - Each HTTP 3xx redirect location is parsed, safety-validated, independently resolved, and pinned with a new transport instance.
   - Bounded to a maximum of 3 redirects (`scraping_max_redirects`).

### B. Private Dependency API Disclosures & Risks
`PinnedAsyncHTTPTransport` relies on:
- `httpcore._backends.anyio.AnyIOBackend`
- `httpx._transports.default.create_ssl_context`

| Dependency | Tested Version | Risk Level | Mitigation & Maintenance Strategy |
|---|---|---|---|
| `httpx` | `0.28.1` | Low | Uses `create_ssl_context` for standard SSL context generation. |
| `httpcore` | `1.0.9` | Medium | Inherits `httpcore.AsyncNetworkBackend` and delegates to `AnyIOBackend`. If `httpcore` refactors its backend module paths in a future major version, imports may need updating. |

*Recommendation:* Pin dependencies in production deployment: `httpx>=0.27.0,<0.29.0` and `httpcore>=1.0.0,<1.1.0`.

---

## 4. Execution Telemetry & Error Sanitization

1. **Metrics Tracking:** Every seller execution records `duration_ms`, `success`, `timed_out`, and `output_validated` within `ExecutionMetrics`.
2. **Correlation ID:** Context preserves `request_id` and forwards client-supplied `Idempotency-Key`.
3. **Secret Redaction:**
   - `_handle_seller_exception` redacts database URLs (`postgresql://`, `mysql://`, `redis://`), passwords, and API keys.
   - Log statements avoid printing raw payment payloads or full scraped content.

---

## 5. Stage 3 Exit Criteria

- [x] Input and output schema validation verified before and after execution.
- [x] Semaphore concurrency limits and timeout releases verified.
- [x] Cancellation caveats and socket timeout mitigation documented.
- [x] Scraping SSRF, DNS pinning, TLS verification, and redirect safety intact.
- [x] Private `httpx`/`httpcore` dependencies and version constraints documented.
