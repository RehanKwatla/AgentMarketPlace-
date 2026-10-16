# M2 Phase 3 Stage 4: Seller Capability Metadata & Orchestration Contract Proposal

**Author:** Member 2 — Seller Agents Technical Lead  
**Target Stakeholders:** Setup Lead, Member 3 (Buyer / Registry), Member 1 (Payments), Member 4 (Ledger)  
**Date:** 2026-10-17  
**Stage:** Stage 4 / Stage 5 (Orchestration & Capability Review)  
**Status:** PROPOSAL — PENDING CROSS-TEAM APPROVAL  

---

## 1. Executive Summary

As the Agentica platform expands in Phase 3 to support multi-step task decomposition and autonomous execution chaining, the Buyer Agent (`backend/buyer/`) requires structured capability metadata to discover, evaluate, price, and invoke seller microservices without hardcoded heuristics.

This proposal specifies:
1. A **Seller Capability Metadata Model** that cleanly distinguishes actual capabilities, configured capabilities, measured vs estimated performance, hard execution limits, protocol declarations, and error categories.
2. A **Multi-Step Execution Chaining Protocol** enforcing 10 non-negotiable safety and payment integrity invariants.

> [!IMPORTANT]
> This document is a proposal originating from Member 2. In strict accordance with module boundary rules, Member 2 will NOT modify `backend/registry/`, `backend/buyer/`, `backend/payments/`, or `backend/shared/` without explicit coordination and cross-team approval.

---

## 2. Proposed Seller Capability Metadata Schema

We propose augmenting the shared `ServiceDefinition` model with an optional `capability_metadata` dictionary or sub-model:

```json
{
  "service_id": "inference_001",
  "category": "inference",
  "version": "2.0.0",
  "protocol_version": "x402:v2.0",
  "supported_tasks": [
    "summarization",
    "market_synthesis",
    "sentiment_analysis",
    "reasoning"
  ],
  "actual_capabilities": {
    "supported_input_formats": ["text/plain", "application/json"],
    "supported_output_formats": ["application/json"],
    "supported_providers": ["gemini", "groq", "fake"]
  },
  "configured_capabilities": {
    "active_provider": "gemini",
    "model": "gemini-2.5-flash",
    "mode": "live"
  },
  "hard_execution_limits": {
    "timeout_seconds": 15.0,
    "concurrency_limit": 50,
    "max_input_length_chars": 20000,
    "max_output_tokens": 2000,
    "max_response_length_chars": 50000
  },
  "performance_profile": {
    "measurement_status": "synthetic_benchmark_baseline",
    "notes": "Figures represent controlled local test baselines, NOT production SLA guarantees.",
    "benchmark_latency_ms": {
      "fake_mode_p50": 15,
      "fake_mode_p99": 45,
      "live_mode_p50_estimate": 650,
      "live_mode_p99_estimate": 1400
    }
  },
  "error_categories": [
    "SELLER_INPUT_INVALID",
    "SELLER_TIMEOUT",
    "SELLER_OUTPUT_INVALID",
    "SELLER_EXECUTION_FAILED",
    "PAYMENT_AUTHORIZATION_FAILED",
    "PAYMENT_PAYLOAD_INVALID",
    "PAYMENT_VERIFIER_UNAVAILABLE"
  ]
}
```

### Distinction of Taxonomy:
- **Actual Capabilities:** Validated operations supported by the underlying Python service codebase (e.g., input schemas, task handlers).
- **Configured Capabilities:** Active provider, model, and mode derived from environment variables (`ProviderSettings`).
- **Hard Execution Limits:** Strict boundaries enforced in code (Pydantic field lengths, `asyncio.wait_for`, semaphore limits). Never assume infinite context windows.
- **Performance Profile:** Explicitly labeled as `synthetic_benchmark_baseline` or `estimated` to prevent misrepresenting unverified latency figures as live production measurements.
- **Protocol Declarations:** Wire-level headers supported (`PAYMENT-REQUIRED`, `PAYMENT-SIGNATURE`, `X-PAYMENT`, `X-402-Requirement`, etc.).
- **Error Categories:** Enumerated error codes returned in JSON error bodies.

---

## 3. Capability Profiles by Service

### A. Data Seller (`data_001`)
- **Category:** `data`
- **Supported Tasks:** `ticker_price`, `crypto_spot`, `volume_24h`
- **Supported Symbols:** `ETH`, `BTC`, `SOL`, `USDC`, and arbitrary alphanumeric uppercase tickers.
- **Configured Providers:** `fake` (deterministic financial market feed) or `configured` (upstream API).
- **Hard Execution Limits:**
  - Timeout: 5.0 seconds.
  - Concurrency: 50 concurrent requests.
