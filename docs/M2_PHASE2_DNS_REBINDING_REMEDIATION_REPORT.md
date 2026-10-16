# M2 Phase 2: DNS Rebinding & TOCTOU Security Remediation Report

**Project:** DI-06 AGENTICA — Pay-Per-Call Agent Economy  
**Role:** Member 2 — Seller Agents Technical Lead  
**Task:** DNS Rebinding / Time-of-Check-to-Time-of-Use (TOCTOU) Security Remediation  
**Date:** 2026-10-17  
**Branch:** `M2`  
**Verdict:** **FIXED AND TESTED**  

---

## 1. Executive Summary

Member 2 has designed, implemented, and verified an IP-pinned transport architecture closing the DNS Time-of-Check to Time-of-Use (TOCTOU) vulnerability in the Scraping Seller service (`scraping_001`).

Prior to this remediation, an attacker operating a rapid-TTL DNS rebinding server could return an approved public IP address on the pre-request security check, but respond with a private address (`127.0.0.1` or `169.254.169.254`) when the underlying HTTP client opened a socket, bypassing SSRF policy.

With this remediation:
1. The TCP socket connection is pinned directly to the pre-validated IP address via `PinnedAsyncNetworkBackend`.
2. The HTTP library is completely prevented from performing an uncontrolled second hostname lookup.
3. Original hostnames are strictly preserved for HTTP `Host` headers and TLS Server Name Indication (SNI).
4. TLS certificate validation against the original hostname remains strictly enabled (`verify=True`).
5. Ambient environment proxies are disabled (`trust_env=False`) to avoid proxy-side re-resolution.
6. The actual OS socket peer address is verified post-connect via `anyio.abc.SocketAttribute.remote_address`.
7. Every redirect hop is independently re-resolved, verified, and re-pinned.

**Test Results:** **102 of 102 project tests pass (100%)**, including 17 provider & DNS security tests.

---

## 2. Root Cause Analysis

In standard HTTP client libraries (including `httpx` and `httpcore`), calling `client.get(url)` delegates connection establishment to the default network backend. Even if a pre-request check resolves the hostname via `socket.getaddrinfo`, the HTTP transport resolves the hostname a second time when creating the connection pool. 

This introduces a TOCTOU race:
- **Time of Check:** Application validates DNS record A (`attacker.com -> 93.184.216.34` - Allowed).
- **Time of Use:** HTTP transport opens TCP socket and re-resolves `attacker.com -> 127.0.0.1` (Forbidden).

---

## 3. Chosen Transport Architecture

```
                 +-----------------------------------+
                 | SafeScrapingFetcher.scrape_url()  |
                 +-----------------+-----------------+
                                   |
                1. Syntax & Port Check (ports 80, 443)
                                   v
             +-------------------------------------------+
             |    resolve_and_validate_destination()     |
             |  - socket.getaddrinfo()                   |
             |  - Every IP verified against SSRF rules   |
             |  - Mixed unsafe DNS answer sets rejected  |
             +---------------------+---------------------+
                                   |
                   2. Select approved IP (pinned_ip)
                                   v
             +-------------------------------------------+
             |         PinnedAsyncHTTPTransport          |
             |  - trust_env=False (No proxy hijack)      |
             |  - max_keepalive=0 (No cross-host reuse)  |
             |  - verify=True (TLS cert check intact)    |
             |  - network_backend:                       |
             |      PinnedAsyncNetworkBackend            |
             +---------------------+---------------------+
                                   |
             3. connect_tcp(host, port)
                Routes socket directly to pinned_ip
                NO second DNS lookup is performed
                                   |
                                   v
             +-------------------------------------------+
             |     OS Socket Peer Verification           |
             |  - SocketAttribute.remote_address checked |
             |  - Peer IP must match pinned_ip           |
             +---------------------+---------------------+
                                   |
             4. HTTPS start_tls(server_hostname=host)
                SNI sends original domain;
                Cert validated against original domain
                                   v
             +-------------------------------------------+
             |         Safe Bounded Data Transfer        |
             |  - Stream body <= 1 MB                    |
             |  - Manual redirect re-resolution loop     |
             |  - Clean HTML extraction <= 50,000 chars  |
             +-------------------------------------------+
```

---

## 4. Key Security Controls & Implementation Details

