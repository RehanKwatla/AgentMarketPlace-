# AGENTICA — PHASE 5 RECONCILIATION & PAYMENT STATE MACHINE SPECIFICATION

**Phase:** 5.3 Reconciliation and Payment State Machine  
**Status:** ACCEPTED  
**Date:** 2026-10-17  
**Module Owner:** Member 1 (`backend/payments/`) & Member 4 (`backend/ledger/`)  
**Evidence Classification:** VERIFIED BY AUTOMATED TESTS & VERIFIED BY CODE INSPECTION  

---

## 1. Executive Summary

This document specifies the authoritative, deterministic payment and execution state machine for AGENTICA. It establishes rules preventing duplicate charging, ghost settlements, orphan budget reservations, and ledger divergence under unexpected server termination or network degradation.

All 10 dedicated reconciliation tests in `backend/tests/test_reconciliation.py` passed with zero errors, verifying:
- Single ledger entry creation upon reconciliation.
- Complete idempotency under concurrent reconciliation triggers.
- Invariant protection: `PENDING_RECONCILIATION` and `FAILED_AND_NOT_CHARGED` never credit seller reputation or debit user budget permanently.

---

## 2. Core State Enums & Meaning

### 2.1 Payment Status (`PaymentStatus` in `backend/payments/schemas.py`)
- `PAID`: Payment challenge verified, on-chain or facilitator settlement verified, output schema validated successfully. Funds committed.
- `PAID_OUTPUT_REJECTED`: Settlement confirmed on-chain or via facilitator, but seller returned malformed output failing catalog JSON schema. Funds committed to seller (service was executed), buyer marks step failed.
- `REFUSED`: Payment refused before initiation (e.g. insufficient task budget, service disabled, or policy violation). Zero funds spent, zero reservations held.
- `FAILED_AND_NOT_CHARGED`: Provider call failed, seller returned HTTP error (non-200), or settlement definitively aborted/reverted. Budget reservation released immediately.
- `PENDING_RECONCILIATION`: Payment initiation attempted or timeout occurred, leaving settlement state ambiguous. Budget reservation remains locked in suspense until authoritative reconciliation resolves it.

### 2.2 Task Step Status (`StepStatus` in `backend/buyer/models.py`)
- `PENDING`: Step awaiting execution.
- `RUNNING`: Step actively executing or awaiting seller response.
- `COMPLETED`: Step executed and verified with valid output.
- `FAILED`: Step execution failed or output invalid.
- `SKIPPED`: Dependent step skipped due to upstream dependency failure.

---

## 3. Authoritative State Transition Table

| Current State | Trigger / Event | Pre-Conditions | Resulting State | Budget Action | Ledger Action |
|---------------|-----------------|----------------|-----------------|---------------|---------------|
| `INITIATING` | `execute_paid_call()` start | Valid service, valid params | `RESERVED` | `reserve(amount)` | None |
| `RESERVED` | Budget Exceeded | Available < Price | `REFUSED` | Release reservation | None |
| `RESERVED` | Policy Violation / Price Gouge | Price > Catalog price | `REFUSED` | Release reservation | None |
| `RESERVED` | Network / HTTP Failure | Seller unreachable | `FAILED_AND_NOT_CHARGED` | `release(res_id)` | Record `FAILED` |
| `RESERVED` | Settlement Timeout | Gateway timeout / no response | `PENDING_RECONCILIATION` | **HOLD in suspense** | Record `PENDING` |
| `RESERVED` | Unverified Proof | Seller 200 but proof missing/invalid | `PENDING_RECONCILIATION` | **HOLD in suspense** | Record `PENDING` |
| `RESERVED` | Settlement Confirmed + Output Valid | Receipt valid + Schema match | `PAID` | `commit(res_id)` | Record `SETTLED` |
| `RESERVED` | Settlement Confirmed + Output Invalid | Receipt valid + Schema mismatch | `PAID_OUTPUT_REJECTED` | `commit(res_id)` | Record `SETTLED` (Flagged) |
| `PENDING_RECONCILIATION` | Reconciliation Triggered | Tx hash confirmed on Base Sepolia | `PAID` | `commit(res_id)` | Update ledger to `SETTLED` |
| `PENDING_RECONCILIATION` | Reconciliation Triggered | Tx definitively reverted (`0x0`) | `FAILED_AND_NOT_CHARGED` | `release(res_id)` | Update ledger to `FAILED` |
| `PENDING_RECONCILIATION` | Reconciliation Triggered | Tx still unmined / RPC unreachable | `PENDING_RECONCILIATION` | **HOLD retained** | No change |

---

## 4. Forbidden & Disallowed State Transitions

The following state transitions violate the protocol and are strictly prevented by code assertions and database checks:
1. `PAID` $\rightarrow$ `FAILED_AND_NOT_CHARGED` (Terminal state immutable).
2. `FAILED_AND_NOT_CHARGED` $\rightarrow$ `PAID` (Cannot charge after releasing reservation).
3. `PENDING_RECONCILIATION` $\rightarrow$ `PAID` **WITHOUT** cryptographic proof or verified RPC receipt.
4. `REFUSED` $\rightarrow$ `PAID` (Refused calls never execute).
5. Automatic retry of an ambiguous call without resolving prior `PENDING_RECONCILIATION` attempt.

---

## 5. Failure Injection & Boundary Scenarios

### Scenario A: Network Timeout During Facilitator Call
- **Action:** Adapter raises `SettlementTimeoutError`.
- **Handling:** Caught at Step 5 in `PaymentService.execute_paid_call`. State transitions to `PENDING_RECONCILIATION`.
- **Safety Guarantee:** Reservation is **NOT** released. Idempotency key stores the pending status.

### Scenario B: Process Crash Between Seller HTTP 200 and Ledger Insertion
- **Durable Persistence:** The payment attempt is persisted to `local_data/payments.db` with status, nonce, and raw proof.
- **Recovery:** On service startup or when `/api/v1/payments/reconcile-all` is called, durable attempts in `PENDING_RECONCILIATION` are queried. The settlement engine checks the Base Sepolia RPC or facilitator API, settling or releasing accordingly.

### Scenario C: Concurrent Duplicate Reconciliation Calls
- Tested by `test_concurrent_reconciliation_does_not_create_duplicate_entries`.
- 5 concurrent reconciliation tasks running against the same attempt result in exactly **1** commit and **1** ledger row. Extra requests receive idempotent `reconciled=True` confirmations.

---

## 6. Verification Evidence

Automated tests in `backend/tests/test_reconciliation.py`:
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
[10 passed]
```

**Gate Status:** PHASE 5 GATE D (ACCOUNTING AND RECOVERY - State Machine) — **PASSED**.
