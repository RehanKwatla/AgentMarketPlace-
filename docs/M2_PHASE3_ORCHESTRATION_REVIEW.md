# M2 Phase 3: Capability Metadata & Orchestration Proposal Review

**Reviewer:** Member 2 — Seller Agents Technical Lead  
**Scope:** `docs/M2_PHASE3_ORCHESTRATION_CONTRACT_PROPOSAL.md`  
**Date:** 2026-10-17  
**Status:** COMPLETE — PENDING CROSS-TEAM APPROVAL  

---

## 1. Executive Summary

This review audited the capability metadata proposal for seller discovery and the multi-step execution chaining invariants required for autonomous buyer orchestration.

---

## 2. Taxonomy Review & Corrections Applied

The capability metadata proposal was corrected to strictly enforce clear semantic distinctions:

1. **Actual Capabilities vs Configured Capabilities:**
   - Actual: Explicitly lists supported schema formats and supported provider adapters (`gemini`, `groq`, `fake`).
   - Configured: Derived dynamically from active environment settings (`ProviderSettings`).
2. **Estimates vs Measured Performance:**
   - Removed unverified latency assumptions.
   - Explicitly categorized benchmark numbers as `synthetic_benchmark_baseline` (local test fixtures), warning that they do not constitute production SLAs.
3. **Hard Execution Limits:**
   - Removed the unverified assumption of a 1,000,000 token context window.
   - Specified hard limits enforced by code: `max_input_length_chars: 20000`, `max_output_tokens: 2000`, and `timeout_seconds`.
4. **Protocol Declarations:**
   - Standardized wire headers for both official x402 v2 (`PAYMENT-REQUIRED`, `PAYMENT-SIGNATURE`, `PAYMENT-RESPONSE`) and legacy compatibility (`X-402-Requirement`, `X-402-Settlement-Proof`).
5. **Error Categories:**
   - Enumerated normalized error codes (`SELLER_INPUT_INVALID`, `SELLER_TIMEOUT`, `SELLER_OUTPUT_INVALID`, `SELLER_EXECUTION_FAILED`, `PAYMENT_AUTHORIZATION_FAILED`, `PAYMENT_PAYLOAD_INVALID`, `PAYMENT_VERIFIER_UNAVAILABLE`).

---

## 3. Multi-Step Orchestration Invariant Audit

The proposal confirms and mandates all 10 non-negotiable orchestration invariants:

1. **Step Validation:** Input and output schemas must be validated at every step before data handoff.
2. **Immediate Abort on Upstream Failure:** Downstream steps are never executed if an upstream step fails.
3. **Pre-Step Budget Reservation:** Budget is checked and locked via `BudgetManager` prior to each paid step.
4. **No Unauthorized Extra Paid Calls:** No speculative or parallel paid calls without explicit authorization.
5. **Zero Fabricated Settlement Records:** No mock hashes or fake receipts recorded for skipped/failed steps.
6. **Separation of Payment vs Delivery Status:** `payment_status: SETTLED` is preserved separately from `delivery_status: FAILED` when execution crashes after confirmed payment.
7. **Reputation as Registry/Ledger Data:** Reputation metrics are owned by Member 3 (Registry) and Member 4 (Ledger); sellers never self-report reputation.
8. **Explicit Retry & Idempotency Rules:** Retries must reuse the same idempotency key and nonce; uncoordinated retries with new nonces are prohibited to prevent double-charging.
9. **Identification of Partial Failure:** Chained tasks must report `PARTIAL_FAILURE` specifying the exact failing step.
10. **Non-Atomicity Across Independent Steps:** Orchestrators must not assume or claim atomic rollbacks across independent payments.

---

## 4. Ownership Boundaries & Approval Status

- **Status:** `PENDING CROSS-TEAM APPROVAL`.
- Member 2 has made NO unilateral changes to `backend/registry/`, `backend/buyer/`, `backend/payments/`, or `backend/shared/`.
- Ready for review by Setup Lead, Member 3, and Member 1.