### 4.1 Connection-Time Destination Pinning
- **File:** [`backend/sellers/providers/scraping/transport.py`](file:///c:/AgentMarket/backend/sellers/providers/scraping/transport.py)
- `PinnedAsyncNetworkBackend.connect_tcp()` intercepts socket connection creation and directs the OS socket to `self._pinned_ip` on the requested port, completely bypassing transport-level DNS resolution.

### 4.2 TLS Hostname Preservation & Certificate Verification
- When establishing TLS, `httpcore` calls `stream.start_tls(ssl_context, server_hostname=host)`.
- Because `host` retains the original domain name (e.g., `example.com`), TLS SNI transmits the correct domain and certificate validation verifies that the certificate presented by the server matches the requested domain.
- **TLS verification is never disabled.**

### 4.3 OS-Level Connected Peer Address Verification
- `PinnedAsyncNetworkBackend` reads `anyio.abc.SocketAttribute.remote_address` directly from the connected raw OS socket.
- If the connected peer IP does not match `_pinned_ip` (e.g., due to transparent routing or socket hijacking), the connection is immediately aborted with `ProviderSSRFBlockedError`.

### 4.4 Mixed DNS Answer Set Policy
- If a domain resolves to multiple addresses (e.g. `[93.184.216.34, 10.0.0.1]`), `resolve_and_validate_destination` strictly rejects the entire resolution set.

### 4.5 Environment Proxy Isolation
- `PinnedAsyncHTTPTransport` sets `trust_env=False`. Ambient environment variables (`HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`) cannot override direct socket routing.

### 4.6 Manual Per-Hop Redirect Re-validation
- Automatic redirect following is disabled (`follow_redirects=False`).
- Every redirect hop extracts the `Location` header, calculates the absolute URL, validates syntax, performs fresh DNS resolution and SSRF validation, and constructs a fresh `PinnedAsyncHTTPTransport` pinned to the new destination IP.

---

## 5. Verification Matrix

| Verification Tier | Description | Status | Evidence |
| :---: | :--- | :---: | :--- |
| **Tier A** | Code Inspected | **VERIFIED** | `transport.py`, `fetcher.py`, `safety.py` inspected and reviewed. |
| **Tier B** | Unit Tested | **VERIFIED** | Syntax, scheme, port, and IP range validators pass offline unit tests. |
| **Tier C** | Controlled Transport Tested | **VERIFIED** | Simulated DNS rebinding, peer mismatch, transport creation, and mixed DNS sets pass in `test_sellers_providers.py`. |
| **Tier D** | Live External Network Tested | **DEFERRED (SAFE)** | Standard test suite intentionally operates offline without contacting arbitrary third-party websites or cloud metadata services. |

---

## 6. Test Suite Results

```bash
python -m pytest backend/tests/test_sellers_providers.py -v
```
**Results:** **17 passed in 0.26s**
- `test_provider_settings_defaults` PASSED
- `test_missing_live_configuration_fails_safely` PASSED
- `test_fake_data_provider_outputs` PASSED
- `test_configured_data_provider_mocked_http` PASSED
- `test_url_syntax_and_scheme_restrictions` PASSED
- `test_ip_address_destination_safety` PASSED
- `test_destination_resolution_and_integer_ip_blocking` PASSED
- `test_safe_scraping_fetcher_redirect_to_private_target_blocked` PASSED
- `test_safe_scraping_content_extraction_and_prompt_injection_safety` PASSED
- `test_fake_inference_provider_outputs` PASSED
- `test_configured_inference_provider_mocked_llm` PASSED
- `test_seller_concurrency_bounding` PASSED
- `test_pinned_network_backend_routes_directly_to_ip` PASSED
- `test_pinned_network_backend_rejects_peer_mismatch` PASSED
- `test_pinned_network_backend_rejects_forbidden_pinned_ip` PASSED
- `test_dns_rebinding_simulation_prevented_by_pinning` PASSED
- `test_mixed_dns_answer_set_strictly_rejected` PASSED

```bash
python scripts/run_tests.py
```
**Results:** **102 passed in 1.03s (100% pass rate)**

---

## 7. Final Verdict

**Verdict:** **FIXED AND TESTED**

The DNS rebinding / TOCTOU vulnerability is closed at the transport level. The actual TCP connection is pinned to an approved IP address, OS peer address validation is enforced, TLS certificate verification is preserved, and all 102 project regression tests pass.
