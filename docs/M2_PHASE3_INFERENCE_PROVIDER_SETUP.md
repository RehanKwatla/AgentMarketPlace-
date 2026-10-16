# M2 Phase 3 Stage 2: Inference Provider Setup (Gemini & Groq)

**Author:** Member 2 — Seller Agents Technical Lead  
**Repository:** `C:\AgentMarket`  
**Date:** 2026-10-17  
**Stage:** Stage 2 (Inference Provider Setup)  

---

## 1. Objective

Document the implementation, configuration, error normalization, and testing of Google Gemini and Groq Cloud inference providers within `backend/sellers/providers/inference/`.

---

## 2. Configuration & Provider Architecture

### A. Environment Configuration Parameters
All inference provider settings are managed via `ProviderSettings` in `backend/sellers/providers/config.py`:

```ini
# Provider Mode: "fake" (default, zero cost) or "live"
SELLER_PROVIDER_MODE=fake

# Active Inference Provider: "gemini" or "groq"
INFERENCE_PROVIDER=gemini

# Google Gemini Settings (Used when INFERENCE_PROVIDER=gemini)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

# Groq Cloud Settings (Used when INFERENCE_PROVIDER=groq)
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile

# Execution Bounds
INFERENCE_TIMEOUT_SECONDS=15.0
INFERENCE_MAX_TOKENS=2000
```

### B. Mode Boundaries & Safe Execution
1. **`FAKE` Mode (Default):**
   - Uses `FakeInferenceProvider`.
   - Generates deterministic, structured analytical synthesis responses.
   - Requires zero external API credentials or network access.
2. **`LIVE` Mode:**
   - Routes strictly to the selected `INFERENCE_PROVIDER` (`gemini` or `groq`).
   - If the selected provider credentials (`GEMINI_API_KEY` or `GROQ_API_KEY`) are missing, fails closed immediately with `ProviderConfigurationError` (HTTP 503).
   - **Zero Silent Fallback:** Live mode never silently falls back to synthetic data or switches to another provider without explicit configuration.

---

## 3. Protocol Adapters

### A. Google Gemini Adapter (`_generate_gemini`)
- Endpoint: `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`
- Authentication: Header-based `x-goog-api-key: <key>`
- Payload: `{"contents": [{"role": "user", "parts": [{"text": prompt}]}], "generationConfig": {"maxOutputTokens": ..., "temperature": ...}}`
- Response Normalization: Extracts candidate text, maps usage metadata to token metrics, bounds output length to 50,000 characters.

### B. Groq Cloud Adapter (`_generate_groq`)
- Endpoint: `https://api.groq.com/openai/v1/chat/completions`
- Authentication: Header-based `Authorization: Bearer <key>`
- Format: OpenAI-compatible chat completion payload with system prompt and user query.
- Response Normalization: Extracts choice content, maps token usage, bounds response length.

---

## 4. Error Normalization Matrix

| HTTP Status / Condition | Provider Error Raised | Seller Exception Mapped | HTTP Status Returned |
|---|---|---|---|
| HTTP 429 Rate Limit | `ProviderRateLimitError` | `SellerExecutionError` | `500 Internal Server Error` |
| HTTP 500 / 502 / 503 | `ProviderUpstreamError` | `SellerExecutionError` | `500 Internal Server Error` |
| Connect / Read Timeout | `ProviderTimeoutError` | `SellerExecutionTimeoutError` | `504 Gateway Timeout` |
| Non-JSON / Empty Text | `ProviderResponseInvalidError` | `SellerExecutionError` | `500 Internal Server Error` |
| Missing API Credentials | `ProviderConfigurationError` | `SellerExecutionError` | `500 Internal Server Error` |

---

## 5. Security & Secrets Protection

1. **Header-Based Authentication:** Neither Gemini nor Groq API keys are ever passed as query parameters in URLs.
2. **Exception Sanitization:** Normalized exceptions and log handlers do not print or interpolate raw API keys.
3. **Repository Cleanliness:** No API keys are committed to Git or stored in test fixtures.

---

## 6. Stage 2 Exit Criteria

- [x] Gemini and Groq providers verified in `ConfiguredInferenceProvider`.
- [x] Missing keys fail closed with `ProviderConfigurationError`.
- [x] Error normalization tested for 429, 500, timeout, and malformed responses.
- [x] Zero silent fallback from live to fake.
- [x] All 28 provider tests pass.
