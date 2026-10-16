# MEMBER 4: LEDGER & REPUTATION ENGINE (`backend/ledger/`)

**Assigned Owner:** Member 4 (Ledger, Dashboard & Deployment Engineer)  
**Assigned Git Branch:** `feature/dashboard-ledger`  
**Status:** `[DEFINED INTERFACES & AUDIT FOUNDATION]`

---

## 📋 Responsibilities Checklist

- [ ] **Persistent Payment Ledger (`models.py`, `backend/database/`):**
  - Implement ledger repository persisting every service invocation.
  - Required fields: `request_id`, `timestamp`, `buyer_id`, `seller_id`, `service_id`, `listed_price`, `amount_paid`, `tx_hash`, `status`, `latency_ms`, `error_reason`.
  - Strictly enforce terminal statuses:
    - `paid`
    - `paid output rejected`
    - `refused`
    - `failed and not charged`
- [ ] **Provider Reputation Metrics (`reputation.py`):**
  - Compute: total calls, success rate, median latency, failure counts, schema violation counts.
  - Reputation score formula weighting reliability, speed, and schema fidelity.
  - Used by Member 3's `ServiceSelector` to route buyer requests dynamically.
- [ ] **Settlement Reconciliation (`reconciliation.py`):**
  - Reconcile in-flight requests and unresolved transaction hashes with Facilitator or Base Sepolia RPC.
- [ ] **Ledger & Reputation Routes (`routes.py`):**
  - `GET /api/v1/ledger`: Query audit records with status/service filtering.
  - `GET /api/v1/ledger/{request_id}`: Retrieve single transaction receipt.
  - `GET /api/v1/reputation`: Overall provider scores.
  - `GET /api/v1/reputation/{service_id}`: Provider-specific scorecard.
- [ ] **Ledger Tests (`backend/tests/test_ledger.py`):**
  - Test insertion of records.
  - Test status enum constraints.
  - Test reputation calculation math.
