# AGENTICA — PHASE 4 CONTRACT ALIGNMENT AUDIT
**Document:** `docs/PHASE4_CONTRACT_AUDIT.md`  
**Date:** 17 October 2026  
**Auditor:** Coordinated Engineering Team (Setup Lead, Members 1–4)  
**Status:** COMPLETE (Stage 1 Master Plan)  
**Classification:** VERIFIED BY CODE INSPECTION & TEST AUDIT  

---

## 1. Executive Summary

This document performs an exhaustive cross-subsystem contract audit across all shared schemas, subsystem domain models, database definitions, and frontend TypeScript interfaces.

The primary architectural requirement is to guarantee:
1. **Zero Currency Ambiguity:** Internal arithmetic MUST use integer base units (`1 USDC = 1,000,000 atomic units`). Floating-point money math is strictly forbidden.
2. **Clear Separation of Concerns:**
   - **Estimates:** Pre-execution expected price from Service Registry.
   - **Budget Reservations:** Locked atomic capacity prior to HTTP challenge.
   - **Payment Amounts:** Signed authorization amounts.
   - **Confirmed Spend:** Authoritative ledger records backed by verified settlement evidence.
3. **Status Decoupling:** Delivery state (`SUCCEEDED`, `OUTPUT_REJECTED`, `FAILED`) is decoupled from settlement state (`PAID`, `PENDING_RECONCILIATION`, `FAILED_AND_NOT_CHARGED`).

---

## 2. Cross-Subsystem Schema Matrix

| Concept | Shared Schema (`backend/shared/schemas.py`) | Buyer Schema (`backend/buyer/schemas.py`) | Ledger Model (`backend/database/models.py`) | Payment Model (`backend/payments/schemas.py`) | Frontend Type (`frontend/src/types/index.ts`) | Status |
|---|---|---|---|---|---|---|
| **Service Definition** | `ServiceDefinition` | Referenced directly | `ServiceRecordModel` | Not applicable | `ServiceDefinition` | **ALIGNED** |
| **Capability Profile**| `CapabilityMetadata` | Evaluated in `ServiceSelector` | Stored in JSON | Not applicable | Optional in UI | **ALIGNED** |
| **Task Request** | `TaskRequest` | `TaskCreationRequest` | `TaskRecordModel` | Not applicable | `submitBuyerTask` body | **ALIGNED** |
| **Step Execution** | `ExecutionStep` | `ServiceCallRecord` | `LedgerRecordModel` | `PaymentAttemptRecord`| `ExecutionStep` | **ALIGNED** |
| **Task Detail Response**| `TaskResponse` | `TaskDetailResponse` | Hydrated from DB | Not applicable | `TaskResponse` | **ALIGNED** |
| **Audit Ledger Record**| `LedgerRecordSchema`| Synced in `TaskRepository`| `LedgerRecordModel` | `PaymentAttemptRecord`| `LedgerRecord` | **ALIGNED** |
| **Currency Value** | `price_usdc` (str) + `price_base_units` (int) | `budget_usdc` (str) + `max_budget_atomic` (int) | `amount_paid` (str) + `amount_paid_units` (int) | `amount_base_units` (int) | `price_usdc` (str) + `price_base_units` (int) | **ALIGNED** |

---

## 3. Money Representation & Accounting Invariants

### 3.1 Conversion Implementation
All currency conversions in AGENTICA rely strictly on `backend/shared/constants.py`:
```python
def usdc_to_base_units(amount_usdc: str | float | Decimal) -> int:
    d = Decimal(str(amount_usdc))
    units = (d * Decimal(USDC_BASE_UNIT_MULTIPLIER)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(units)

def base_units_to_usdc(units: int) -> str:
    d = Decimal(units) / Decimal(USDC_BASE_UNIT_MULTIPLIER)
    return f"{d:.6f}"
```

### 3.2 Invariant Verification Across Modules
1. **Registry (`backend/registry/`):**
   - Stores `price_usdc` as Decimal string (`"0.002"`, `"0.003"`, `"0.004"`).
   - Automatically computes `price_base_units` via Pydantic validator (`2000`, `3000`, `4000`).
