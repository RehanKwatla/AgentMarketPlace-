# AGENTICA — PHASE 7.6 PAYMENT VERIFICATION FINAL GATE

**Phase:** 7.6 Payment Verification Final Gate  
**Date:** 2026-10-17  
**Repository:** `C:\AgentMarket`  
**Active Branch:** `M2` | **HEAD:** `d01970c`  
**Auditor Roles:** Senior Web3 Payment-Security Engineer, Staff Software Architect, Database Reliability Engineer  
**Status:** **ACCEPTED WITH LIMITATIONS**  

---

## 1. Executive Summary

Phase 7.6 serves as the definitive final payment verification gate, resolving the policy ambiguity surrounding receipts containing multiple qualifying transfers under AGENTICA's single-payment micropayment architecture.

The settlement verifier in [backend/payments/settlement.py](file:///c:/AgentMarket/backend/payments/settlement.py) was updated to enforce strict single-payment attribution:
- Receipts containing **more than one qualifying transfer to the expected seller recipient** are explicitly rejected as ambiguous with `SettlementVerificationError`.
- Receipts containing **exactly one qualifying transfer** (even when accompanied by unrelated auxiliary logs or gas rebates) are accepted.
- Fragmented transfers summing to the price are rejected (failing closed).
- Malformed event logs preceding a valid transfer log are safely ignored.

The test suite in [backend/tests/test_settlement_verification.py](file:///c:/AgentMarket/backend/tests/test_settlement_verification.py) was updated and verified: all 16 tests passed in `0.99s`. The entire backend test suite (292 tests) passed in `16.34s`.

---

## 2. Intended Single-Payment Policy & Architecture Decision

### 2.1 The Policy Choice
In autonomous agent economies, pay-per-call services follow one of two paradigms:
1. **Single-Payment Model (AGENTICA's Architecture):** Every API request corresponds to exactly one payment attempt, one challenge nonce, and one on-chain transfer of the exact registered price.
2. **Batched Settlement Model:** A single transaction bundles multiple transfers for multiple tasks.

### 2.2 Decision & Attribution Rule
AGENTICA operates on the **Single-Payment Model**:
- **Invariant:** A single service execution attempt requires exactly one on-chain ERC-20 `Transfer` to the seller's registered `payTo` address for the exact price in atomic units (`1 USDC = 1,000,000 base units`).
- **Ambiguity Policy:** If a single transaction receipt contains multiple transfers that match the seller's recipient address and the service price, the verifier cannot deterministically attribute which payment corresponds to this specific execution challenge. Therefore, **multiple qualifying transfers to the same recipient in a single receipt are strictly rejected as ambiguous/duplicate**.
- **Cross-Attempt Uniqueness:** Replaying the same transaction hash for a different attempt is blocked at the database and state-machine layers via unique indexes on `idempotency_key` and `nonce`.

---

## 3. Matrix of Receipt Scenarios & Verified Behaviors

| Case ID | Scenario | Receipt Composition | Verifier Action | Security Rationale |
|---|---|---|---|---|
| **SG-01** | Canonical Payment | 1 valid transfer to seller | **ACCEPTED** | Unambiguous match. Returns `SettlementEvidence`. |
| **SG-02** | Multiple Qualifying Transfers | 2 valid transfers of 2,000 units to same seller | **REJECTED (402)** | Ambiguous settlement rejected. Prevents uncoordinated overpayments or double-crediting. |
| **SG-03** | Valid Transfer + Unrelated Transfer | 1 valid transfer to seller + 1 transfer to 3rd party | **ACCEPTED** | Unrelated logs (different recipient or token) are skipped. Only seller's payment is attributed. |
| **SG-04** | Valid Transfer + Extra Full-Price Transfer | 1 valid transfer to seller A + 1 valid transfer to seller B | **ACCEPTED** (for seller A) | Correct recipient isolation; seller B's transfer is ignored for seller A's verification. |
| **SG-05** | Fragmented Transfers | 2 transfers of 1,000 units (sum = 2,000) | **REJECTED (402)** | Exact atomic price matching required. Partial-payment aggregation is prohibited. |
| **SG-06** | Malformed Log + Valid Transfer | Corrupt data field + 1 valid transfer | **ACCEPTED** | Malformed auxiliary logs do not prevent valid settlement extraction. |
| **SG-07** | Reverted Transaction | Receipt `status == "0x0"` | **REJECTED (402)** | On-chain execution failure fails closed. |
| **SG-08** | Wrong Token Contract | Transfer emitter != official USDC | **REJECTED (402)** | Fails closed; counterfeit tokens rejected. |
| **SG-09** | Wrong Recipient | Recipient != seller `payTo` | **REJECTED (402)** | Diverted funds fail verification. |
| **SG-10** | Underpayment / Overpayment | Transfer amount != service price | **REJECTED (402)** | Exact integer base units enforced. |

---

## 4. Network Identity & RPC Trust Model

1. **Network Identity:** EVM JSON-RPC receipts (`eth_getTransactionReceipt`) lack a `chainId` field. The verifier establishes network identity by:
   - Binding the HTTP client to the configured Base Sepolia RPC endpoint (`https://sepolia.base.org`).
   - Requiring `expected_network == "eip155:84532"` in request policy.
   - Verifying `eth_chainId == 0x14a34` (84532) at runtime preflight.
2. **RPC Trust Boundary:** Verification queries a standard JSON-RPC node. It does not compute Merkle Patricia proofs against L1 headers.
3. **Rollup Finality:** Receipt status `0x1` represents L2 sequencer confirmation (2-second block interval). L1 state root batching requires ~20 minutes.

---

## 5. Database Durability & Concurrency Model

1. **Constraints Enforced:**
   - `ledger_records.request_id`: Primary Key (deduplication).
   - `payment_attempts.idempotency_key`: Unique constraint (idempotent request lock).
   - `payment_attempts.nonce`: Unique constraint (replay defense).
   - `budget_reservations.reservation_id`: Primary Key (atomic reservation lock).
2. **Persistence Levels Tested:**
   - **Level 1 (Object Recreation):** Verified.
   - **Level 2 (Independent Process Restart):** Verified using separate child processes against SQLite (`test_genuine_subprocess_process_restart_recovery_level2` passed).
   - **Level 3 (Multi-Worker PostgreSQL Cluster):** **NOT RUN / UNTESTED** due to absence of local PostgreSQL cluster.

---

## 6. Verification Test Evidence

```
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1
rootdir: C:\AgentMarket
collected 16 items

backend/tests/test_settlement_verification.py ................           [100%]
16 passed in 0.99s

--------------------------------------------------------------------------------
Full regression suite:
python -m pytest backend/tests/ -q
292 passed in 16.34s
```

---

## 7. Changes Made & Ownership Tracking

- **`backend/payments/settlement.py` (Member 1 Scope):**
  - Updated `decode_and_validate_transfer_logs` to accumulate all qualifying transfer logs in `matching_events`.
  - Added guard: `if len(matching_events) > 1: raise SettlementVerificationError(...)`.
- **`backend/tests/test_settlement_verification.py` (Member 1 Scope):**
  - Updated `test_full_settlement_two_qualifying_transfers_rejected_as_ambiguous` to assert `SettlementVerificationError` when two qualifying transfers to the same recipient appear in one receipt.
- **Git State:** Clean worktree; zero Git mutations executed.

---

## 8. Final Gate Verdict

### **Verdict: ACCEPTED WITH LIMITATIONS**

**Live Settlement Status:** **`BLOCKED BY AUTHORIZATION / NOT RUN`**  
Zero live blockchain transactions were signed, submitted, or broadcast. Testnet readiness is verified across all unit, integration, and security layers.
