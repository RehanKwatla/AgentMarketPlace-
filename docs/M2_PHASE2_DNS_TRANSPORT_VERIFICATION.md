# M2 PHASE 2 — DNS REBINDING & IP-PINNING TRANSPORT VERIFICATION REPORT

**Project:** DI-06 AGENTICA (Pay-Per-Call Agent Economy)  
**Role:** Member 2 — Seller Agents Technical Lead  
**Branch:** `M2`  
**Target Subsystem:** `backend/sellers/providers/scraping/`  
**Date of Verification:** 2026-10-17  
**Verification Verdict:** **`VERIFIED`**

---

## 1. Executive Summary

This report documents the rigorous verification of the connect-time IP-pinning transport and DNS rebinding remediation implemented for the Scraping Seller service.

The verification examined the exact runtime behavior of the custom transport layer under `httpx 0.28.1` and `httpcore 1.0.9`, confirming that:
1. `PinnedAsyncHTTPTransport` directly replaces the underlying `httpcore.AsyncConnectionPool._network_backend` with `PinnedAsyncNetworkBackend`.
2. Socket connections in `httpcore` bypass all runtime DNS queries for the target hostname and connect directly to the pre-validated IP address passed at transport instantiation.
3. TLS verification remains fully active (`verify_mode = CERT_REQUIRED`, `check_hostname = True`), and the TLS Server Name Indication (SNI) and certificate validation use the original hostname, not the pinned IP.
4. OS-level peer address inspection verifies the actual connected socket address across both IPv4 and IPv6 representations, immediately closing the stream and raising `ProviderSSRFBlockedError` on mismatch.
5. Every HTTP redirect hop creates a newly resolved, independently pinned, and strictly validated transport with `max_keepalive_connections = 0`, eliminating cross-origin socket reuse.
6. The entire automated test suite passes **106 of 106 tests (100%)** with zero regressions.

---

## 2. Dependency Environment

The verification was executed in the active project environment:

| Component | Installed Version | Manifest Requirement | Compatibility Status |
| :--- | :--- | :--- | :--- |
| **Python** | `3.14.3` (AMD64, Windows) | `>=3.11` | Fully Compatible |
| **httpx** | `0.28.1` | `>=0.27.0` | Fully Compatible |
| **httpcore** | `1.0.9` | Implicit via `httpx` | Fully Compatible |
| **AnyIO** | `4.13.0` | Implicit via `httpcore` | Fully Compatible |
| **pytest** | `9.1.1` | `>=8.2.0` | Fully Compatible |

---

## 3. Transport Architecture & Call-Chain Verification

### 3.1 Architecture Overview

The Scraping Seller defense architecture consists of three interlocking security layers:

```
User Scraping Request: "http://attacker-controlled.example/data"
                          │
                          ▼
        [Layer 1: URL Syntax & Policy Validation]
        - Scheme restriction: http / https only
        - Port restriction: 80 / 443 only
        - Reject userinfo credentials (@)
        - Reject localhost, .local, .internal, metadata hostnames
                          │
                          ▼
        [Layer 2: Destination Resolution & IP Safety]
        - socket.getaddrinfo() resolves all A and AAAA records
        - Every IP must pass RFC private, loopback, link-local,
          multicast, reserved, and carrier-grade NAT checks
        - Mixed answer sets (public + private IP) are rejected fail-closed
        - Selected safe IP: e.g. "93.184.216.34"
                          │
                          ▼
        [Layer 3: Connect-Time IP-Pinning Transport]
        - PinnedAsyncHTTPTransport instantiated with pinned_ip="93.184.216.34"
        - Custom httpcore.AsyncConnectionPool created with:
            * network_backend = PinnedAsyncNetworkBackend("93.184.216.34")
            * ssl_context = default TLS context (verify=True, check_hostname=True)
            * max_keepalive_connections = 0 (prohibit socket reuse)
                          │
                          ▼
        [httpcore Connection Establishment]
        - AsyncHTTPConnection._connect() calls:
            network_backend.connect_tcp(host="attacker-controlled.example", port=80)
        - PinnedAsyncNetworkBackend intercepts:
            connects directly to ("93.184.216.34", 80) via AnyIOBackend
            (NO second DNS lookup occurs; attacker DNS changes are inert)
                          │
                          ▼
        [OS Socket Peer Verification]
        - stream._stream.extra(SocketAttribute.remote_address) inspected
        - Verified that connected peer IP == "93.184.216.34"
        - If mismatch: stream.aclose() immediately executed, raises SSRF error
                          │
                          ▼
        [If HTTPS: TLS Handshake & SNI]
        - stream.start_tls(ssl_context, server_hostname="attacker-controlled.example")
        - Hostname checked against server certificate SAN/CN
```

### 3.2 Evidence of Real Pool & Backend Integration

Inspection of `httpcore.AsyncConnectionPool` and `httpx.AsyncHTTPTransport` in the installed packages verified:

