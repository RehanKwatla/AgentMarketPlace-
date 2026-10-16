# M2 Phase 2: DNS Rebinding & TOCTOU Security Audit

**Role:** Member 2 — Seller Agents Technical Lead  
**Task:** DNS Rebinding / Time-of-Check-to-Time-of-Use (TOCTOU) Security Remediation  
**Date:** 2026-10-17  
**Branch:** `M2` (Commit: `4372671`)  

---

## 1. Executive Summary

This audit investigates the HTTP request lifecycle of the Scraping Seller service (`scraping_001`), focusing specifically on how destination hostnames are parsed, resolved, validated, and connected to via `httpx`.

The previous implementation resolved hostnames using `socket.getaddrinfo()` and checked each returned IP against forbidden destination rules (loopback, private RFC1918 subnets, cloud metadata, carrier-grade NAT, and IPv4-mapped IPv6). However, the resulting connection was established by passing the original URL string (`current_url`) to `httpx.AsyncClient.get()`. 

Because standard HTTP client libraries (including `httpx` backed by `httpcore`) perform an internal DNS lookup when opening a connection pool or socket stream, an unpinned request creates a **DNS Time-of-Check to Time-of-Use (TOCTOU) gap**:
1. Initial validation queries DNS: `attacker.com -> 93.184.216.34` (Public, permitted).
2. Security check passes.
3. Milliseconds later, `httpx` opens a socket and queries DNS again: `attacker.com -> 127.0.0.1` or `169.254.169.254` (Private metadata / loopback).
4. The socket connects to the forbidden internal address despite the earlier check.

---

## 2. Request Execution Flow Analysis

### Current Sequence in `SafeScrapingFetcher`:
1. **URL Syntax Check:** `validate_url_syntax(url)` verifies scheme (`http`/`https`), disallows userinfo (`user:pass@host`), restricts ports to `80` and `443`, and rejects blocked hostnames (`localhost`, `metadata.google.internal`, etc.).
2. **Pre-Flight DNS Resolution:** `resolve_and_validate_destination(parsed.hostname)` calls `socket.getaddrinfo(hostname, None)` and validates every returned IP address.
3. **HTTP Client Invocation:**
   ```python
   async with (self._client or httpx.AsyncClient(timeout=timeout, follow_redirects=False)) as client:
       res = await client.get(current_url, headers=...)
   ```
4. **Independent DNS Resolution:** `httpx` delegates connection establishment to its underlying transport (`httpcore.AsyncConnectionPool`). In standard operation, `httpcore` calls its default network backend (`AnyIOBackend.connect_tcp`), which performs its own independent DNS resolution of `current_url.host`.
5. **TOCTOU Gap Identified:** The connection is not bound to the IP validated in step 2. If the DNS response changes between step 2 and step 4, the socket connects to an unvalidated destination.

---

## 3. Dependency & Environment Analysis

- **Python Version:** 3.14.3
- **httpx Version:** 0.28.1
- **httpcore Version:** 1.0.9
- **Network Backend:** `httpcore` supports customizable `network_backend: AsyncNetworkBackend` within `httpcore.AsyncConnectionPool`.
- **AnyIO Socket Attributes:** `anyio.abc.SocketAttribute.remote_address` is supported on the active socket stream, allowing actual OS-level connected peer IP verification.

---

## 4. Remediation Architecture Design

To close the DNS TOCTOU vulnerability completely without disabling TLS verification or breaking HTTP semantics:

1. **Custom Pinned Network Backend (`PinnedAsyncNetworkBackend`):**
   - Subclasses `httpcore.AsyncNetworkBackend`.
   - In `connect_tcp(self, host, port, ...)`: Intercepts the connection request and directs the actual TCP socket connection to the pre-validated, approved destination IP (`self._pinned_ip`).
   - Prevents `httpcore`/`httpx` from performing a second, unvalidated DNS query.
2. **Preservation of TLS SNI & Hostname Verification:**
   - In `connect_tcp`, the original hostname is preserved in the request structure.
   - When HTTPS is used, `httpcore` invokes `stream.start_tls(ssl_context, server_hostname=host)`.
   - TLS SNI sends the original domain name, and the server certificate is verified strictly against the original domain name (not the IP address). Certificate verification remains enabled (`verify=True`).
3. **OS-Level Connected Peer Address Verification:**
   - The established socket stream queries the OS-level socket for `anyio.abc.SocketAttribute.remote_address`.
   - Asserts that the connected peer IP exactly matches the pinned IP and passes all SSRF destination checks.
4. **Environment Proxy Isolation:**
   - The transport explicitly sets `trust_env=False` to prevent ambient environment proxies (`HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`) from intercepting or rerouting direct pinned socket connections.
5. **Per-Hop Manual Redirect Pinning:**
   - With `follow_redirects=False`, each redirect hop extracts the `Location` header, re-validates URL syntax, performs independent DNS resolution and safety checks, and creates a fresh pinned transport for the next destination.
