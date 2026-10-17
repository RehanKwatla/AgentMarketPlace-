# AGENTICA — PHASE 5 CONTRACT & API CONSISTENCY AUDIT
**Document:** `docs/PHASE5_CONTRACT_AND_API_AUDIT.md`  
**Date:** 17 October 2026  
**Auditor:** Setup Lead & Module Owners (Members 1–4)  
**Status:** COMPLETE (Phase 5.1 Workstream)  
**Classification:** VERIFIED BY CODE INSPECTION & TEST AUDIT  

---

## 1. Executive Summary

This audit performs an end-to-end verification of all data contracts, schemas, enumerations, wire formats, and API models across the AGENTICA marketplace. It verifies that:
1. Producers and consumers agree on schema definitions without data truncation or drift.
2. Monetary amounts use unambiguous integer base units (`1 USDC = 1,000,000 atomic units`).
3. Payment, task, and ledger statuses have distinct, non-overlapping semantic definitions.
4. Error responses follow a uniform structured format.

---

## 2. API Contract & Schema Alignment Matrix

| Data Contract | Producer Subsystem | Consumer Subsystem(s) | Wire / Python Type | Alignment Verification |
|---|---|---|---|---|
| `ServiceDefinition` | Registry (`backend/registry/`) | Buyer Agent, Frontend Dashboard | Pydantic model (`backend/shared/schemas.py`) | **ALIGNED** — All fields (`service_id`, `name`, `price_usdc`, `price_base_units`, `pay_to`, `capability_metadata`) match frontend `ServiceDefinition` interface. |
| `CapabilityMetadata` | Registry seeds (`backend/registry/`) | Buyer Selector (`backend/buyer/selector.py`) | Pydantic model (`backend/shared/schemas.py`) | **ALIGNED** — Supports `tags`, `supported_formats`, `max_payload_bytes`, `sla_latency_p95_ms`, `constraints`. |
| `PaymentRequirement` | Seller Routes (`backend/sellers/routes.py`) | Buyer Agent (`backend/buyer/payment_client.py`) | Header `X-402-Requirement` / Base64 JSON | **ALIGNED** — Emits CAIP-2 `network: "eip155:84532"`, Base Sepolia USDC address, integer atomic amount, recipient `payTo`, and single-use `nonce`. |
| `PaymentPayload` | Buyer Payment Client (`backend/buyer/payment_client.py`) | Seller Routes & Settlement Verifier | Header `X-402-Payment-Payload` / `PAYMENT-SIGNATURE` | **ALIGNED** — Includes EIP-712 `authorization` dict, hex ECDSA `signature`, and `buyer_address`. |
| `SettlementReceipt` | Seller Verifier (`backend/payments/settlement.py`) | Seller Routes & Buyer Ledger Recorder | Header `X-402-Settlement-Proof` / `PAYMENT-RESPONSE` | **ALIGNED** — Contains either on-chain `tx_hash` or facilitator `facilitator_receipt_id`. |
| `TaskCreationRequest` | Client / Frontend (`frontend/src/api/client.ts`) | Buyer Service (`backend/buyer/service.py`) | JSON Body (`POST /api/v1/buyer/tasks` & `/api/v1/tasks`) | **ALIGNED** — Supports `task` prompt, `budget_usdc`, and `max_budget_atomic` with validation. |
| `TaskResponse` | Buyer Service (`backend/buyer/routes.py`) | Frontend Dashboard (`frontend/src/pages/TaskDetail.tsx`) | JSON Body (`TaskDetailResponse` & legacy `TaskResponse`) | **ALIGNED** — Both canonical and legacy response shapes are fully supported. |
| `LedgerRecordSchema`| Ledger Repo (`backend/ledger/models.py`) | Frontend Audit View (`frontend/src/pages/Ledger.tsx`) | JSON Body (`GET /api/v1/ledger`) | **ALIGNED** — Fields `request_id`, `task_id`, `amount_paid`, `amount_paid_units`, `tx_hash`, `status`, `latency_ms` match. |

---

## 3. Status Enumeration Mapping & Semantics

To prevent state corruption, status vocabularies are strictly scoped:

### 3.1 Task Lifecycle Status (`TaskStatus`)
Defined in `backend/buyer/schemas.py`:
- `ACCEPTED`: Task received and persisted in database.
- `PLANNING`: Capability-aware planning and DAG generation underway.
- `RUNNING`: DAG step execution active.
- `COMPLETED`: All planned steps executed successfully.
- `COMPLETED_WITH_WARNINGS`: Primary objective fulfilled, but non-critical steps had safe fallbacks.
- `FAILED`: Critical task step failed or timed out.
- `REFUSED`: Task rejected prior to execution (e.g. insufficient budget).
- `PENDING_RECONCILIATION`: Indeterminate payment status requiring batch reconciliation.

### 3.2 Service Step Status (`CallStatus`)
Defined in `backend/buyer/schemas.py`:
- `CREATED` -> `AWAITING_PAYMENT` -> `EXECUTING` -> `VALIDATING_OUTPUT` -> `SUCCEEDED` / `PAID_OUTPUT_REJECTED` / `FAILED_AND_NOT_CHARGED`.

### 3.3 Terminal Ledger Status (`LedgerStatus`)
Defined in `backend/shared/constants.py`:
- `PAID` (`"paid"`): Confirmed payment evidence, successful service delivery.
- `PAID_OUTPUT_REJECTED` (`"paid output rejected"`): Confirmed payment evidence, but seller produced schema-invalid output.
- `REFUSED` (`"refused"`): Rejected prior to payment authorization.
- `FAILED_AND_NOT_CHARGED` (`"failed and not charged"`): Seller failed, timed out, or crashed before payment settled.

### 3.4 Internal Payment Status (`PaymentStatus`)
Defined in `backend/payments/schemas.py`:
- `NOT_STARTED`, `PAYMENT_REQUIRED`, `PENDING_PAYMENT`, `PAYMENT_SUBMITTED`, `SETTLED`, `SETTLEMENT_REJECTED`, `FAILED_AND_NOT_CHARGED`, `PENDING_RECONCILIATION`.

---

## 4. Monetary Arithmetic Invariants

1. **Internal Atomic Base Units:**
   All payments, budget locks, and balances are stored and manipulated as integers:
   `1 USDC = 1,000,000 atomic base units`.
2. **Display Representation:**
   Only formatted as human-readable string (e.g. `"0.002000 USDC"`) when rendered in UI or logs.
3. **Conversion Safeguard:**
   `backend/shared/constants.py` enforces Python's `Decimal` with `ROUND_HALF_UP` rounding to completely eliminate IEEE 754 floating-point inaccuracies.

---

## 5. Contract Audit Verdict

**VERIFIED BY CODE INSPECTION:** Zero contract discrepancies exist between shared definitions, subsystem models, and frontend client interfaces.