2. **Buyer Agent (`backend/buyer/`):**
   - Validates `TaskCreationRequest`: converts `budget_usdc` into `max_budget_atomic` integer base units without float arithmetic.
   - Calculates plan budget limits and step allocations strictly using integer sums:
     ```python
     total_units = sum(s.estimated_cost_base_units for s in plan.steps)
     ```
3. **Payment Engine (`backend/payments/`):**
   - `BudgetManager.reserve_budget`: reserves atomic integer units under `asyncio.Lock` and persists `BudgetReservationModel`.
   - `SettlementVerifier.verify_full_settlement`: verifies on-chain event log `value == expected_amount_units`.
4. **Ledger Subsystem (`backend/ledger/`):**
   - `LedgerRecordModel` stores both human-readable string `amount_paid` and integer `amount_paid_units`.
   - Reputation and volume metrics (`total_volume_units`) accumulate strictly using integer arithmetic.

---

## 4. Status Alignment and State Transitions

### 4.1 Buyer Task & Call Statuses
- **Buyer `TaskStatus`:** `ACCEPTED` -> `PLANNING` -> `RUNNING` -> `COMPLETED` / `COMPLETED_WITH_WARNINGS` / `FAILED` / `REFUSED` / `PENDING_RECONCILIATION`.
- **Buyer `CallStatus`:**
  - `CREATED`: Step planned, not yet invoked.
  - `AWAITING_PAYMENT`: Challenge received from seller.
  - `EXECUTING`: Payment verified, seller lifecycle running.
  - `VALIDATING_OUTPUT`: Output received, schema checking underway.
  - `SUCCEEDED`: Output valid, step concluded.
  - `PAID_OUTPUT_REJECTED`: Settlement confirmed, but seller produced invalid schema output.
  - `REFUSED`: Rejected before payment (422 input validation).
  - `FAILED_AND_NOT_CHARGED`: Provider error or seller timeout prior to payment.
  - `PENDING_RECONCILIATION`: Settlement ambiguous or proof unconfirmed.

### 4.2 Terminal Ledger Statuses (`LedgerStatus`)
Defined in `backend/shared/constants.py`:
1. `PAID` (`"paid"`): Verified settlement evidence confirmed on-chain or via facilitator, valid delivery.
2. `PAID_OUTPUT_REJECTED` (`"paid output rejected"`): Verified settlement confirmed, but seller output failed validation.
3. `REFUSED` (`"refused"`): Request rejected prior to payment (422).
4. `FAILED_AND_NOT_CHARGED` (`"failed and not charged"`): Seller failed or timed out before settlement occurred.

### 4.3 Internal Payment Statuses (`PaymentStatus`)
Defined in `backend/payments/schemas.py`:
- `NOT_STARTED`, `PAYMENT_REQUIRED`, `PENDING_PAYMENT`, `PAYMENT_SUBMITTED`, `SETTLED`, `SETTLEMENT_REJECTED`, `FAILED_AND_NOT_CHARGED`, `PENDING_RECONCILIATION`.

### 4.4 Suspense & Reconciliation Boundary
Uncertain settlement attempts (`PENDING_RECONCILIATION`) are preserved in durable storage (`PaymentAttemptModel`) and an internal suspense store. In compliance with Decision 14, uncertain payments are **never** recorded into the shared ledger as terminal `PAID` or `REFUSED` until resolved by authoritative reconciliation.

---

## 5. Contract Alignment Conclusion

* **Schema Parity:** All shared schemas match subsystem implementations.
* **Currency Formatting:** Full conformance with Base Sepolia USDC 6-decimal integer atomic accounting.
* **Public Endpoints:** Backward-compatible aliases exist for both `/api/v1/tasks` and `/api/v1/buyer/tasks`.
* **Frontend Compatibility:** The React/TypeScript frontend client types in `frontend/src/types/index.ts` align 100% with backend responses.
