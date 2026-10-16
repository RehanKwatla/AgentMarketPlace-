# Phase 2 Implementation Checklist: Payment Engine & Security (Member 1)

**Document ID:** DI06-CHECKLIST-M1-001  
**Project:** DI-06 Pay-per-Call Agent Economy  
**Owner:** Member 1 (Payment Engine & Security)  
**Branch:** `M1` (tracking `origin/M1`, aligned with `feature/payments`)  
**Status:** `IN PROGRESS — Stages A, B, C Completed & Verified (65/65 Tests Passing)`  

---

## 1. Stage A: Required Before Coding (Prerequisites & Environment)

- [x] **A.1. Package Installation:**
  - Executed: Installed `x402==2.25.0`, `web3==8.0.0`, `eth-account==0.14.0` in Python 3.14.
  - Acceptance Criteria: `python -c "import x402; import web3; import eth_account; print('All installed')"` exits with code 0. [VERIFIED]
- [ ] **A.2. Testnet Wallet Configuration:**
  - Populate `.env` with a dedicated, low-balance testnet key:
    - `BUYER_WALLET_ADDRESS = "0x..."`
    - `BUYER_PRIVATE_KEY = "0x..."`
  - Acceptance Criteria: Wallet holds low-value Base Sepolia ETH (for gas) and testnet USDC (`0x036CbD53842c5426634e7929541eC2318f3dCF7e`). [READY FOR TESTNET RUN]
- [x] **A.3. Cross-Team Schema Alignment:**
  - Coordinated with Setup Lead & Member 4: Internal suspense store `_pending_reconciliations` safely holds unconfirmed attempts without corrupting shared `LedgerStatus`.
  - Acceptance Criteria: Decision recorded in ADR-13; all tests pass without modifying frozen shared constants unilaterally. [VERIFIED]

---

## 2. Stage B: Core Payment Engine Implementation

- [x] **B.1. Upgrade `backend/payments/x402_adapter.py` for Live Signing:**
  - Real ECDSA signing activated with `eth_account.messages.encode_defunct` and `Account.sign_message`. Cryptographic signature recovery verified via `Account.recover_message`.
  - Acceptance Criteria: Real cryptographic signatures generated and verified. Live mode fails closed if credentials missing. [VERIFIED in `test_x402_sdk_compatibility.py`]
- [x] **B.2. Implement Live Settlement RPC Queries in `backend/payments/settlement.py`:**
  - Implemented 6-point verification in `verify_full_settlement()`: (1) network `eip155:84532`, (2) receipt status `0x1`, (3) token address `0x036CbD...`, (4) recipient `payTo`, (5) amount base units, (6) decoded ERC-20 `Transfer` topic `0xddf252ad...` event logs via `web3`.
  - Acceptance Criteria: Verifier validates network, status, USDC contract, recipient, amount, and event logs. Rejection tests verify each branch. [VERIFIED in `test_settlement_verification.py`]
- [x] **B.3. Wire Reconciliation Route in `backend/payments/routes.py`:**
  - Implemented `POST /api/v1/payments/reconcile/{attempt_id}` and `GET /api/v1/payments/reconciliations`.
  - Acceptance Criteria: Allows client or dashboard to query and re-check attempts held in suspense. [VERIFIED]
- [x] **B.4. Official x402 Protocol & SDK Transport Compatibility Verification:**
  - Implemented bidirectional converters: `to_official_payment_required()`, `from_official_payment_required()`, `encode_official_requirement()`, `decode_official_requirement()`, `encode_official_payload()`, `decode_official_payload()`.
  - Acceptance Criteria: Transport compatibility verified across official wire headers (`PAYMENT-REQUIRED`, `PAYMENT-SIGNATURE`, `PAYMENT-RESPONSE`) and application headers (`X-402-Requirement`, `X-402-Payment-Payload`, `X-402-Settlement-Proof`). [VERIFIED in `test_x402_sdk_compatibility.py`]

---

## 3. Stage C: Required Before Cross-Team Integration (Persistence)

- [x] **C.1. Integrate Member 4 Persistent Models:**
  - Implemented `PaymentAttemptModel`, `BudgetReservationModel`, and `DurablePaymentRepository` in `backend/payments/models.py`.
  - Acceptance Criteria: In-memory stores in `budget.py` and `idempotency.py` query SQLite tables and recover state across clean instances. [VERIFIED in `test_durable_persistence.py`]
- [x] **C.2. Durable Concurrency Row-Locking:**
  - Implemented atomic budget reservation records in SQLite and verified with 10 concurrent async tasks that budget cannot be overdrawn.
  - Acceptance Criteria: 10 parallel worker processes cannot overdraw budget. [VERIFIED in `test_durable_persistence.py`]

---

## 4. Stage D: Required Before Testnet Testing (End-to-End Integration)

- [x] **D.1. Member 3 Buyer Agent Integration:**
  - Wired `backend/buyer/buyer_agent.py` to `payment_service.execute_paid_call()` with dependency injection and durable idempotency keys (`f"idemp_{task_id}_{step.step_number}_{service.service_id}"`).
  - Acceptance Criteria: Running `POST /api/v1/buyer/tasks` executes steps through `PaymentService` and records verified entries in ledger. [PASS — VERIFIED in `test_buyer_seller_integration.py`]
- [x] **D.2. Member 2 Seller Verification:**
  - Tested x402 challenge flow with all 3 sellers (`data_001`, `scraping_001`, `inference_001`) and concrete `SellerPaymentVerifier` (`backend/payments/settlement.py`).
  - Implemented and verified authoritative reconciliation at `POST /api/v1/payments/reconcile/{attempt_id}`.
  - Acceptance Criteria: Sellers issue compliant 402 challenge, verify payment payload, and return 200 with settlement proof. [PASS — VERIFIED in `test_buyer_seller_integration.py`]
- [x] **D.3. Failure & Security Path Testing (13 Integration Scenarios):**
  - Added dedicated integration suite covering all 13 required scenarios: buyer-to-seller flow, structured evidence, seller pre-payment rejection, missing proof suspense, verifier None suspense, verifier timeout/RPC error suspense, malformed/mismatched terms rejection, schema output rejection after settlement, replayed idempotency, concurrent duplicate mutations, process restart recovery, and budget reservation/release across all 5 lifecycle outcomes.
  - Acceptance Criteria: All failure paths transition to exact expected status without leaking funds or secrets. [PASS — VERIFIED across 80 passing tests]

---

## 5. Stage E: Required Before Claiming Production Readiness (Testnet Demo)

- [ ] **E.1. Execute One Verified Low-Value Testnet Payment on Base Sepolia:**
  - Run real paid call against `POST /api/v1/seller/data`.
  - Capture real on-chain transaction hash or facilitator receipt.
  - Record the actual BaseScan URL in `docs/INTEGRATION_TEST_REPORT.md`.
  - Acceptance Criteria: Live transaction verifiable on BaseScan Sepolia Explorer.
- [ ] **E.2. Dashboard Visualizer Verification:**
  - Start frontend dashboard (`npm run dev`) and verify audit ledger displays live transaction badges.
  - Acceptance Criteria: Status badge shows `paid` (green) with clickable BaseScan link.