- **Performance Profile:** Synthetic test baseline p50 ~2ms, p99 ~15ms (fake mode).
- **Price:** `0.002 USDC` (2,000 base units).

### B. Scraping Seller (`scraping_001`)
- **Category:** `scraping`
- **Supported Tasks:** `web_markdown_extraction`, `html_text_parsing`
- **Hard Execution Limits & Security Constraints:**
  - Allowed Schemes: `http`, `https` strictly.
  - Allowed Ports: `80`, `443` strictly.
  - Max Response Body Size: 1,000,000 bytes (1 MB).
  - Max Extracted Text Length: 50,000 characters.
  - Max Redirects: 3 hops (each independently DNS-validated and IP-pinned).
  - Pinned Transport: OS socket connects directly to validated IP, preventing DNS rebinding.
  - Timeout: 10.0 seconds.
  - Concurrency: 20 concurrent requests.
- **Performance Profile:** Synthetic test baseline p50 ~15ms, p99 ~80ms (local/pinned tests).
- **Price:** `0.003 USDC` (3,000 base units).

### C. Inference Seller (`inference_001`)
- **Category:** `inference`
- **Supported Tasks:** `summarization`, `synthesis`, `reasoning`, `analysis`
- **Supported Providers:** Google Gemini (`gemini-2.5-flash`), Groq Cloud (`llama-3.3-70b-versatile`), Fake.
- **Hard Execution Limits:**
  - Max input prompt length: 20,000 characters (enforced in schema).
  - Max output tokens: 2,000 tokens (enforced in request body and clamped).
  - Max response length: 50,000 characters.
  - Timeout: 15.0 seconds.
  - Concurrency: 10 concurrent requests.
- **Performance Profile:** Synthetic test baseline ~20ms (fake mode); ~500ms–1500ms (estimated live network round-trip).
- **Price:** `0.004 USDC` (4,000 base units).

---

## 4. Multi-Step Orchestration Safety & Payment Invariants

When the Buyer Agent decomposes a composite user request into a multi-step chain (e.g. `ScrapingSeller` -> `InferenceSeller`):

1. **Schema Validation at Every Step:**
   Every step's input and output must be validated against its declared Pydantic schema before data flows to the next step.
2. **Immediate Abort on Upstream Failure:**
   If Step N fails (e.g. SSRF block, timeout, or output corruption), downstream execution MUST abort immediately. No downstream steps may be invoked.
3. **Atomic Pre-Step Budget Reservation:**
   Before invoking each paid step, the Buyer Agent must check and lock the required budget via Member 1's `BudgetManager`. No call may proceed without locked funds.
4. **No Unauthorized Extra Paid Calls:**
   Orchestrators must never make unapproved additional paid calls or speculative parallel calls that consume user funds without authorization.
5. **Zero Fabricated Settlement Proofs:**
   If a step fails or is skipped, no transaction hash, receipt ID, or mock settlement proof may ever be recorded for that step.
6. **Separation of Payment Status and Output Delivery Status:**
   If payment settles successfully on-chain or via facilitator, but the seller service subsequently times out or fails schema validation, the system must clearly record:
   - `payment_status: SETTLED`
   - `delivery_status: FAILED`
   These statuses must never be collapsed into `PAYMENT_FAILED` or `SUCCESS`.
7. **Reputation as Registry/Ledger Data:**
   Reputation scores and provider selection weights belong strictly to Member 3's Registry and Member 4's Ledger. Sellers must never self-report or manipulate reputation scores.
8. **Explicit Retry and Idempotency Rules:**
   - Retries must reuse the same `idempotency_key` and nonce.
   - Retrying a paid call with a new nonce without checking whether prior settlement succeeded is strictly forbidden to prevent double-charging.
9. **Identification of Partial Task Failure:**
   When a chain fails, the orchestrator must return `task_status: PARTIAL_FAILURE`, explicitly reporting which step failed, which succeeded, and the exact error code.
10. **Non-Atomicity Across Independent Paid Steps:**
    Orchestrators must NOT claim or simulate atomic rollbacks across independent on-chain/facilitator payments. Each paid call is an irrevocable financial settlement.

---

## 5. Cross-Team Handoff & Approval Status

- **Seller Readiness:** Member 2's seller services implement all schemas, error codes, and limits defined above.
- **Cross-Team Approval Status:** `PENDING CROSS-TEAM APPROVAL`.
- **Target Owners:**
  - Setup Lead: Merge capability metadata fields into shared schemas if approved.
  - Member 3: Implement buyer orchestration pipeline following Section 4 invariants.
  - Member 1: Verify budget locking and idempotency alignment.
