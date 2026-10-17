# AGENTICA — PHASE 5 OBSERVABILITY & OPERATIONAL DIAGNOSTICS SPECIFICATION

**Phase:** 5.9 Observability, Audit Trail, and Operations  
**Status:** ACCEPTED  
**Date:** 2026-10-17  
**Module Owner:** Setup Lead / Shared Architecture & Member 4 (`backend/ledger/`)  
**Evidence Classification:** VERIFIED BY AUTOMATED TESTS & VERIFIED BY CODE INSPECTION  

---

## 1. Executive Summary

This document specifies the logging standards, correlation identifiers, diagnostic health endpoints, and credential redaction rules enforced across AGENTICA. The platform provides end-to-end trace correlation from initial buyer task dispatch to seller execution, settlement verification, and ledger journaling.

---

## 2. Distributed Tracing & Correlation Hierarchy

To trace operations across the buyer, registry, seller microservices, payment engine, and database, every operation carries a hierarchical set of correlation identifiers:

```
[Task Context]
  └── task_id: "task_<uuid>" (Root correlation across the multi-hop workflow)
        │
        ├── [Execution Step 1]
        │     ├── call_id: "call_scraping_01"
        │     ├── service_id: "scraping_001"
        │     ├── request_id / attempt_id: "req_<uuid>"
        │     ├── idempotency_key: "idem_<task_id>_<call_id>" (Hashed on-disk)
        │     └── settlement_proof: "rec_auth_<sig_hash>"
        │
        └── [Execution Step 2]
              ├── call_id: "call_data_01"
              ├── service_id: "data_001"
              ├── request_id / attempt_id: "req_<uuid>"
              └── settlement_proof: "rec_auth_<sig_hash>"
```

---

## 3. Secret Redaction & Logging Safety Rules

In accordance with project security rules:
1. **Zero Wallet Secrets:** Under no circumstance are `buyer_private_key`, `seller_private_key`, or wallet seed phrases logged or returned in error payloads.
2. **Zero Provider API Keys:** Vendor tokens (`GEMINI_API_KEY`, `GROQ_API_KEY`) are stripped by error sanitization decorators in `backend/sellers/base.py` before exception propagation.
3. **Redacted Idempotency Keys:** Payload arguments are recorded as SHA-256 hashes (`request_hash`) rather than logging unscrubbed customer inputs.
4. **Header Exposure Safety:** CORS middleware in `backend/main.py` explicitly exposes only public protocol headers (`X-402-Requirement`, `X-402-Payment-Payload`, `X-402-Settlement-Proof`, `Idempotency-Key`).

---

## 4. Diagnostics & Health Endpoints

### 4.1 Liveness and Readiness: `GET /health`
Returns system status, active version, network specification, and subsystem connectivity:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "network": "eip155:84532",
  "services": {
    "database": "connected",
    "registry": "active",
    "payment_engine": "configured"
  }
}
```

### 4.2 Suspense Inspection: `GET /api/v1/payments/pending-reconciliations`
Returns all active payment attempts held in suspense (`PENDING_RECONCILIATION`) awaiting settlement resolution.

### 4.3 Operational Recovery: `POST /api/v1/payments/reconcile-all`
Scans durable storage and triggers authoritative reconciliation checks against Base Sepolia RPC and facilitator endpoints, committing or releasing held budget reservations without human intervention.

---

## 5. Verification Evidence

```
backend/tests/test_health.py::test_health_endpoint PASSED
backend/tests/test_health.py::test_openapi_available PASSED
backend/tests/test_phase3_payment_hardening.py::test_reconcile_all_pending_batches_in_memory_and_durable PASSED
backend/tests/test_phase3_payment_hardening.py::test_reconcile_batch_route PASSED
```

**Gate Status:** PHASE 5 GATE H (OPERATIONS) — **PASSED**.
