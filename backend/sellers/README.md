# MEMBER 2: SELLER AGENTS (`backend/sellers/`)

**Assigned Owner:** Member 2 (Seller Agents Engineer)  
**Assigned Git Branch:** `feature/sellers`  
**Status:** `[DEFINED INTERFACES & STUBS AWAITING IMPLEMENTATION]`

---

## 📋 Responsibilities Checklist

- [ ] **Data Seller (`data_seller.py`):**
  - Input: `{ "symbol": str }`
  - Output: `{ "symbol": str, "price": float, "volume_24h": float, "timestamp": str }`
  - Fetch live or high-fidelity cached financial data.
- [ ] **Scraping Seller (`scraping_seller.py`):**
  - Input: `{ "url": HttpUrl }`
  - Output: `{ "url": str, "content": str, "word_count": int, "title": str }`
  - Safe HTML fetching, boilerplate stripping, and clean markdown generation.
- [ ] **Inference Seller (`inference_seller.py`):**
  - Input: `{ "prompt": str, "max_tokens": int }`
  - Output: `{ "response": str, "model_used": str, "tokens_generated": int }`
  - LLM integration (Groq / OpenAI / Ollama / local model fallback).
- [ ] **x402 Protocol Integration on Endpoints (`routes.py`):**
  - Check incoming requests for `X-402-Payment-Payload` and `Idempotency-Key`.
  - If header is absent or invalid, emit `HTTP 402 Payment Required` with `X-402-Requirement` header.
  - If header is present, verify payment with Facilitator via Member 1 verifier interface.
  - Settle payment, execute seller logic, and return `HTTP 200 OK` with `X-402-Settlement-Proof`.
- [ ] **Output Schema Strictness:** Ensure all outputs conform 100% to registered schemas in `backend/sellers/schemas.py`.
- [ ] **Seller Tests (`backend/tests/test_sellers.py`):**
  - Test 402 challenge issuance.
  - Test input schema validation rejection (422).
  - Test output schema conformance.
