# AGENTICA — PHASE 5 DURABLE PERSISTENCE & CRASH RECOVERY SPECIFICATION

**Phase:** 5.5 Durable Persistence and Crash Recovery  
**Status:** ACCEPTED  
**Date:** 2026-10-17  
**Module Owner:** Member 4 (`backend/database/`, `backend/ledger/`) & Member 1 (`backend/payments/`)  
**Evidence Classification:** VERIFIED BY AUTOMATED TESTS & VERIFIED BY CODE INSPECTION  

---

## 1. Executive Summary

This audit assesses the durable persistence layer and crash recovery mechanisms in AGENTICA. All 9 dedicated persistence, restart, and ledger tests passed cleanly (`9 passed in 0.28s`), verifying that critical system state survives application restarts, unhandled process terminations, and memory evictions.

Verified capabilities:
- **Zero-Loss Restart:** In-memory caches (`IdempotencyStore`, `BudgetManager`, `PaymentService._pending_reconciliations`) reliably reconstruct state from the underlying SQL database upon restart.
- **Replay Protection Post-Crash:** Spent nonces persisted in the database continue to be detected and rejected even if the server is rebooted between challenges.
- **Durable Suspense Hold:** Payment attempts in `PENDING_RECONCILIATION` survive restarts and are immediately recoverable via reconciliation endpoints.

---

## 2. Database Architecture & Models

The system uses SQLAlchemy 2.0 ORM with a unified configuration in `backend/database/session.py`.

### 2.1 Storage Configuration
- **Development & Test Default:** SQLite file database located at `local_data/ledger.db` (auto-created on startup).
- **Production Support:** Configurable via `DATABASE_URL` (e.g., `postgresql+psycopg2://user:pass@host:5432/agentica`).
- **Connection Engine:** Uses `connect_args={"check_same_thread": False}` for SQLite concurrency support with standard session pooling.

### 2.2 Primary Durable Tables
| Table Name | Model | Purpose | Primary Key |
|------------|-------|---------|-------------|
| `payment_attempts` | `PaymentAttemptModel` | Auditable history of every payment attempt, nonce, status, tx_hash, and raw proof | `attempt_id` |
| `budget_reservations` | `BudgetReservationModel` | Durable reservations locking funds per task | `reservation_id` |
| `ledger_records` | `LedgerRecordModel` | Immutable accounting journal of settled calls, latencies, and amounts | `record_id` |
| `buyer_tasks` | `BuyerTaskModel` | Task execution graphs, step statuses, and final outputs | `task_id` |

---

## 3. Crash Recovery Validation Across Key Interruption Points

Automated test `backend/tests/test_durable_persistence.py` simulates process death at critical lifecycle points:

### Point 1: Interruption During Payment Challenge (Nonce Recovery)
- **Failure:** Server crashes after issuing HTTP 402 challenge with nonce `nonce_restart_01`.
- **Test:** `test_nonce_replay_detection_across_simulated_process_restart`.
- **Outcome:** Clean `IdempotencyStore` instance instantiated without in-memory cache. Replaying `nonce_restart_01` queries the database and raises `ReplayAttackDetectedError`. **Replay attack is thwarted.**

### Point 2: Interruption After Execution (Idempotency Recovery)
- **Failure:** Server crashes after returning response for key `key_restart_01`.
- **Test:** `test_idempotency_recovery_across_simulated_process_restart`.
- **Outcome:** Fresh `IdempotencyStore` instantiated. Checking `key_restart_01` returns `is_new=False` and accurately serves the cached result from the database without re-executing seller code.

### Point 3: Interruption During Network Timeout (Suspense Recovery)
- **Failure:** Server crashes while a transaction is pending confirmation on Base Sepolia.
- **Test:** `test_pending_reconciliation_recovery_across_process_restart`.
- **Outcome:** Fresh `PaymentService` created. Querying `get_pending_reconciliations()` returns the suspended attempt from durable storage, ready for batch reconciliation.

---

## 4. Database Concurrency & Known Limitations

1. **SQLite Concurrency Limitation:**
   - In default local mode, SQLite utilizes file-level locking. While sufficient for single-process agent execution and developer workflows, high-throughput concurrent writes under multi-worker setups may encounter `database is locked` if timeouts are brief.
   - For multi-worker production deployments, PostgreSQL is required (`DATABASE_URL=postgresql://...`).
2. **Transaction Boundaries:**
   - Database operations use explicit `SessionLocal()` context managers with commits at atomic boundaries.
   - Budget operations commit reservation rows within the critical section to prevent inconsistent disk state.

---

## 5. Automated Test Evidence

```
backend/tests/test_durable_persistence.py::test_payment_attempt_model_crud PASSED
backend/tests/test_durable_persistence.py::test_budget_reservation_durable_lifecycle PASSED
backend/tests/test_durable_persistence.py::test_idempotency_recovery_across_simulated_process_restart PASSED
backend/tests/test_durable_persistence.py::test_nonce_replay_detection_across_simulated_process_restart PASSED
backend/tests/test_durable_persistence.py::test_pending_reconciliation_recovery_across_process_restart PASSED
backend/tests/test_durable_persistence.py::test_concurrent_budget_reservations_with_durable_storage PASSED
backend/tests/test_ledger.py::test_ledger_status_enum_values PASSED
backend/tests/test_ledger.py::test_ledger_insertion_and_query PASSED
backend/tests/test_ledger.py::test_reputation_metrics_computation PASSED
[9 passed in 0.28s]
```

**Gate Status:** PHASE 5 GATE D (ACCOUNTING AND RECOVERY - Persistence) — **PASSED**.
