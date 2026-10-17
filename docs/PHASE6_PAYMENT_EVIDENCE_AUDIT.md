# AGENTICA — PHASE 6 PAYMENT EVIDENCE & STATE-MACHINE AUDIT

**Phase:** 6.1 Payment Evidence and State-Machine Audit  
**Status:** **ACCEPTED**  
**Date:** 2026-10-17  
**Module Owner:** Member 1 (`backend/payments/`) & Setup Lead  
**Evidence Classification:** VERIFIED BY AUTOMATED TESTS & VERIFIED BY CODE INSPECTION  

---

## 1. Executive Summary

This audit establishes the rigorous, fail-closed payment verification lifecycle in AGENTICA. All 35 dedicated payment verification, policy, engine, and settlement tests passed without failure (`35 passed in 5.48s`).

### Core Findings & Guarantees:
1. **6-Point On-Chain Settlement Verification:** Evaluates Base Sepolia network ID (`eip155:84532`), receipt status (`0x1`), token address (`USDC_BASE_SEPOLIA`), verified seller recipient (`payTo`), exact integer token amount, and decoded ERC-20 `Transfer(address,address,uint256)` event log topics.
2. **Fail-Closed Semantics:** Unverified hashes, unconfirmed transactions, RPC outages, and missing facilitator receipts transition directly to `PENDING_RECONCILIATION` without releasing held budget reservations.
3. **Strict State Decoupling:** Payment settlement (`PAID`) and execution output validity (`StepStatus.COMPLETED` vs. `StepStatus.FAILED`) are strictly separated in accounting. If a seller delivers invalid JSON failing the catalog schema, the seller remains paid (the workload was executed), while the buyer records `PAID_OUTPUT_REJECTED` and marks the workflow step as failed.
4. **Synthetic Receipt Confinement:** Synthetic receipts (`rec_auth_...`, `receipt_...`) are permitted only in development/test modes (`test_mode=True`) and are explicitly badged as `SIMULATED`. In live mode, synthetic proofs are rejected.
5. **No Speculative Explorer Links:** Transaction explorer links (`https://sepolia.basescan.org/tx/0x...`) are generated exclusively for validated 64-hex transaction hashes, never for synthetic receipts.

---

## 2. End-to-End Payment Lifecycle Trace

```
[Buyer Client]                              [Seller Endpoint]                         [Base Sepolia / Facilitator]
      │                                             │                                              │
      │ 1. POST /api/v1/seller/<service> (No Auth)  │                                              │
      ├────────────────────────────────────────────>│                                              │
      │                                             │ (Halt execution: no payment)                │
      │ 2. HTTP 402 + X-402-Requirement Header     │                                              │
      │<────────────────────────────────────────────┤                                              │
      │                                             │                                              │
      │ 3. Pre-Payment Verification (Policy):       │                                              │
      │    - Check price <= catalog price           │                                              │
      │    - Check network == eip155:84532          │                                              │
      │    - Check token == Base Sepolia USDC       │                                              │
      │    - Check recipient == seller pay_to       │                                              │
      │    - Reserve budget atomically              │                                              │
      │                                             │                                              │
      │ 4. Re-Request + X-402-Payment-Payload       │                                              │
      ├────────────────────────────────────────────>│                                              │
      │                                             │ 5. Seller Verification:                      │
      │                                             │    - In live mode: reject mock signatures    │
      │                                             │    - Verify authorization terms              │
      │                                             │    - Query verifier / settle                 │
      │                                             │    - Execute seller workload                 │
      │                                             │                                              │
      │ 6. HTTP 200 + X-402-Settlement-Proof        │                                              │
      │<────────────────────────────────────────────┤                                              │
      │                                             │                                              │
      │ 7. Post-Execution Verification:             │                                              │
      │    - Query Base Sepolia JSON-RPC receipt    │                                              │
      │    - If verified: commit budget, write      │                                              │
      │      settled record to Ledger               │                                              │
      │    - If timeout / unverified: hold          │                                              │
      │      suspense in PENDING_RECONCILIATION     │                                              │
      ▼                                             ▼                                              ▼
```

---

## 3. Strict 6-Point Settlement Verification Invariants

In `backend/payments/settlement.py`, `SettlementVerifier.verify_full_settlement()` validates:

| Check # | Verification Criterion | Failure Mode Action |
|---|---|---|
| **1** | `expected_network == "eip155:84532"` | Raises `SettlementVerificationError("Network mismatch")` |
| **2** | Transaction receipt `status == "0x1"` | Raises `SettlementVerificationError("unconfirmed or reverted")` |
| **3** | Log emitter address equals `USDC_BASE_SEPOLIA` | Skips foreign token logs; raises if none match |
| **4** | Topic[2] (recipient) matches seller `payTo` address | Rejects logs paying wrong recipient |
| **5** | Event `data` field integer matches `expected_amount_units` | Raises `SettlementVerificationError("amount mismatch")` |
| **6** | Topic[0] matches ERC-20 `Transfer` topic hash | Rejects non-Transfer event logs |

---

## 4. State Machine Transition Table

| Starting State | Trigger / Event | Pre-Conditions | Resulting State | Budget Hold Action | Ledger Status |
|---|---|---|---|---|---|
| `UNRESERVED` | Task Initiated | Valid service, valid params | `RESERVED` | `reserve(amount)` | None |
| `RESERVED` | Budget Exhausted | Price > Available budget | `REFUSED` | `release(res_id)` | None |
| `RESERVED` | Policy Violation | Price > Catalog price | `REFUSED` | `release(res_id)` | None |
| `RESERVED` | Seller Network Error | Seller unreachable (5xx/4xx) | `FAILED_AND_NOT_CHARGED` | `release(res_id)` | `failed and not charged` |
| `RESERVED` | Settlement Timeout | Gateway timeout / unconfirmed | `PENDING_RECONCILIATION` | **RETAIN HOLD** | `pending reconciliation` |
| `RESERVED` | Unverified Proof | Seller 200 but proof unverified | `PENDING_RECONCILIATION` | **RETAIN HOLD** | `pending reconciliation` |
| `RESERVED` | Verified Settlement + Output Valid | 6-point check passed + schema match | `PAID` | `commit(res_id)` | `paid` |
| `RESERVED` | Verified Settlement + Output Invalid | 6-point check passed + schema fail | `PAID_OUTPUT_REJECTED` | `commit(res_id)` | `paid output rejected` |
| `PENDING_RECONCILIATION` | Authoritative Reconciliation | On-chain status confirmed (0x1) | `PAID` | `commit(res_id)` | Transition to `paid` |
| `PENDING_RECONCILIATION` | Authoritative Reconciliation | On-chain status reverted (0x0) | `FAILED_AND_NOT_CHARGED` | `release(res_id)` | Transition to `failed` |
| `PENDING_RECONCILIATION` | Authoritative Reconciliation | On-chain status still unmined | `PENDING_RECONCILIATION` | **RETAIN HOLD** | No change |

---

## 5. Automated Test Evidence

```
backend/tests/test_settlement_verification.py (11 tests) PASSED
backend/tests/test_payments.py (5 tests) PASSED
backend/tests/test_payment_engine.py (10 tests) PASSED
backend/tests/test_phase3_payment_hardening.py (9 tests) PASSED
[35 passed in 5.48s]
```

**Gate Status:** PHASE 6 GATE B (PAYMENT CORRECTNESS) — **PASSED**.
