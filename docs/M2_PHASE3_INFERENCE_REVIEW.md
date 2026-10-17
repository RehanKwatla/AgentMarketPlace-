# M2 Phase 3: Gemini & Groq Inference Provider Review

**Reviewer:** Member 2 — Seller Agents Technical Lead  
**Scope:** `backend/sellers/providers/inference/` (`configured_provider.py`, `fake.py`), `backend/sellers/providers/config.py`, and `backend/sellers/inference_seller.py`  
**Date:** 2026-10-17  
**Status:** COMPLETE — PROVIDER-VERIFIED (MOCKED) / LIVE PENDING AUTHORIZATION  

---

## 1. Executive Summary

The Inference Seller (`inference_001`) supports LLM inference synthesis across Google Gemini, Groq Cloud, and a deterministic offline Fake provider.

This review audited the implementation against the 13 required verification criteria in Stage 3, ensuring complete isolation of credentials, robust normalization of upstream errors, strict timeout enforcement, and zero silent fallback from Live to Fake mode.

---

## 2. Verification Checklist (13 Invariants)

| # | Invariant | Implementation Status | Evidence / Verification |
|---|-----------|-----------------------|--------------------------|
| 1 | Provider selection matches configuration | VERIFIED | `settings.inference_provider` switches cleanly between `gemini`, `groq`, and `openai_compatible`. |
| 2 | Missing live credentials fail closed | VERIFIED | Missing `GEMINI_API_KEY` or `GROQ_API_KEY` in live mode raises `ProviderConfigurationError`. |
| 3 | Live mode never silently falls back to fake | VERIFIED | `generate()` branches to `_fake` ONLY if `settings.mode == ProviderMode.FAKE`. Live mode failure raises exception without fallback. |
| 4 | API keys supplied via environment | VERIFIED | Loaded strictly via `pydantic_settings.BaseSettings` (`backend/sellers/providers/config.py`). |
| 5 | Keys not logged or in URLs | VERIFIED | Gemini uses `x-goog-api-key` header; Groq uses `Authorization: Bearer` header. No query parameters. |
| 6 | Provider errors are sanitized | VERIFIED | Exception handlers strip URLs and raw error dumps, ensuring keys are never leaked in error messages. |
| 7 | Timeouts enforced | VERIFIED | Configured with `httpx.Timeout(inference_timeout_seconds, connect=5.0)`. |
| 8 | HTTP 429 handled consistently | VERIFIED | Normalized to `ProviderRateLimitError` extracting `Retry-After` header. |
| 9 | Upstream errors normalized | VERIFIED | HTTP 5xx mapped to `ProviderUpstreamError` (status code 502/503). |
| 10 | Malformed & empty responses rejected | VERIFIED | Non-JSON, missing candidates/choices, or empty string content raises `ProviderResponseInvalidError`. |
| 11 | Input and output limits enforced | VERIFIED | Input prompt clamped to 20,000 chars; output tokens clamped to `min(max_tokens, 2000)`; content clamped to 50,000 chars. |
| 12 | Token usage metrics not fabricated | VERIFIED | Populated from upstream `usageMetadata.candidatesTokenCount` or `usage.completion_tokens`. |
| 13 | Configured model names correspond to requests | VERIFIED | Defaults to `gemini-2.5-flash` for Gemini and `llama-3.3-70b-versatile` for Groq. |

---

## 3. Operational Modes & Testing Boundaries

- **Fake Mode (`ProviderMode.FAKE`):**
  - Fully deterministic synthesis returning structured analysis based on prompt keywords.
  - Used for local unit tests and automated CI test runs without external network dependencies.
- **Live Mode (`ProviderMode.LIVE`):**
  - Verified with comprehensive mock HTTP responses (`httpx.MockTransport`) testing 200 OK, 429 Rate Limit, 500 Server Error, 503 Unavailable, and malformed JSON payloads.
  - Live API testing against production endpoints (Google AI Studio / Groq Cloud) requires explicit user authorization and provision of live environment secrets.
  - No paid API calls were made during this audit.
