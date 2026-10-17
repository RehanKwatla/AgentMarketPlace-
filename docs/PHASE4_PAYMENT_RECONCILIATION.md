# AGENTICA — PHASE 4 PAYMENT INTEGRITY & RECONCILIATION REPORT
**Document:** `docs/PHASE4_PAYMENT_RECONCILIATION.md`  
**Date:** 17 October 2026  
**Auditor:** Member 1 (Payment Protocol Engineer) & Member 4 (Ledger Engineer)  
**Status:** COMPLETE (Stage 2 Master Plan)  
**Classification:** VERIFIED BY AUTOMATED TESTS & CODE INSPECTION  

---

## 1. Executive Summary

This report documents the verification and operational hardening of the x402 v2 payment lifecycle within AGENTICA. The payment subsystem enforces strict cryptographic guarantees, Base Sepolia testnet lockdown, fail-closed settlement verification, and durable reconciliation.

### Binding Safety Commitments
1. **Network & Token Lockdown:** Strictly restricted to Base Sepolia (`eip155:84532`) and USDC contract (`0x036CbD53842c5426634e7929541eC2318f3dCF7e`).
2. **Zero Fabrication:** Synthetic transaction hashes or mock settlement strings are strictly forbidden in live mode.
3. **Atomic Base Units:** All internal accounting uses 6-decimal integer base units (`1 USDC = 1,000,000 units`).
4. **Suspense Isolation:** Ambiguous payments are held in suspense (`PENDING_RECONCILIATION`) and never recorded as terminal `PAID` without verified proof.

---

## 2. End-to-End x402 v2 Lifecycle

```
Buyer Agent (Client)                   Seller Service (API)               Settlement Verifier
      │                                       │                                   │
      │ 1. POST /api/v1/seller/{service}      │                                   │
      │    (No payment headers attached)      │                                   │
      │──────────────────────────────────────>│                                   │
      │                                       │                                   │
      │ 2. HTTP 402 Payment Required          │                                   │
      │    Headers: X-402-Requirement         │                                   │
      │             PAYMENT-REQUIRED (Base64) │                                   │
      │<──────────────────────────────────────│                                   │
      │                                                                           │
      │ 3. Validate terms against Registry:                                       │
      │    - Network == 'eip155:84532'                                            │
      │    - Token == Base Sepolia USDC                                           │
      │    - Amount == registered price                                           │
      │    - PayTo == seller registered address                                   │
      │ 4. Reserve budget atomically (BudgetManager)                              │
      │ 5. Sign EIP-712 payment authorization                                     │
      │                                                                           │
      │ 6. POST /api/v1/seller/{service}                                          │
      │    Headers: X-402-Payment-Payload                                         │
      │             PAYMENT-SIGNATURE (Base64)                                    │
      │             Idempotency-Key                                               │
      │──────────────────────────────────────>│                                   │
      │                                       │ 7. verify_and_settle(payload, req)│
      │                                       │──────────────────────────────────>│
      │                                       │                                   │
      │                                       │ 8. SettlementEvidence             │
      │                                       │    (tx_hash / facilitator receipt)│
      │                                       │<──────────────────────────────────│
      │                                       │                                   │
      │                                       │ 9. Execute seller business logic  │
      │                                       │    (Only AFTER verified proof)    │
      │                                       │                                   │
      │ 10. HTTP 200 OK + Result Payload      │                                   │
      │     Headers: X-402-Settlement-Proof   │                                   │
      │              PAYMENT-RESPONSE         │                                   │
      │<──────────────────────────────────────│                                   │
      │                                                                           │
      │ 11. Draft-7 Output Validation                                             │
      │ 12. Record in Ledger (LedgerStatus: PAID / PAID_OUTPUT_REJECTED)          │
      │ 13. Commit budget reservation & release surplus                           │
```

---

## 3. Fail-Closed Verification Enforcement

The `SettlementVerifier` and `SellerPaymentVerifier` enforce 6-point verification in `backend/payments/settlement.py`:

1. **Network Check:** Rejects any transaction not on `eip155:84532`.
2. **Transaction Status:** Rejects reverted transactions (`receipt.status != 0x1`).
3. **Token Address:** Rejects transfers where `log.address != USDC_BASE_SEPOLIA`.
4. **Recipient Verification:** Rejects transfers where `transfer.to != expected_pay_to`.
5. **Amount Verification:** Rejects transfers where `transfer.value != expected_amount_units`.
6. **Decoded ERC-20 Transfer Log:** Uses `web3` contract ABI to decode topic `0xddf252ad...` and verify the sender matches the payer.

### Negative Test Evidence
All rejection scenarios are verified by dedicated tests in `backend/tests/test_settlement_verification.py`:
- `test_full_settlement_rejection_on_wrong_network`: PASSED
- `test_full_settlement_rejection_on_wrong_token_contract`: PASSED
- `test_full_settlement_rejection_on_wrong_recipient`: PASSED
- `test_full_settlement_rejection_on_wrong_amount`: PASSED
- `test_full_settlement_rejection_on_reverted_receipt_status`: PASSED
- `test_full_settlement_rejection_on_missing_event_logs`: PASSED
- `test_full_settlement_rejection_on_wrong_payer`: PASSED

---

## 4. Idempotency & Replay Defense

### 4.1 Hierarchical Idempotency Keys
- **Task Session:** `task_id` (UUID4).
- **Service Call:** `call_id = f"call_{task_id[:8]}_{step_id}"`.
- **Payment Idempotency Key:** `f"idemp_{task_id}_{step_number}_{service_id}"`.
- **Payment Nonce:** Single-use nonce emitted by seller verifier, tracked in durable storage.

### 4.2 Durable Idempotency Storage
In `backend/payments/idempotency.py` and `backend/payments/models.py`, `IdempotencyStore` persists attempt records to the database. If a duplicate request arrives:
- **Same Request Hash:** Returns the cached response immediately without executing the seller or issuing a second payment.
- **Mutated Request Hash:** Rejects immediately with HTTP 409 `IDEMPOTENCY_CONFLICT`.

---

## 5. Suspense Store & Batch Reconciliation

### 5.1 Uncertain Payment Handling
When payment proof verification is ambiguous (e.g. RPC timeout, network failure, or pending facilitator status):
1. Attempt is assigned `PaymentStatus.PENDING_RECONCILIATION`.
2. The attempt record is persisted in `payment_attempts` with `error_code="SETTLEMENT_UNVERIFIED"`.
3. Budget reservation remains locked to prevent overdrawing while outcome is indeterminate.
4. The attempt is **not** committed to the shared ledger as `PAID`.

### 5.2 Authoritative Batch Reconciliation
Implemented in `PaymentService.reconcile_all_pending()` (`backend/payments/service.py`) and exposed via:
- `POST /api/v1/payments/reconcile` (batch reconciliation of all pending attempts)
- `POST /api/v1/payments/reconcile/{attempt_id}` (reconciliation of single attempt)

The reconciler queries the facilitator or JSON-RPC endpoint:
- **If confirmed settled:** Transitions attempt to `SETTLED`, records `PAID` into the audit ledger, commits budget reservation, and updates reputation.
- **If confirmed failed:** Transitions attempt to `SETTLEMENT_REJECTED`, releases budget reservation, and marks ledger as `FAILED_AND_NOT_CHARGED`.
- **If still pending:** Preserves suspense status without data mutation.

Verified by automated tests in `test_phase3_payment_hardening.py`:
- `test_reconcile_all_pending_batches_in_memory_and_durable`: PASSED
- `test_reconcile_batch_route`: PASSED
