# M2 INFERENCE ENVIRONMENT & PROVIDER SETUP REPORT

**Project:** DI-06 AGENTICA (Pay-Per-Call Agent Economy)  
**Role:** Member 2 — Seller Agents Technical Lead  
**Branch:** `M2`  
**Subsystem:** `backend/sellers/providers/inference/`  
**Date of Audit & Setup:** 2026-10-17  
**Status:** **`CONFIGURED AND VERIFIED`**

---

## 1. Executive Summary

This report documents the environment configuration and provider architecture enhancements for the Inference Seller service. The configuration supports both **Google Gemini** and **Groq Cloud** LLM backends in addition to deterministic offline execution, adhering strictly to the project's zero-secret-leakage security rules and module boundaries.

Key outcomes:
1. **Google Gemini Support:** Implemented native Gemini REST adapter in `ConfiguredInferenceProvider` utilizing header-based authentication (`x-goog-api-key`) and structured content generation (`contents`/`generationConfig`).
2. **Groq Cloud Support:** Implemented dedicated Groq adapter targeting `https://api.groq.com/openai/v1/chat/completions` with bearer token authentication.
3. **Explicit Provider Selection:** Added `INFERENCE_PROVIDER` setting (`gemini` or `groq`) ensuring no silent provider switching.
4. **Environment Isolation:** Verified that `.env` is ignored by Git, `.env.example` contains only documented placeholders, and no API keys are logged or committed.
5. **Quality Assurance:** Full project test suite passes **109 of 109 tests (100%)** with zero regressions.

---

## 2. Environment Variables Specification

The seller subsystem supports the following environment variables:

| Variable Name | Default | Required in FAKE | Required in LIVE Gemini | Required in LIVE Groq | Purpose |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `SELLER_PROVIDER_MODE` | `fake` | **No** | **Yes** (`live`) | **Yes** (`live`) | Master switch: `fake` (offline synthetic) or `live` (outbound API calls). |
| `INFERENCE_PROVIDER` | `gemini` | **No** | **Yes** (`gemini`) | **Yes** (`groq`) | Explicit LLM backend selection: `gemini` or `groq`. |
| `GEMINI_API_KEY` | `None` | **No** | **Yes** | **No** | Google AI Studio API key for Gemini inference. |
| `GEMINI_MODEL` | `gemini-2.5-flash` | **No** | **No** (has default) | **No** | Gemini model identifier (e.g. `gemini-2.5-flash`, `gemini-1.5-flash`). |
| `GROQ_API_KEY` | `None` | **No** | **No** | **Yes** | Groq Cloud API key. |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | **No** | **No** | **No** (has default) | Groq model identifier (e.g. `llama-3.3-70b-versatile`). |
| `INFERENCE_TIMEOUT_SECONDS` | `15.0` | **No** | **No** (has default) | **No** (has default) | Maximum timeout for upstream inference HTTP requests. |
| `INFERENCE_PROVIDER_URL` | `None` | **No** | **No** (optional override)| **No** (optional override)| Custom REST URL override (for proxies or custom enterprise gateways). |
| `DATA_PROVIDER_URL` | `None` | **No** | **Yes** (Data Seller) | **Yes** (Data Seller) | Financial market data REST upstream (for Data Seller in LIVE mode). |
| `DATA_PROVIDER_API_KEY` | `None` | **No** | **No** | **No** | Optional API key for Data Seller REST upstream. |

---

## 3. Provider Architecture & Selection Mechanics

### 3.1 Provider Selection Routing
In `backend/sellers/providers/inference/configured_provider.py`:
- **FAKE Mode (`SELLER_PROVIDER_MODE=fake`):**
  - Routes to `FakeInferenceProvider`.
  - Zero API keys are required.
  - Returns deterministic synthetic responses with simulated token usage.
- **LIVE Mode (`SELLER_PROVIDER_MODE=live`):**
  - Evaluates `INFERENCE_PROVIDER`:
    - If `gemini`: Routes to `_generate_gemini()`. Requires non-empty `GEMINI_API_KEY`. If missing, raises `ProviderConfigurationError` (HTTP 503).
    - If `groq`: Routes to `_generate_groq()`. Requires non-empty `GROQ_API_KEY`. If missing, raises `ProviderConfigurationError` (HTTP 503).
    - If `openai` (backward compatibility): Routes to `_generate_openai_compatible()`.

### 3.2 Fallback Policy
- **No Silent Fallback to FAKE:**
  If `SELLER_PROVIDER_MODE=live` is configured, the system **never** silently falls back to synthetic fake data. If an upstream service or key is unavailable, it fails closed with a sanitized `ProviderConfigurationError` or `ProviderUpstreamError`.
