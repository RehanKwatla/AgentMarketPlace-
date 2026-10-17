# AGENTICA — PHASE 7 RECONCILIATION, STATE MACHINE, AND BUDGET AUDIT

**Project:** DI-06 — AGENTICA: Pay-per-Call Agent Economy  
**Tagline:** Discover. Pay. Execute. Trust.  
**Phase:** 7 (Stage 2 — Reconciliation and Budget State Machine Audit)  
**Date:** 2026-10-17  
**Module Owner:** Member 1 (`backend/payments/`), Member 3 (`backend/buyer/`), Member 4 (`backend/ledger/`)  
**Evidence Classification:** `VERIFIED BY AUTOMATED TESTS` & `VERIFIED BY CODE INSPECTION`  

---

## 1. Executive Summary

This audit establishes the formal mathematical and transactional invariants governing payment state transitions, budget reservation/commitment, reconciliation, and ledger insertion.

The primary financial invariants verified across 24 dedicated unit/integration tests are:
1. **Budget Invariance:** The sum of `available_budget` + `reserved_budget` + `spent_budget` strictly equals `initial_budget` at all times.
2. **Integer Math Only:** Monetary math is performed strictly on unsigned 64-bit integers ($1\text{ USDC} = 1,000,000\text{ atomic base units}$). Zero floating-point money math.
3. **Double-Spend Prevention:** Ambiguous settlements (`SETTLEMENT_TIMEOUT` / network partition) lock reservations in `PENDING_RECONCILIATION`. Automated fallbacks are strictly blocked, preventing dual payment.
4. **Idempotent Reconciliation:** Reconciling an attempt multiple times produces exactly one ledger record and prevents duplicate reputation metrics.

---

## 2. Formal Payment State Transition Table

| Current State | Trigger / Event | Preconditions | Next State | Budget Action | Ledger Action | Retry / Fallback Behavior | Verification Evidence |
|---|---|---|---|---|---|---|---|
| **INIT** | `execute_paid_call` initiated | Valid service in catalog; policy checks pass | **RESERVED** | `budget.reserve(price)`: atomic lock | None | None (in flight) | `test_budget.py` |
| **INIT** | Policy check fails or disabled | Service terms invalid, forbidden chain | **REFUSED** | None | Recorded with `status: refused` | Terminated; no fallback | `test_payments.py` |
| **INIT** | Budget insufficient | `price > available_budget` | **REFUSED** | None | Recorded with `status: refused` | Refused; task aborted or downgraded | `test_budget.py` |
| **RESERVED** | HTTP error or initiation crash | Connection refused, 500 error before payment | **FAILED_AND_NOT_CHARGED** | `budget.release()`: full refund | Recorded with `status: failed and not charged` | Safe to execute fallback seller | `test_buyer_dependency_execution.py` |
| **RESERVED** | RPC timeout / ambiguous dispatch | Challenge issued, proof unconfirmed | **PENDING_RECONCILIATION** | Retained in suspense hold | Recorded with `status: pending reconciliation` | **FALLBACK BLOCKED**; awaiting reconciliation | `test_buyer_dependency_execution.py` |
| **RESERVED** | On-chain verified + Output valid | Status 0x1, valid ERC-20 log, schema matches | **PAID** | `budget.commit()`: deducted permanently | Recorded with `status: paid` | Step completed successfully | `test_payment_engine.py` |
| **RESERVED** | On-chain verified + Output invalid | Status 0x1, valid ERC-20 log, schema invalid | **PAID_OUTPUT_REJECTED** | `budget.commit()`: deducted permanently | Recorded with `status: paid output rejected` | Step failed; payment retained | `test_payment_engine.py` |
| **PENDING_RECONCILIATION** | `reconcile_attempt`: receipt confirmed | Authoritative on-chain receipt discovered (0x1) | **PAID** | `budget.commit()`: committed | Updated in ledger to `status: paid` | Settled; unblocks dependents | `test_reconciliation.py` |
| **PENDING_RECONCILIATION** | `reconcile_attempt`: definitively reverted | Receipt status 0x0 or proof proved invalid | **FAILED_AND_NOT_CHARGED** | `budget.release()`: refunded | Updated to `failed and not charged` | Unblocks task for retry | `test_reconciliation.py` |
| **PAID / PAID_OUTPUT_REJECTED** | Re-reconciliation attempted | Attempt already resolved in DB or memory | **NO CHANGE** (Idempotent) | None | Zero duplicate ledger rows | No-op | `test_reconciliation.py` |

---

## 3. Concurrency and Race Condition Audit

### 3.1 Idempotency Key Replay Protection
- When two identical requests with the same `Idempotency-Key` arrive simultaneously, `IdempotencyStore` registers the key atomically. The first request executes; subsequent requests wait or retrieve the cached response from memory or persistent storage.
- If an existing key is presented with a mutated payload hash, the verifier raises `IdempotencyConflictError` (HTTP 409) and refuses execution.

### 3.2 Concurrent Budget Reservations
- When 10 concurrent requests compete for a limited task budget, `BudgetManager._lock` synchronizes reservation accounting.
- In `test_concurrent_budget_reservations_with_durable_storage`, exactly 10 reservations of 1,000 units deplete a 10,000 unit budget to 0. An 11th reservation is rejected with `BudgetExceededError`. Overdraw is mathematically impossible.

### 3.3 Concurrent Reconciliation Safe Invariants
- `test_concurrent_reconciliation_does_not_create_duplicate_entries` simulates two concurrent reconciliation workers resolving the same payment attempt.
- The ledger repository enforces uniqueness constraints on `payment_id` / `request_id`, guaranteeing that only one ledger audit record is created.

---

## 4. Audit Verdict

**STAGE 2 AUDIT STATUS: PASSED / ZERO DISCREPANCIES DETECTED**  
All 24 reconciliation, state machine, idempotency, and budget tests pass. State transitions are deterministic, budget reservations are atomic, and double-spend fallback vulnerabilities are prevented.
