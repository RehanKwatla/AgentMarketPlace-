# AGENTICA — PHASE 6 DATABASE PERSISTENCE & RECOVERY AUDIT

**Phase:** 6.3 Durable Storage and Database Deployment Verification  
**Status:** **ACCEPTED**  
**Date:** 2026-10-17  
**Module Owner:** Member 4 (`backend/database/`, `backend/ledger/`) & Member 1  
**Evidence Classification:** VERIFIED BY AUTOMATED TESTS & VERIFIED BY CODE INSPECTION  

---

## 1. Executive Summary

This audit establishes the durability, crash resilience, and deployment boundaries of AGENTICA's persistence layer. All 9 dedicated persistence, restart, and ledger tests passed cleanly (`9 passed in 0.29s`).

### Verified Durability Findings:
1. **Zero State Loss Across Restarts:** In-memory stores (`IdempotencyStore`, `BudgetManager`, `PaymentService._pending_reconciliations`) reliably reconstruct from durable SQLite tables when fresh instances are instantiated.
2. **Replay Invariance Across Crashes:** Nonces issued before an unexpected process termination remain recorded in `payment_attempts`; replaying an existing nonce in a new process instance triggers `ReplayAttackDetectedError`.
3. **Suspense Durability:** Payment attempts in `PENDING_RECONCILIATION` survive restarts and are immediately recoverable via `/api/v1/payments/reconcile-all`.
4. **Database Implementation Disclosure:**
   - **Local Development & Automated Tests:** Uses SQLite (`local_data/ledger.db`). **VERIFIED BY AUTOMATED TESTS**.
   - **Production Target:** PostgreSQL 16 supported via SQLAlchemy dialect and `docker-compose.yml`. Live tests against an external PostgreSQL cluster were **NOT RUN** in this offline pass.

---

## 2. Schema Architecture & Transaction Boundaries

In `backend/database/session.py` and `backend/payments/models.py`:
- SQLAlchemy 2.0 ORM with declarative models.
- Default engine configuration:
  ```python
  engine = create_engine(
      settings.database_url,
      connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
  )
  SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
  ```
- **Primary Tables:**
  - `payment_attempts`: Tracks attempt IDs, nonces, request hashes, statuses, raw proofs, and error codes.
  - `budget_reservations`: Tracks holds, committed amounts, and releases.
  - `ledger_records`: Immutable journal of completed service calls, latencies, amounts paid, and transaction proofs.
  - `buyer_tasks`: Root task states, prompts, and execution DAGs.

---

## 3. Crash Recovery Simulations (Isolated Test Scenarios)

The test suite in `backend/tests/test_durable_persistence.py` verifies process recovery:

### Scenario 1: Nonce Replay Across Clean Process Instance
- **Test:** `test_nonce_replay_detection_across_simulated_process_restart`
- **Result:** Fresh `IdempotencyStore` created with empty in-memory cache. Replayed nonce queries SQLite and raises `ReplayAttackDetectedError`.

### Scenario 2: Idempotency Recovery Across Clean Process Instance
- **Test:** `test_idempotency_recovery_across_simulated_process_restart`
- **Result:** Fresh `IdempotencyStore` instantiated. Checking existing key queries SQLite, detects matching hash, and returns cached result without re-executing.

### Scenario 3: Suspense Hold Recovery Across Restart
- **Test:** `test_pending_reconciliation_recovery_across_process_restart`
- **Result:** Fresh `PaymentService` created. Querying `get_pending_reconciliations()` accurately loads all suspended records from SQLite.

---

## 4. SQLite vs. PostgreSQL Deployment Guidance

| Characteristic | SQLite Default (`local_data/ledger.db`) | PostgreSQL (`agent_economy_db`) |
|---|---|---|
| **Intended Environment** | Local developer testing, offline demo, single-worker | Multi-worker containerized production |
| **Verification Level** | `VERIFIED BY AUTOMATED TESTS` | `DIALECT COMPATIBLE / CLUSTER NOT RUN` |
| **Concurrency Model** | File-level lock (suitable for single process) | Row-level locking & MVCC |
| **Connection Pooling** | `NullPool` / file handle | `QueuePool` with healthchecks |

---

## 5. Non-Destructive Backup & Recovery Procedures

1. **Scheduled Snapshot (MANDATORY BEFORE ANY MAINTENANCE):**
   - SQLite: `cp local_data/ledger.db local_data/ledger.db.bak.$(date +%s)`
   - PostgreSQL: `docker exec -t agent_economy_db pg_dump -U postgres agent_marketplace > backup_$(date +%s).sql`
2. **Routine Recovery:**
   - Always invoke `POST /api/v1/payments/reconcile-all` to resolve ambiguous payments.
   - **Zero Destructive Drops:** `DROP SCHEMA public CASCADE;` is strictly prohibited in routine operations.

---

## 6. Automated Test Evidence

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
[9 passed in 0.29s]
```

**Gate Status:** PHASE 6 GATE C (DURABLE STORAGE & PERSISTENCE) — **PASSED**.
