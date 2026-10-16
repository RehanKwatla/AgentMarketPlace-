# M2 Phase 3: Scraping Transport Security Review

**Reviewer:** Member 2 — Seller Agents Technical Lead  
**Scope:** `backend/sellers/providers/scraping/` (`safety.py`, `transport.py`, `fetcher.py`)  
**Date:** 2026-10-17  
**Status:** COMPLETE — SECURITY-VERIFIED  

---

## 1. Executive Summary

The Scraping Seller (`scraping_001`) accepts user-specified URLs and extracts readable web content. This functionality represents a high-risk attack surface for Server-Side Request Forgery (SSRF), DNS Rebinding, and Time-of-Check to Time-of-Use (TOCTOU) race conditions.

This review audited the implementation of `safety.py`, `transport.py`, and `fetcher.py` to ensure that all outbound HTTP connections are strictly validated, connect-time pinned, and protected against socket hijacking or DNS oscillation.

---

## 2. In-Depth Technical Verification

### 2.1 URL Syntax and Scheme Validation
- **Allowed Schemes:** `http` and `https` strictly (`validate_url_syntax`). Any other scheme (e.g. `file://`, `ftp://`, `gopher://`) is rejected immediately.
- **Embedded Userinfo:** URLs with embedded credentials (e.g. `http://user:pass@host`) are strictly rejected.
- **Port Restrictions:** Only standard ports `80` and `443` are permitted.
- **Blocked Hostnames:** Blocks `localhost`, `127.0.0.1`, `::1`, `0.0.0.0`, `metadata.google.internal`, `metadata`, `instance-data`, and `.internal`/`.local` suffixes.
- **Numeric/Integer Encodings:** Validates and decodes integer representations (e.g. `2130706433` -> `127.0.0.1`) and hex notations.

### 2.2 IP Destination Safety (`validate_ip_address_safety`)
- **Blocked Special & Private Ranges:**
  - Loopback (`127.0.0.0/8`, `::1`)
  - RFC 1918 Private subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`)
  - Link-local (`169.254.0.0/16`, `fe80::/10`)
  - Cloud Metadata endpoints (`169.254.169.254`, `fd00:ec2::254`, `100.100.100.200`)
  - Carrier-Grade NAT (`100.64.0.0/10`)
  - IPv4-mapped IPv6 (`::ffff:127.0.0.1`)
  - Multicast, unspecified, and reserved addresses.

### 2.3 Mixed Public/Private DNS Answers
- `resolve_and_validate_destination()` resolves all A and AAAA records via `socket.getaddrinfo`.
- If an answer set contains a mixture of public and private IPs (e.g. `[93.184.216.34, 10.0.0.1]`), the entire resolution is rejected with `ProviderSSRFBlockedError`.

### 2.4 Connect-Time IP Pinning (`PinnedAsyncNetworkBackend`)
- **DNS Rebinding Defense:** The root cause of DNS rebinding is the HTTP client performing a second DNS query at socket connect time.
- `PinnedAsyncNetworkBackend` intercepts `connect_tcp` and replaces the destination address with the pre-validated pinned IP (`self._pinned_ip`).
- The OS socket connects directly to `self._pinned_ip`, completely bypassing subsequent DNS queries.

### 2.5 TLS SNI and Certificate Verification
- In `PinnedAsyncHTTPTransport`:
  - `ssl_context = create_ssl_context(verify=True, trust_env=False)`.
  - TLS certificate verification remains active (`check_hostname=True`, `verify_mode=CERT_REQUIRED`).
  - When `start_tls` is called, the original domain name is supplied as `server_hostname` for SNI and certificate common name/SAN validation.
  - A TLS certificate issued to an unauthorized host or IP will be rejected by OpenSSL.

### 2.6 Socket Peer-Address Verification
- At the OS socket level, `PinnedAsyncNetworkBackend.connect_tcp` checks `raw_stream.extra(anyio.abc.SocketAttribute.remote_address)`.
- If the connected peer IP does not match `self._pinned_ip`, the stream is closed immediately (`await stream.aclose()`) and `ProviderSSRFBlockedError` is raised.

### 2.7 Redirect Revalidation & Transport Isolation
- Redirects are manually followed in `fetcher.py` up to `scraping_max_redirects` (default 3).
- Automatic redirects in `httpx` are disabled.
- Each redirect destination is independently parsed, resolved, and validated.
- Each redirect hop creates a brand-new, isolated `PinnedAsyncHTTPTransport` with `max_keepalive_connections=0` to prevent connection reuse across origins.

### 2.8 Content & Resource Limits
- Max response body: 1 MB (1,000,000 bytes).
- Max extracted text: 50,000 characters.
- Timeout: 10.0 seconds.

---

## 3. Test Evidence

All scraping security tests pass:
- `test_url_syntax_and_scheme_restrictions`: PASS
- `test_ip_address_destination_safety`: PASS
- `test_destination_resolution_and_integer_ip_blocking`: PASS
- `test_safe_scraping_fetcher_redirect_to_private_target_blocked`: PASS
- `test_safe_scraping_content_extraction_and_prompt_injection_safety`: PASS
- `test_pinned_network_backend_routes_directly_to_ip`: PASS
- `test_pinned_network_backend_rejects_peer_mismatch`: PASS
- `test_pinned_network_backend_rejects_forbidden_pinned_ip`: PASS
- `test_dns_rebinding_simulation_prevented_by_pinning`: PASS
- `test_mixed_dns_answer_set_strictly_rejected`: PASS
- `test_pinned_transport_end_to_end_http_integration`: PASS
- `test_pinned_transport_https_sni_and_cert_verification`: PASS
- `test_pinned_network_backend_ipv6_peer_verification`: PASS
- `test_safe_scraping_fetcher_multi_hop_independent_pinning`: PASS
