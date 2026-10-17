# AGENTICA — PHASE 5 BUDGET, IDEMPOTENCY & REPLAY PROTECTION AUDIT

**Phase:** 5.4 Budget, Idempotency, and Replay Protection  
**Status:** ACCEPTED  
**Date:** 2026-10-17  
**Module Owner:** Member 1 (`backend/payments/`) & Setup Lead / Integration  
**Evidence Classification:** VERIFIED BY AUTOMATED TESTS & VERIFIED BY CODE INSPECTION  

---

## 1. Executive Summary

This document audits the mechanisms that prevent double spending, race conditions, replay attacks, and budget overruns in AGENTICA. 

Key verified invariants:
- **Zero Floating-Point Money Math:** All arithmetic is performed strictly on 6-decimal integer base units (`1 USDC = 1,000,000 base units`).
- **Atomic Two-Phase Budget Hold:** Funds are reserved under an `asyncio.Lock` and persisted to SQLite/PostgreSQL *before* any network call to a seller is dispatched.
- **Durable Idempotency & Conflict Detection:** Idempotency keys are hashed against canonical JSON payloads (`compute_payload_hash` using sorted keys and compact separators). Reusing a key with a mismatched payload raises `IdempotencyConflictError`. Reusing a key with an identical payload returns the cached result without re-executing or double-charging.
- **Cryptographic Replay Protection:** Every seller payment challenge generates a unique nonce (`nonce_<uuid.hex>`). Replaying a nonce raises `ReplayAttackDetectedError`.

---

## 2. Integer Atomic Units & Money Representation

In `backend/shared/constants.py`:
- `USDC_DECIMALS = 6`
- `USDC_BASE_UNIT = 1_000_000`
- `usdc_to_base_units("0.002000") -> 2000`
- `base_units_to_usdc(2000) -> "0.002000"`

Under no circumstance does any payment or budget method accept floating-point numbers (`float`). Negative reservation amounts raise `ValueError`.

---

## 3. Budget Lifecycle & Concurrency Invariants

### 3.1 Invariants
1. $Available = Total - Reserved - Spent$
2. At all times: $Available \ge 0$.
3. Any attempt to reserve $Amount > Available$ raises `BudgetExceededError`.
4. Overdraw is mathematically impossible even under massive concurrent coroutine execution.

### 3.2 Two-Phase Budget Allocation
```
      [Initial Task Budget]
                │
                ▼
      ┌──────────────────┐
      │ reserve(res_id)  │──> (Available -= amount, Reserved += amount)
      └──────────────────┘
                │
      ┌─────────┴─────────┐
      │                   │
[Success]             [Failure]
      │                   │
      ▼                   ▼
┌──────────────────┐ ┌──────────────────┐
│ commit(res_id)   │ │ release(res_id)  │
│ (Reserved -= X,  │ │ (Reserved -= X,  │
│  Spent += X)     │ │  Available += X) │
└──────────────────┘ └──────────────────┘
```

---

## 4. Idempotency Key Construction & Request Canonicalization

`compute_payload_hash(payload)` in `backend/payments/idempotency.py` enforces canonical serialization:
```python
def compute_payload_hash(payload: Any) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()
```

### Idempotency State Machine
1. **New Request (`is_new=True`):** Caller registers in-flight key. No cached result exists. Execution proceeds.
2. **Identical Replay (`is_new=False`, matching hash):** Cached execution result returned immediately. Zero seller network calls, zero payment deductions.
3. **Mismatched Payload Conflict:** Same idempotency key submitted with different input arguments. Raises `IdempotencyConflictError` (HTTP 409).

---

## 5. Nonce Lifecycle & Replay Detection

1. **Challenge Generation:** Seller issues challenge containing unique nonce `nonce_<uuid4().hex[:16]>`.
2. **Buyer Authorization:** Buyer includes the nonce in the signed EIP-712 / x402 authorization.
3. **Seller Nonce Verification:** `IdempotencyStore.record_and_verify_nonce(nonce)` checks in-memory active cache and durable database. If previously seen, execution is halted with `ReplayAttackDetectedError`.

---

## 6. Automated Test Verification Results

Tests in `backend/tests/test_budget.py`, `backend/tests/test_replay.py`, and `backend/tests/test_payment_engine.py`:
```
backend/tests/test_budget.py::test_integer_base_unit_conversions PASSED
backend/tests/test_budget.py::test_budget_reservation_and_commit PASSED
backend/tests/test_budget.py::test_budget_overdraw_prevention PASSED
backend/tests/test_budget.py::test_budget_release_refund PASSED
backend/tests/test_budget.py::test_concurrent_budget_reservations PASSED
backend/tests/test_replay.py::test_nonce_replay_detection PASSED
backend/tests/test_replay.py::test_idempotency_cache PASSED
backend/tests/test_payment_engine.py::test_idempotency_replay_cached_result PASSED
backend/tests/test_payment_engine.py::test_idempotency_conflict_different_payload PASSED
[9 passed]
```

**Gate Status:** PHASE 5 GATE D (ACCOUNTING AND RECOVERY - Invariants & Idempotency) — **PASSED**.
