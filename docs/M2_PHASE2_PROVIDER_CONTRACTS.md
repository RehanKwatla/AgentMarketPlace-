# M2 Phase 2: External Provider Contracts & Adapter Architecture

**Role:** Member 2 — Seller Agents Technical Lead  
**Repository:** `C:\AgentMarket`  
**Status:** IMPLEMENTED & VERIFIED  

---

## 1. Architectural Overview

To ensure high reliability, payment safety, and offline testability, the Seller microservices separate core seller lifecycle logic (`BaseSellerService`) from external upstream provider implementations.

```
                      +-----------------------------+
                      |     FastAPI Route Handler   |
                      |  (x402 Verification Gate)   |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |      BaseSellerService      |
                      |  - Input pre-validation     |
                      |  - Concurrency bounding     |
                      |  - Execution timeout        |
                      |  - Output post-validation   |
                      |  - Telemetry & metrics      |
                      +--------------+--------------+
                                     |
                                     v
                     +-------------------------------+
                     |     Provider Interface (ABC)  |
                     +---------------+---------------+
                                     |
                     +---------------+---------------+
                     |                               |
                     v                               v
         +-----------------------+       +-----------------------+
         |     Fake Provider     |       |  Configured Provider  |
         | (Offline/Deterministic)       |  (Live Network/API)   |
         +-----------------------+       +-----------------------+
```

---

## 2. Provider Modes & Selection

The system supports two explicit operational modes configured via `SELLER_PROVIDER_MODE`:

1. **`FAKE` (Default / CI / Offline Demo):**
   - Deterministic, offline execution.
   - Zero external network requests made during test runs.
   - Fixed baseline data aligned with existing system integration expectations.

2. **`LIVE` (Production / Staging / Live Demo):**
   - Explicitly configured external endpoints and credentials.
   - Never silently falls back to fake data upon failure.
   - If required credentials or URLs are missing, the system **fails safely and immediately** with `ProviderConfigurationError` (HTTP 503).

---

## 3. Provider Interfaces & Contracts

### 3.1 Data Provider Contract
- **Interface:** `DataProviderInterface`
- **Method:** `async def get_data(self, ticker: str) -> Dict[str, Any]`
- **Required Output Keys:** `symbol: str`, `price: float`, `volume_24h: float`, `timestamp: str`
- **Implementations:**
  - `FakeDataProvider`: Deterministic pricing for BTC ($67,500), ETH ($2,650.50), USDC ($1.00), and synthetic hash-based pricing for arbitrary tickers.
  - `ConfiguredDataProvider`: Upstream HTTP market data client with query validation, numeric validation, and error normalization.

### 3.2 Scraping Provider Contract
- **Interface:** `ScrapingProviderInterface`
- **Method:** `async def scrape_url(self, url: str) -> Dict[str, Any]`
- **Required Output Keys:** `url: str`, `title: str`, `content: str`, `content_length: int`, `word_count: int`
- **Implementations:**
  - `FakeScrapingProvider`: Offline deterministic extractor with syntax and local destination verification.
  - `SafeScrapingFetcher`: Full connect-time SSRF-defended HTTP client:
    - Manual redirect following with re-validation at every hop.
    - IP resolution and destination checking against IPv4/IPv6 loopback, private ranges, metadata IPs, and carrier-grade NAT.
    - Streaming response size bounding (max 1 MB).
    - HTML extraction stripping `<script>`, `<style>`, and SVG tags.
    - Neutral text processing treating prompt-injection strings as inert body text.

### 3.3 Inference Provider Contract
- **Interface:** `InferenceProviderInterface`
- **Method:** `async def generate(self, prompt: str, max_tokens: int, temperature: float) -> Dict[str, Any]`
- **Required Output Keys:** `response: str`, `model_used: str`, `tokens_generated: int`
- **Implementations:**
  - `FakeInferenceProvider`: Offline deterministic reasoner with prompt bounding and token metrics.
  - `ConfiguredInferenceProvider`: Upstream OpenAI/Groq compatible chat completions adapter with credential sanitization and strict token boundaries.

---

## 4. Normalized Error Hierarchy

All provider adapters normalize vendor-specific exceptions into a unified hierarchy under `ProviderBaseError`:

| Exception Class | HTTP Status | Retryable | Description |
| :--- | :---: | :---: | :--- |
| `ProviderConfigurationError` | 503 | No | Required environment variable or credential missing in LIVE mode. |
| `ProviderRequestRejectedError` | 400 | No | Upstream rejected request due to client error or redirect limit exceeded. |
| `ProviderTimeoutError` | 504 | Yes | Upstream connection or read timeout exceeded. |
| `ProviderRateLimitError` | 429 | Yes | Upstream HTTP 429 received; captures `retry_after_seconds` if provided. |
| `ProviderUpstreamError` | 502 | Yes | Upstream HTTP 5xx outage or connection reset. |
| `ProviderResponseInvalidError` | 502 | No | Upstream returned non-JSON, missing fields, or malformed data. |
| `ProviderOutputLimitExceededError` | 502 | No | Output exceeded memory or character limits. |
| `ProviderSSRFBlockedError` | 400 | No | Destination resolution or redirect target violated SSRF policy. |

---

## 5. Security & Sanitization Guarantees

1. **Zero Secret Leakage:** Error messages emitted from providers strictly omit API keys, tokens, authorization headers, and database connection strings.
2. **Fail-Closed Execution:** An unverified payment never reaches the provider adapter ($\text{Unverified Payment} \implies \text{Provider Invocations} = 0$).
3. **Bounded Concurrency:** Concurrency per seller service is governed by an `asyncio.Semaphore` (default 50) to prevent thread/socket exhaustion under peak loads.