- **No Unintended Live Cross-Provider Fallback:**
  When `INFERENCE_PROVIDER=gemini` is selected, requests are directed exclusively to Gemini. If Gemini experiences an outage, it raises `ProviderUpstreamError` (HTTP 502) to notify the caller rather than silently billing a secondary provider.

---

## 4. Confirmed Model Identifiers

The configured defaults reflect currently active production models:

| Provider | Confirmed Default Model | Alternative Supported Models |
| :--- | :--- | :--- |
| **Google Gemini** | `gemini-2.5-flash` | `gemini-1.5-flash`, `gemini-1.5-pro` |
| **Groq Cloud** | `llama-3.3-70b-versatile` | `llama-3.1-8b-instant`, `mixtral-8x7b-32768` |

Models can be customized without code changes by setting `GEMINI_MODEL` or `GROQ_MODEL` in `.env`.

---

## 5. Security & Configuration Audit

1. **.env Loading Location:**
   - Primary location: `C:\AgentMarket\.env`.
   - Loaded at application startup via `python-dotenv` in `backend/sellers/providers/config.py` and `backend/shared/config.py`.
2. **.gitignore Verification:**
   - `.gitignore` explicitly ignores `.env` and all `.env.*` files except `!.env.example`.
   - Verified via `git status --short`: `.env` is completely untracked and excluded from version control.
3. **Secret Scrubbing & Sanitization:**
   - Header-based authentication is used:
     - Gemini: `x-goog-api-key: <key>` header (prevents key exposure in HTTP access logs or URL parameters).
     - Groq: `Authorization: Bearer <key>` header.
   - All exception handlers map upstream network/status errors without interpolating raw request headers or credentials into error messages.
   - Zero hardcoded keys exist in source files, test fixtures, or documentation.

---

## 6. Test Execution & Coverage

All tests were executed offline using mocked `httpx.MockTransport` fixtures to guarantee determinism and avoid live API charges:

```powershell
# 1. Provider & Security Test Suite (including Gemini & Groq unit tests)
python -m pytest backend/tests/test_sellers_providers.py -v
# Output: 24 passed in 1.35s (Exit code: 0)

# 2. Seller Foundation & Payment Integration Test Suite
python -m pytest backend/tests/test_sellers_payment_integration.py backend/tests/test_sellers.py backend/tests/test_sellers_foundation.py -v
# Output: 58 passed in 0.66s (Exit code: 0)

# 3. Full Project Test Suite
python scripts/run_tests.py
# Output: 109 passed in 2.12s (Exit code: 0)
# [SUCCESS] ALL TESTS PASSED SUCCESSFULLY!

# 4. Git Diff Hygiene Check
git diff --check
# Output: Exit code 0 (No whitespace errors)
```

### Verified Test Assertions:
1. `test_gemini_inference_provider_mocked`: Verified Gemini payload format, `x-goog-api-key` header, candidate parsing, token tracking, and 200 OK output schema validation.
2. `test_groq_inference_provider_mocked`: Verified Groq OpenAI-compatible payload format, Bearer authorization, choices parsing, token tracking, and output schema validation.
3. `test_inference_provider_missing_keys_fail_closed`: Verified that missing `GEMINI_API_KEY` in Gemini mode or missing `GROQ_API_KEY` in Groq mode raises `ProviderConfigurationError` (HTTP 503) without leaking secrets.
4. `test_provider_settings_defaults`: Verified default values and enum types.
5. `test_all_seller_routes_fail_closed_without_verifier`: Verified existing x402 payment gate remains strictly enforced.

---

## 7. Configuration Instructions for the Developer / User

To enable LIVE inference for local development:
1. Open your local `.env` file at `C:\AgentMarket\.env`.
2. Set `SELLER_PROVIDER_MODE=live`.
3. Choose your provider:
   - For Gemini: Set `INFERENCE_PROVIDER=gemini` and enter your newly rotated API key in `GEMINI_API_KEY=<your-key>`.
   - For Groq: Set `INFERENCE_PROVIDER=groq` and enter your newly rotated API key in `GROQ_API_KEY=<your-key>`.
4. Save `.env`.
5. For automated test runs, keep `SELLER_PROVIDER_MODE=fake` (default) to ensure 100% offline test execution without consuming API quota.

---

## 8. Final Safety Checklist

- [x] Active branch remains `M2`.
- [x] Zero API keys or secrets were printed, logged, or committed.
- [x] `.env` is verified untracked and ignored by Git.
- [x] `.env.example` contains placeholders only.
- [x] Zero changes made to `backend/payments/`, `backend/buyer/`, `backend/registry/`, `backend/ledger/`, or `backend/shared/`.
- [x] Zero live paid API calls were made during testing.
- [x] Zero files staged (`git add`), committed, pushed, or reset.
