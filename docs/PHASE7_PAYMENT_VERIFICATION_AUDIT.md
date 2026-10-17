# AGENTICA — PHASE 7 PAYMENT VERIFICATION AUDIT

**Project:** DI-06 — AGENTICA: Pay-per-Call Agent Economy  
**Tagline:** Discover. Pay. Execute. Trust.  
**Phase:** 7 (Stage 1 — Payment Contract and Settlement Verification Audit)  
**Date:** 2026-10-17  
**Module Owner:** Member 1 (`backend/payments/`) & Setup Lead  
**Evidence Classification:** `VERIFIED BY AUTOMATED TESTS` & `VERIFIED BY CODE INSPECTION`  

---

## 1. Executive Summary

This audit establishes the binding contract, verification invariants, and state-machine semantics implemented in `SettlementVerifier`, `SellerPaymentVerifier`, and `PaymentService`. 

The core invariant verified is:
> **A payment attempt is authorized for execution ONLY if a cryptographically verified receipt or settlement proof authoritatively binds to the exact challenge, registered seller payTo address, Base Sepolia network (`eip155:84532`), target USDC token contract (`0x036CbD53842c5426634e7929541eC2318f3dCF7e`), and integer base units.**
>
> **Neither an HTTP 200 response, a raw transaction hash `0x...`, nor an unverified facilitator string alone satisfies settlement.**

---

## 2. Six-Point On-Chain Verification Audit

In live verification mode (`test_mode=False`), `SettlementVerifier.verify_full_settlement` executes a strict 6-point EVM inspection against Base Sepolia JSON-RPC:

| # | Inspection Point | Implementation Mechanism | Adversarial Threat Prevented | Evidence Status |
|---|---|---|---|---|
| **1** | **Network Identity** | Checked against `expected_network == NETWORK_BASE_SEPOLIA` (`eip155:84532`) | Cross-chain replay or accepting cheap/test payments from alternate EVM chains | `VERIFIED BY AUTOMATED TESTS` |
| **2** | **Transaction Receipt Status** | Evaluates JSON-RPC receipt field `status in ("0x1", "1", 1)` | Reverted transactions (`status: 0x0`) attempting to claim service execution | `VERIFIED BY AUTOMATED TESTS` |
| **3** | **Token Contract Address** | Matches `log.address == USDC_BASE_SEPOLIA.lower()` (`0x036CbD53842c5426634e7929541eC2318f3dCF7e`) | Fake token transfers or worthless ERC-20 transfers spoofing USDC | `VERIFIED BY AUTOMATED TESTS` |
| **4** | **Recipient Address (`payTo`)** | Decodes `topic[2]` to 20-byte address; compares against registered `payTo` | Diverted payments sent to third parties or attacker wallets | `VERIFIED BY AUTOMATED TESTS` |
| **5** | **Exact Integer Base Units** | Decodes ABI uint256 data; asserts `transfer_amount == expected_amount_units` | Insufficient payments, partial transfers, or floating-point rounding exploits | `VERIFIED BY AUTOMATED TESTS` |
| **6** | **ERC-20 Event Signature** | Asserts `topic[0] == 0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | Malformed or non-Transfer event logs masquerading as settlement | `VERIFIED BY AUTOMATED TESTS` |

---

## 3. Multi-Log Receipt Policy

A transaction receipt on Base Sepolia may contain multiple event logs (e.g. batch transactions, multicall swaps, or fee distributions). The audit inspected `decode_and_validate_transfer_logs` in `backend/payments/settlement.py`:

- **Log Filtering:** The verifier iterates through `logs`, skipping non-token emitters, truncated topics (<3 topics), and non-Transfer topics.
- **Recipient Isolation:** Logs transferring funds to unrelated third parties do not abort evaluation; the verifier continues searching for the log paying the registered seller.
- **Amount Matching:** If an earlier log sends funds to the seller with a mismatched amount (e.g. fee rebate), the verifier records the discrepancy and continues searching. If an exact matching log is found, it confirms settlement. If no exact matching log is found, it raises `SettlementVerificationError`.
- **Zero Aggregation:** The verifier does NOT aggregate fragmented transfers. AGENTICA pricing requires a single canonical qualifying transfer satisfying the listed atomic price.

---

## 4. Transaction-to-Payment Association & Nonce Lifecycle

1. **Challenge Issuance:** When an agent queries a seller endpoint without payment or receives HTTP 402, `SellerPaymentVerifier.issue_challenge` generates a cryptographically random nonce (`nonce_<uuid4>`) bound to the service and price.
2. **Authorization Binding:** The buyer signs an EIP-712 payment authorization embedding `network`, `token`, `amount`, `payTo`, and the unique challenge `nonce`.
3. **Idempotency & Replay Defense:**
   - In `PaymentService.execute_paid_call`, the request is registered with `idempotency_store`.
   - Replayed nonces trigger `ReplayAttackDetectedError`.
   - Idempotency key reuse with an altered payload triggers `IdempotencyConflictError` (HTTP 409).
4. **Authoritative Evidence Separation:**
   - Facilitator receipts (`rec_auth_...`) are validated via facilitator REST endpoint.
   - On-chain hashes (`0x[0-9a-fA-F]{64}`) are validated via Base Sepolia JSON-RPC.
   - Mock signatures (`0x_mock_...`) are strictly rejected in live seller verification (`test_mode=False`).

---

## 5. Payment and Output Separation (Decoupled State Machine)

The audit confirms that payment finality is strictly decoupled from downstream execution validity:
- **Scenario A: Payment Confirmed + Seller Output Valid:**
  - Status: `PAID`
  - Budget: Committed
  - Ledger: Recorded with `status: paid`
- **Scenario B: Payment Confirmed + Seller Output Invalid (Schema Mismatch / Crash):**
  - Status: `PAID_OUTPUT_REJECTED`
  - Budget: Committed (the microservice executed and cost funds)
  - Ledger: Recorded with `status: paid output rejected`
  - Invariant: **A confirmed payment is NEVER deleted or refunded merely because the seller output was malformed.**
- **Scenario C: Ambiguous Settlement (RPC Timeout / Network Partition):**
  - Status: `PENDING_RECONCILIATION`
  - Budget: Retained in suspense (NOT released, NOT double-spent)
  - Fallback: Automated fallback is blocked until authoritative reconciliation occurs.

---

## 6. Audit Verdict

**STAGE 1 AUDIT STATUS: PASSED / SPECIFICATION VERIFIED**  
The implementation correctly enforces 6-point settlement verification, robust multi-log inspection, atomic budget reservations, and decoupled payment/output state machines.