1. **Transport Delegation:**
   `httpx.AsyncHTTPTransport.handle_async_request(request)` directly executes:
   ```python
   resp = await self._pool.handle_async_request(req)
   ```
2. **Pool Connection Creation:**
   `httpcore.AsyncConnectionPool.create_connection(origin)` initializes:
   ```python
   return AsyncHTTPConnection(
       origin=origin,
       network_backend=self._network_backend,
       ...
   )
   ```
3. **Connection Socket Hook:**
   `httpcore.AsyncHTTPConnection._connect(request)` executes:
   ```python
   stream = await self._network_backend.connect_tcp(**kwargs)
   ```
4. **Backend Override:**
   `PinnedAsyncHTTPTransport` replaces `self._pool` with an `AsyncConnectionPool` whose `network_backend` is `PinnedAsyncNetworkBackend`. Consequently, every request sent by `httpx.AsyncClient` traverses `PinnedAsyncNetworkBackend.connect_tcp`.

---

## 4. Empirical Test Results

### 4.1 Controlled Local HTTP Integration Test

**Objective:** Verify that an HTTP request issued via `httpx.AsyncClient` with `PinnedAsyncHTTPTransport` reaches the pinned destination IP through the custom network backend, rather than resolving the requested hostname.

**Method:**
A controlled integration test (`test_pinned_transport_end_to_end_http_integration`) initialized a `PinnedAsyncHTTPTransport` with `pinned_ip = "93.184.216.34"`. A client request was made to `http://my-target-host.example:80/data`. The underlying network backend call was recorded.

**Observed Result:**
- `AnyIOBackend.connect_tcp` was invoked with `host = "93.184.216.34"`, `port = 80`.
- The target hostname `"my-target-host.example"` was never queried or passed to the OS socket connection.
- Response `HTTP 200 OK` was successfully received and decoded.
- **Status:** **VERIFIED**

### 4.2 DNS Rebinding / TOCTOU Simulation Test

**Objective:** Verify defense against an attacker whose DNS server returns a valid public IP upon initial security check, but returns `169.254.169.254` (cloud metadata) on subsequent lookup.

**Method:**
`test_dns_rebinding_simulation_prevented_by_pinning` configured an oscillating DNS fixture where lookup #1 returned `93.184.216.34` and lookup #2 returned `169.254.169.254`. `SafeScrapingFetcher.scrape_url("http://dns-rebind-target.com/page")` was invoked while monitoring socket connections.

**Observed Result:**
- Initial safety check resolved and approved `93.184.216.34`.
- The transport layer pinned socket connection directly to `93.184.216.34`.
- The second DNS response (`169.254.169.254`) was never queried by the transport and never contacted.
- Safe content from the pinned destination was extracted without error.
- **Status:** **VERIFIED**

### 4.3 Mixed DNS Answer Set Test

**Objective:** Verify that if DNS returns both a public IP and a forbidden private IP in the same answer set, the destination is completely rejected.

**Method:**
`test_mixed_dns_answer_set_strictly_rejected` simulated DNS resolution returning `[("93.184.216.34", 80), ("10.0.0.1", 80)]`.

**Observed Result:**
- `resolve_and_validate_destination()` iterated over all sockaddr records.
- The presence of `10.0.0.1` immediately triggered `ProviderSSRFBlockedError("Access to private subnet IP '10.0.0.1' is blocked.")`.
- Zero connections were attempted.
- **Status:** **VERIFIED**

### 4.4 HTTPS TLS Verification & SNI Test

**Objective:** Verify that:
1. Sockets connect to the pinned IP.
2. TLS verification remains enabled (`verify=True`).
3. The original hostname is used for certificate verification and SNI.
4. An incorrect certificate hostname is rejected.
5. No insecure SSL context is introduced.

**Method:**
`test_pinned_transport_https_sni_and_cert_verification` inspected `transport._pool._ssl_context` and simulated both a valid HTTPS handshake and an invalid certificate hostname handshake.

**Observed Result:**
- `ssl_context.verify_mode` is `ssl.CERT_REQUIRED` (value `2`).
- `ssl_context.check_hostname` is `True`.
- `stream.start_tls` received `server_hostname = "secure.example.com"` (original domain name), enabling strict SNI and SAN verification.
- When an incorrect certificate was encountered (`mismatched-cert.example.com`), `httpx.ConnectError` was raised.
- **Status:** **VERIFIED**

### 4.5 Socket Peer-Address Verification Test

**Objective:** Verify that the connected socket address is checked at the OS level, handles both IPv4 and IPv6 representations, and immediately closes the stream on mismatch.

**Method:**
- `test_pinned_network_backend_ipv6_peer_verification` tested IPv6 4-element sockaddr `(ip_str, port, flowinfo, scope_id)`.
- `test_pinned_network_backend_rejects_peer_mismatch` tested a socket where the connected peer returned `127.0.0.1` instead of the pinned IP `93.184.216.34`.

