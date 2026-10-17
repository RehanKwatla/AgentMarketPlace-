# AGENTICA — PHASE 6 RECONCILIATION, IDEMPOTENCY & REPLAY AUDIT

**Phase:** 6.2 Reconciliation, Idempotency, and Replay Resilience  
**Status:** **ACCEPTED**  
**Date:** 2026-10-17  
**Module Owner:** Member 1 (`backend/payments/`) & Member 4 (`backend/ledger/`)  
**Evidence Classification:** VERIFIED BY AUTOMATED TESTS & VERIFIED BY CODE INSPECTION  

---

## 1. Executive Summary

This audit establishes the resilience of AGENTICA against race conditions, duplicate execution, replay attacks, and financial double spending. All 16 dedicated tests in `backend/tests/test_reconciliation.py`, `backend/tests/test_budget.py`, and `backend/tests/test_replay.py` passed without failure (`16 passed in 0.43s`).

### Verified Core Invariants:
1. **Replay Defense:** Challenge nonces are cryptographically unique and stored in memory and on disk. Re-submitting a challenge nonce raises `ReplayAttackDetectedError`.
2. **Canonical Idempotency:** Payloads are serialized canonically via `compute_payload_hash` (sorted keys, compact separators). Duplicate requests return cached results with zero additional network dispatch or budget deductions. Re-using an idempotency key with a mismatched payload raises `IdempotencyConflictError` (HTTP 409).
3. **Idempotent Reconciliation:** Reprocessing an already paid attempt or dispatching concurrent reconciliation requests produces exactly **one** ledger record and commits the budget hold once.
4. **Suspense Confinement (Zero Premature Fallbacks):** When a payment attempt results in `PENDING_RECONCILIATION`, the budget hold is retained and automated fallbacks are **strictly blocked** to prevent duplicate charges.

---

## 2. Idempotency Key & Payload Canonicalization

In `backend/payments/idempotency.py`:
```python
def compute_payload_hash(payload: Any) -> str:
    """Compute canonical SHA-256 hash of a JSON-serializable request payload."""
    serialized = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()
```

### Request Lifecycle under Idempotency:
- **First Request:** Key and hash recorded as in-flight; execution proceeds.
- **Identical Replay:** `IdempotencyStore.check_or_register()` matches `payload_hash` and returns `(False, cached_data)`. The cached result is returned directly. Zero seller calls, zero charges.
- **Mismatched Payload:** Key matches but hash differs $\rightarrow$ raises `IdempotencyConflictError`.

---

## 3. Reconciliation State Invariants

In `backend/payments/service.py` (`reconcile_attempt` and `reconcile_all_pending`):
- **On-Chain Confirmed (0x1) & Valid ERC-20 Transfer:**
  - Status transitions to `PAID`.
  - Budget hold committed (`commit(res_id, amount)`).
  - Attempt updated in database.
  - Exactly one immutable row recorded in `ledger_repo`.
  - Removed from active suspense map.
- **On-Chain Definitively Reverted (0x0) or Proof Invalidated:**
  - Status transitions to `FAILED_AND_NOT_CHARGED`.
  - Budget hold released (`release(res_id)`).
  - Attempt updated with error reason.
  - Removed from active suspense map.
- **RPC Unreachable or Receipt Unmined:**
  - Status remains `PENDING_RECONCILIATION`.
  - Budget hold retained in suspense.
  - No ledger update performed.

---

## 4. Concurrent Reconciliation & Multi-Worker Safety

Automated test `test_concurrent_reconciliation_does_not_create_duplicate_entries` executes 5 concurrent reconciliation tasks simultaneously against the same suspended attempt:
- Exactly 1 task performs the ledger insert and budget commit.
- 4 concurrent tasks receive idempotent `reconciled=True` confirmations.
- Result: **Zero duplicate ledger rows.**

---

## 5. Automated Test Evidence

```
backend/tests/test_reconciliation.py::test_reconciled_payment_creates_one_ledger_entry PASSED
backend/tests/test_reconciliation.py::test_reprocessing_same_paid_payment_does_not_create_duplicates PASSED
backend/tests/test_reconciliation.py::test_concurrent_reconciliation_does_not_create_duplicate_entries PASSED
backend/tests/test_reconciliation.py::test_ledger_fields_match_reconciled_payment PASSED
backend/tests/test_reconciliation.py::test_seller_reputation_metrics_update_correctly PASSED
backend/tests/test_reconciliation.py::test_failed_and_pending_payments_do_not_count_as_successful PASSED
backend/tests/test_reconciliation.py::test_reputation_update_failure_retryable_recovery PASSED
backend/tests/test_reconciliation.py::test_inconsistent_payment_and_ledger_data_detected PASSED
backend/tests/test_reconciliation.py::test_reconciliation_api_endpoints PASSED
backend/tests/test_budget.py::test_integer_base_unit_conversions PASSED
backend/tests/test_budget.py::test_budget_reservation_and_commit PASSED
backend/tests/test_budget.py::test_budget_overdraw_prevention PASSED
backend/tests/test_budget.py::test_budget_release_refund PASSED
backend/tests/test_budget.py::test_concurrent_budget_reservations PASSED
backend/tests/test_replay.py::test_nonce_replay_detection PASSED
backend/tests/test_replay.py::test_idempotency_cache PASSED
[16 passed in 0.43s]
```

**Gate Status:** PHASE 6 GATE C (RECOVERY AND DUPLICATE PROTECTION) — **PASSED**.
