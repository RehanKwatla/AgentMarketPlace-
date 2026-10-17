# AGENTICA — PHASE 7 DATABASE DURABILITY AND CONCURRENCY AUDIT

**Project:** DI-06 — AGENTICA: Pay-per-Call Agent Economy  
**Tagline:** Discover. Pay. Execute. Trust.  
**Phase:** 7 (Stage 3 — Persistence and Database Concurrency Audit)  
**Date:** 2026-10-17  
**Module Owner:** Member 4 (`backend/ledger/`, `backend/database/`)  
**Evidence Classification:** `VERIFIED BY AUTOMATED TESTS` & `VERIFIED BY CODE INSPECTION`  

---

## 1. Executive Summary

This audit establishes the empirical persistence boundaries, crash recovery guarantees, and concurrency capabilities of AGENTICA across the three standardized recovery tiers:
- **Level 1 (Object Recreation):** Verified.
- **Level 2 (Process Restart):** Verified via independent subprocesses against an isolated SQLite file.
- **Level 3 (Multi-Process / Cloud PostgreSQL Concurrency):** **NOT RUN / UNTESTED** in live cloud infrastructure.

---

## 2. Recovery Level Breakdown & Verified Guarantees

### Level 1 — In-Memory Object Recreation
- **Test:** `test_idempotency_recovery_across_simulated_process_restart` and `test_nonce_replay_detection_across_simulated_process_restart`.
- **Mechanism:** Fresh instances of `IdempotencyStore` and `PaymentService` instantiated with empty in-memory caches successfully reload cached responses and consumed nonces from the underlying database session.
- **Result:** `VERIFIED BY AUTOMATED TESTS` (Passed).

### Level 2 — Genuine Process Restart
- **Test:** `test_genuine_subprocess_process_restart_recovery_level2` in `backend/tests/test_durable_persistence.py`.
- **Mechanism:**
  1. A separate child process (`sys.executable -c <writer_script>`) creates an isolated temporary SQLite database and commits:
     - Completed payment attempt (`status: paid`, cached response JSON)
     - Suspense payment attempt (`status: pending reconciliation`, error reason)
     - Active budget reservation (5,000 base units)
  2. Child process 1 closes all connections and terminates normally (`exit 0`).
  3. A second, completely independent child process (`sys.executable -c <reader_script>`) launches from a new OS process environment, attaches to the identical database file, and proves:
     - Exact idempotency hit returned (`is_new=False`, response cached).
     - Mutated payload with the same key raises `IdempotencyConflictError`.
     - Replay of the consumed nonce raises `ReplayAttackDetectedError`.
     - Suspense attempt is loaded by `PaymentService.get_pending_reconciliations()`.
     - Active reserved budget (5,000 units) is accurately recovered.
- **Result:** `VERIFIED BY AUTOMATED TESTS` (Passed in 5.76s).

### Level 3 — Multi-Process Concurrency / Cloud PostgreSQL Cluster
- **Mechanism:** Multiple distributed workers concurrently executing against a shared PostgreSQL database using row-level locking (`SELECT ... FOR UPDATE`).
- **Audit Finding:** SQLAlchemy model definitions in `backend/database/models.py` and `backend/payments/models.py` use ANSI SQL types compatible with PostgreSQL. Connection string configuration supports `postgresql+psycopg2://...`.
- **Empirical Status:** **NOT RUN / UNTESTED**. No live external PostgreSQL cluster was provisioned for this offline test run. Therefore, Level 3 is strictly documented as unverified to maintain evidence integrity.

---

## 3. Schema Models and Uniqueness Constraints

| Model Name | Table Name | Primary Key | Key Unique / Indexed Constraints | Durability Purpose |
|---|---|---|---|---|
| `PaymentAttemptModel` | `payment_attempts` | `attempt_id` (String 64) | Index: `idempotency_key`, `nonce`, `task_id`, `call_id` | Durably stores payment lifecycle state, nonces, and suspense holds across restarts |
| `BudgetReservationModel` | `budget_reservations`| `reservation_id` (String 64)| Index: `task_id`, `call_id`, `status` | Tracks atomic two-phase reservations and active holds per task |
| `LedgerRecordModel` | `ledger_records` | `request_id` (String 64) | Index: `payment_id`, `buyer_id`, `seller_id`, `tx_hash`, `status` | Immutable audit trail for financial settlements |
| `SellerReputationModel` | `seller_reputation` | `service_id` (String 64) | Index: `service_id` | Tracks rolling success rates, latency, volume, and sync status |

---

## 4. Audit Verdict

**STAGE 3 AUDIT STATUS: PASSED (LEVELS 1 & 2 VERIFIED / LEVEL 3 DISCLOSED AS NOT RUN)**  
Process-level durability across process restarts is empirically confirmed. Persistent SQLite storage ensures zero state loss of nonces, idempotency keys, budget reservations, and suspense records.