**Observed Result:**
- IPv6 4-element sockaddr was correctly parsed, and the matching address passed without error.
- Socket peer mismatch immediately invoked `await stream.aclose()`, terminating the TCP connection, and raised `ProviderSSRFBlockedError("Connected peer IP '127.0.0.1' does not match pinned IP '93.184.216.34'.")`.
- **Status:** **VERIFIED**

### 4.6 Redirects & Connection Reuse Test

**Objective:** Verify that redirects to private targets are blocked, multi-hop redirects independently pin IP per hop, redirect limits are enforced, and connections are not reused across pins.

**Method:**
- Tested redirect to `http://127.0.0.1:80/admin`: verified immediate block before connection.
- Tested redirect from `http://first.com` (pinned to `93.184.216.34`) to `http://second.com/page` (pinned to `104.26.10.228`).
- Tested exceeding `scraping_max_redirects`.
- Inspected `max_keepalive_connections = 0` in `PinnedAsyncHTTPTransport`.

**Observed Result:**
- Redirect to `127.0.0.1` raised `ProviderSSRFBlockedError`.
- Multi-hop redirect created two separate, sequentially pinned transports with `pinned_ip = "93.184.216.34"` and `pinned_ip = "104.26.10.228"`.
- Exceeding maximum redirects raised `ProviderRequestRejectedError("Exceeded maximum allowed redirects (2).")`.
- `max_keepalive_connections = 0` prevents socket reuse across different origins or IP pins.
- **Status:** **VERIFIED**

---

## 5. Regression Test Results

The full test suite was executed across the entire repository:

### Test Execution Commands & Outputs

```powershell
# 1. Provider & Security Test Suite
python -m pytest backend/tests/test_sellers_providers.py -v
# Output: 21 passed in 2.08s (Exit code: 0)

# 2. Seller Foundation & Payment Integration Test Suite
python -m pytest backend/tests/test_sellers_payment_integration.py backend/tests/test_sellers.py backend/tests/test_sellers_foundation.py -v
# Output: 58 passed in 0.70s (Exit code: 0)

# 3. Full Project Test Suite
python scripts/run_tests.py
# Output: 106 passed in 2.36s (Exit code: 0)
# [SUCCESS] ALL TESTS PASSED SUCCESSFULLY!

# 4. Git Diff Check
git diff --check
# Output: Exit code 0 (No whitespace errors or invalid line endings)
```

### Test Count Progression

- **Baseline Phase 1:** 43 tests
- **Phase 2 Baseline:** 97 tests
- **Initial DNS Rebinding Remediation:** 102 tests
- **Comprehensive Verification Suite (with Steps 2-6 tests):** **106 tests** (100% passing)

---

## 6. Analysis of Edge Cases & Remaining Limitations

1. **DNS Server Behavior:**
   If a malicious domain's DNS returns exclusively private or metadata IP addresses, `resolve_and_validate_destination()` rejects the request before transport instantiation. If DNS returns NXDOMAIN or timeouts, it safely fails closed.
2. **Keepalive Overhead:**
   Enforcing `max_keepalive_connections = 0` requires a fresh TCP handshake for subsequent requests. For a web scraping service evaluating untrusted URLs, this slight latency cost is the necessary and optimal design choice to guarantee complete cross-origin socket isolation and prevent socket hijacking.
3. **Non-Standard Ports:**
   The scraper strictly restricts outbound ports to `80` (HTTP) and `443` (HTTPS), preventing port-scanning attacks against internal services on arbitrary ports.
4. **Proxy Bypassing:**
   `trust_env = False` is enforced on both `httpx.AsyncClient` and `PinnedAsyncHTTPTransport`, preventing environment proxy variables (`HTTP_PROXY`, `HTTPS_PROXY`) from redirecting pinned requests to an external proxy that could perform unvalidated secondary DNS resolution.

---

## 7. Verification Checklist

| Step | Description | Result |
| :---: | :--- | :---: |
| **Step 1** | Inspect actual implementation and dependency manifests | **PASS** |
| **Step 2** | Verify `PinnedAsyncHTTPTransport` pool integration & controlled HTTP test | **PASS** |
| **Step 3** | Verify DNS rebinding defense under oscillating DNS records | **PASS** |
| **Step 4** | Verify HTTPS TLS verification, SNI preservation, and bad cert rejection | **PASS** |
| **Step 5** | Verify OS socket peer address check (IPv4 and IPv6) and mismatch stream closure | **PASS** |
| **Step 6** | Verify per-hop redirect validation, independent pinning, and connection isolation | **PASS** |
| **Step 7** | Run regression suite (106 tests) and `git diff --check` | **PASS** |
| **Step 8** | Document verification findings in formal report | **PASS** |

---

## 8. Final Verdict

### **`VERIFIED`**

The connect-time IP-pinning remediation is fully functional, architecturally sound, thoroughly tested under controlled conditions, and completely resolves the DNS rebinding / TOCTOU vulnerability in the Scraping Seller service. The codebase is safe and ready for commit authorization.
