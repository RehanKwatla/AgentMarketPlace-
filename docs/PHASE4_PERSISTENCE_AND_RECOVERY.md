# AGENTICA — PHASE 4 PERSISTENCE & RECOVERY AUDIT
**Document:** `docs/PHASE4_PERSISTENCE_AND_RECOVERY.md`  
**Date:** 17 October 2026  
**Auditor:** Member 4 (Database & Ledger Engineer)  
**Status:** COMPLETE (Stage 3 Master Plan)  
**Classification:** VERIFIED BY AUTOMATED TESTS & CODE INSPECTION  

---

## 1. Executive Summary

This document audits durable persistence and multi-process crash recovery across AGENTICA. The application uses SQLAlchemy 2.0 ORM with SQLite for local development and unit tests, and maintains full DDL compatibility for containerized PostgreSQL deployments.

### Core Architectural Guarantees
1. **Durable Ledger of Record:** All pay-per-call executions, settlement hashes, and monetary flows are persisted to relational database tables.
2. **Crash & Restart Recovery:** Payment attempts, budget reservations, and idempotent nonces survive clean and unclean process restarts.
3. **No Phantom Settlement:** Blockchain transactions and database state transitions are bounded by durable idempotency keys and suspense stores, preventing duplicate executions across restarts.

---

## 2. Relational Schema Architecture

```
┌─────────────────────────┐          ┌─────────────────────────┐
│     services (DDL)      │          │       tasks (DDL)       │
├─────────────────────────┤          ├─────────────────────────┤
│ service_id (PK, String) │          │ task_id (PK, String)    │
│ name (String)           │          │ task_prompt (Text)      │
│ category (String)       │          │ budget_usdc (String)    │
│ endpoint_url (String)   │          │ total_cost_usdc (String)│
│ price_usdc (String)     │          │ status (String)         │
│ price_base_units (Int)  │          │ created_at (DateTime)   │
│ is_active (Boolean)     │          └────────────┬────────────┘
└─────────────────────────┘                       │ 1:N
                                                  ▼
┌─────────────────────────┐          ┌─────────────────────────┐
│  seller_reputation      │          │     ledger_records      │
├─────────────────────────┤          ├─────────────────────────┤
│ service_id (PK, String) │          │ request_id (PK, String) │
│ total_calls (Int)       │          │ task_id (Index, String) │
│ successful_calls (Int)  │          │ payment_id (String)     │
│ success_rate (Float)    │          │ buyer_id (String)       │
│ median_latency_ms (Flt) │          │ seller_id (String)      │
│ reputation_score (Float)│          │ service_id (String)     │
│ total_volume_units (Int)│          │ amount_paid_units (Int) │
│ total_volume_usdc (Str) │          │ tx_hash (String)        │
│ sync_status (String)    │          │ status (String)         │
│ updated_at (DateTime)   │          │ timestamp (DateTime)    │
└─────────────────────────┘          └─────────────────────────┘

┌─────────────────────────┐          ┌─────────────────────────┐
│    payment_attempts     │          │   budget_reservations   │
├─────────────────────────┤          ├─────────────────────────┤
│ attempt_id (PK, String) │          │ reservation_id (PK, Str)│
│ idempotency_key (Unique)│          │ task_id (Index, String) │
│ nonce (Unique, String)  │          │ call_id (Index, String) │
│ request_hash (String)   │          │ amount_base_units (Int) │
│ amount_units (Int)      │          │ status (String)         │
│ status (String)         │          │ created_at (DateTime)   │
│ tx_hash (String)        │          │ updated_at (DateTime)   │
│ settlement_proof (Text) │          └─────────────────────────┘
│ created_at (DateTime)   │
│ updated_at (DateTime)   │
└─────────────────────────┘
```

---

## 3. Transaction Safety & ACID Guarantees

1. **Uniqueness Constraints:**
   - `payment_attempts.idempotency_key`: Prevents concurrent insertion of duplicate payment requests.
   - `payment_attempts.nonce`: Enforces cryptographic single-use nonces at the database level.
   - `ledger_records.request_id`: Guarantees idempotency of audit log records.
2. **Atomic Ledger Inconsistency Checks:**
   `LedgerRepository.record_transaction()` validates existing records with the same `request_id`:
   - Checks that `service_id`, `buyer_id`, `seller_id`, and `amount_paid` match.
   - If inconsistent payload is submitted for an existing request ID, it raises `LedgerInconsistencyError`.
3. **Thread Safety & Multi-Worker Concurrency:**
   - `LedgerRepository` uses `threading.RLock()` for thread-safe in-memory cache synchronization.
   - Database sessions use scoped session contexts (`with SessionLocal() as session:`) with explicit commit/rollback semantics.

---

## 4. Recovery Scenarios & Test Evidence

### 4.1 Process Restart During Payment Flow
- **Mechanism:** On startup, `PaymentService` hydrates pending attempts from `payment_attempts` table where `status == PaymentStatus.PENDING_RECONCILIATION`.
- **Budget Locking:** Active reservations (`status == 'reserved'`) are aggregated to prevent overdrawing upon service restart.

### 4.2 Test Verification Matrix (`backend/tests/test_durable_persistence.py`)
| Test Case | Scenario Verified | Result |
|---|---|---|
| `test_payment_attempt_durable_persistence` | Payment attempt, nonce, and settlement proof survive repository re-instantiation | **PASSED** |
| `test_budget_reservation_durable_lifecycle` | Budget reservation transitions (`reserved` -> `committed` -> `released`) persist durably | **PASSED** |
| `test_idempotency_recovery_across_process_restart` | New `IdempotencyStore` instance accurately detects cached response from disk | **PASSED** |
| `test_budget_manager_recovery_active_reservations` | New `BudgetManager` instance recovers active reservations and enforces balance ceiling | **PASSED** |
| `test_payment_service_hydration_on_startup` | `PaymentService` hydrates pending reconciliation attempts on boot | **PASSED** |
| `test_concurrent_payment_attempt_uniqueness` | Duplicate idempotency key insertion raises database uniqueness violation | **PASSED** |

All 6 durable persistence tests execute cleanly and verify multi-process restart integrity.
