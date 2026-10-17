# AGENTICA — PHASE 5 FINAL PAYMENT & SETTLEMENT VERIFICATION

**Phase:** Verification & Release Freeze (Stage D)  
**Date:** 2026-10-17  
**Module Owner:** Member 1 (`backend/payments/`) & Security Engineer  
**Evidence Classification:** VERIFIED BY AUTOMATED TESTS & VERIFIED BY CODE INSPECTION  

---

## 1. Executive Summary

This audit independently re-verifies the payment and settlement invariants implemented in `backend/payments/`, `backend/sellers/routes.py`, `backend/buyer/payment_client.py`, and `backend/ledger/`.

All 42 dedicated payment, settlement, budget, replay, and reconciliation tests passed without failure (`42 passed in 2.23s`).

---

## 2. Invariant Verification Analysis

### D1. Monetary Arithmetic Invariants
- **Base Unit Standard:** 1 USDC = 1,000,000 integer base units (`USDC_DECIMALS = 6`).
- **Zero Floating-Point Drift:** In `backend/shared/constants.py`, `base_units_to_usdc` and `usdc_to_base_units` perform strict string-based integer conversion. Floating-point arithmetic is strictly forbidden.
- **Negative & Zero Amounts:** `BudgetManager.reserve()` raises `ValueError("Reservation amount must be positive integer.")` if amount $\le 0$.

### D2. Buyer Policy Invariants
In `backend/payments/policy.py` and `backend/buyer/payment_client.py`:
- Registered service verification: Checked against `service_catalog`.
- Price gouging prevention: Rejects challenges where requested amount > catalog registered price.
- Network confinement: Pinned to `eip155:84532` (Base Sepolia).
- Token confinement: Pinned to `0x036CbD53842c5426634e7929541eC2318f3dCF7e`.
- Recipient validation: Checked against seller `payTo` address.
- Budget reservation: Funds locked under `asyncio.Lock` *before* outbound seller invocation.

### D3. Seller Enforcement Invariants
In `backend/sellers/routes.py`:
- Unpaid requests return HTTP 402 with `X-402-Requirement`. **Zero business logic executes.**
- Missing or malformed payloads (`X-402-Payment-Payload`) return HTTP 400 or fresh HTTP 402.
- Verifier outages fail closed: If the payment verifier raises an unhandled exception or is missing, returns HTTP 503 or HTTP 402.
- Seller errors do not create false settlement proofs.

### D4. Settlement Evidence Invariants
In `backend/payments/settlement.py`:
- 6-Point On-Chain Validation:
  1. `expected_network == "eip155:84532"`
  2. Transaction receipt `status == 0x1`
  3. Log address matches `USDC_BASE_SEPOLIA`
  4. Log topic[2] matches seller `payTo` address
  5. Log data matches exact integer base units
  6. Topic[0] matches `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef`
- A raw transaction hash `0x...` is never accepted on syntax alone; it must be verified via Base Sepolia RPC.

### D5. State Machine Invariants
In `backend/payments/service.py`:
- Settlement confirmation commits budget reservation exactly once.
- Schema invalid output after confirmed settlement preserves payment as `PAID` (work was executed and settled) while recording execution as `OUTPUT_REJECTED`.
- Definitive failure before settlement releases the reservation immediately.
- Ambiguous settlement (`SettlementTimeoutError` or missing proof) holds reservation in `PENDING_RECONCILIATION`.
- Fallbacks are strictly blocked when settlement is uncertain.

### D6. Idempotency and Replay Protection
In `backend/payments/idempotency.py`:
- Identical retries return cached result without re-executing.
- Reusing an idempotency key with a mismatched payload raises `IdempotencyConflictError` (HTTP 409).
- Challenge nonces are tracked in `_used_nonces` and durable SQLite storage; replaying a nonce raises `ReplayAttackDetectedError`.

---

## 3. Test Evidence

```
backend/tests/test_settlement_verification.py (11 tests) PASSED
backend/tests/test_payments.py (5 tests) PASSED
backend/tests/test_payment_engine.py (10 tests) PASSED
backend/tests/test_reconciliation.py (9 tests) PASSED
backend/tests/test_budget.py (5 tests) PASSED
backend/tests/test_replay.py (2 tests) PASSED
[42 passed in 2.23s]
```

**Verdict:** All payment and settlement invariants are strictly enforced and verified.
