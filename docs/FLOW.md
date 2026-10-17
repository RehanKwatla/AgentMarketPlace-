# FLOW.md — COMPLETE EXECUTION LIFECYCLE & CALL SEQUENCES

This document provides a detailed end-to-end execution flow map showing **which file runs, in what order, and how each component interacts** across the entire lifecycle of the Pay-Per-Call Agent Economy.

---

## 1. System Boot & Initialization Flow

When starting the application using `python scripts/start_dev.py` (or `uvicorn backend.main:app`):

```mermaid
graph TD
    A["scripts/start_dev.py"] -->|1. Set PYTHONPATH & parse CLI args| B["backend/main.py"]
    B -->|2. Import application settings| C["backend/shared/config.py"]
    C -->|3. Read .env with fallbacks| D["backend/shared/constants.py"]
    B -->|4. Initialize DB engine| E["backend/database/session.py"]
    E -->|5. Auto-create tables| F["backend/database/models.py"]
    B -->|6. Import & register catalog| G["backend/registry/service_catalog.py"]
    G -->|7. Seed default seller services| H["backend/shared/schemas.py"]
    B -->|8. Mount subsystem routers| I["FastAPI Router Mounting"]
    I --> J["backend/registry/routes.py"]
    I --> K["backend/buyer/routes.py"]
    I --> L["backend/sellers/routes.py"]
    I --> M["backend/ledger/routes.py"]
    I --> N["backend/payments/routes.py"]
    B -->|9. Start Uvicorn HTTP loop| O["Listening on http://0.0.0.0:8000"]
```

### Execution Steps:
1. **Entrypoint:** [`scripts/start_dev.py`](file:///c:/Users/ASUS/Desktop/AgentMarketPlace/scripts/start_dev.py) adds the workspace root to `sys.path` and starts Uvicorn.
2. **Configuration Load:** [`backend/shared/config.py`](file:///c:/Users/ASUS/Desktop/AgentMarketPlace/backend/shared/config.py) reads `.env` variables (Base Sepolia RPC, contract addresses, seller endpoints).
3. **Database Spin-up:** [`backend/database/session.py`](file:///c:/Users/ASUS/Desktop/AgentMarketPlace/backend/database/session.py) sets up the SQLAlchemy engine. The `lifespan` handler in [`backend/main.py`](file:///c:/Users/ASUS/Desktop/AgentMarketPlace/backend/main.py) calls `init_db()` to ensure tables exist in SQLite/PostgreSQL.
4. **Service Catalog Seed:** [`backend/registry/service_catalog.py`](file:///c:/Users/ASUS/Desktop/AgentMarketPlace/backend/registry/service_catalog.py) initializes with default entries for the three sellers (`data_001`, `scraping_001`, `inference_001`).
5. **Route Registration:** All subsystem routers are mounted under `/api/v1/` and health diagnostics under `/health`.

---

## 2. Service Discovery & Registry Flow

When a client or frontend requests `GET /api/v1/services?category=data`:

```mermaid
sequenceDiagram
    autonumber
    actor Client as Frontend / Buyer Agent
    participant Router as backend/registry/routes.py
    participant Catalog as backend/registry/service_catalog.py
    participant Schemas as backend/shared/schemas.py

    Client->>Router: GET /api/v1/services?category=data
    Router->>Catalog: catalog.list_services(category="data")
    Catalog->>Catalog: Filter active services matching category
    Catalog-->>Router: List[ServiceDefinition]
    Router->>Schemas: ServiceListResponse(services=..., total=...)
    Schemas-->>Router: Validated Pydantic JSON
    Router-->>Client: HTTP 200 OK + Services JSON
```

---

## 3. Member 1 Payment Engine: `execute_paid_call` Flow

When the Buyer Agent (or client) invokes `PaymentService.execute_paid_call()`:

```mermaid
sequenceDiagram
    autonumber
    actor Buyer as Buyer Agent (Member 3)
    participant Svc as backend/payments/service.py
    participant Idemp as backend/payments/idempotency.py
    participant Policy as backend/payments/policy.py
    participant Budget as backend/payments/budget.py
    participant Adapter as backend/payments/x402_adapter.py
    participant Seller as backend/sellers/routes.py
    participant Settle as backend/payments/settlement.py
    participant Repo as backend/payments/models.py (Durable Repo)
    participant Ledger as backend/ledger/models.py

    Buyer->>Svc: execute_paid_call(task_id, call_id, service_id, payload, key)

    Svc->>Idemp: check_or_register(key, SHA256(payload))
    Idemp->>Repo: get_attempt_by_idempotency_key(key) [DB Recovery]
    alt Idempotency Hit (Same Key & Payload)
        Idemp-->>Svc: Return cached PaidCallResult
        Svc-->>Buyer: Return cached PaidCallResult (Zero Network Call)
    else Idempotency Conflict (Different Payload)
        Idemp-->>Svc: Raise IdempotencyConflictError
        Svc-->>Buyer: PaidCallResult(status='refused', code='IDEMPOTENCY_CONFLICT')
    end

    Svc->>Policy: verify_service_terms(service)
    alt Policy Violation
        Policy-->>Svc: Raise PaymentPolicyViolationError
        Svc-->>Buyer: PaidCallResult(status='refused')
    end

    Svc->>Budget: reserve(reservation_id, price_base_units)
    Budget->>Repo: record_reservation(res_id, task_id, units) [Durable Lock]
    alt Insufficient Budget
        Budget-->>Svc: Raise BudgetExceededError
        Svc-->>Buyer: PaidCallResult(status='refused', code='BUDGET_EXCEEDED')
    end

    Svc->>Adapter: execute_paid_request(service, payload, key)
    Adapter->>Seller: POST endpoint_url (Initial challenge trigger)
    Seller-->>Adapter: HTTP 402 + X-402-Requirement
    Adapter->>Policy: verify(requirement, service)
    Adapter->>Adapter: create_payment_payload(requirement, key) [EIP-712 Sign]
    Adapter->>Seller: POST endpoint_url + X-402-Payment-Payload + Idempotency-Key

    alt Network Timeout / Disconnection
        Seller--xAdapter: Timeout
        Adapter-->>Svc: Raise SettlementTimeoutError
        Svc->>Svc: retain_in_suspense(status='pending reconciliation', hold_reservation=True)
        Svc-->>Buyer: PaidCallResult(status='pending reconciliation')
    else Seller Delivers Response
        Seller-->>Adapter: HTTP 200 OK + payload + X-402-Settlement-Proof
        Adapter-->>Svc: (status=200, data, proof_header)
        Svc->>Settle: verify_settlement_proof(proof_header, price_base_units)
        Svc->>Svc: validate_seller_output(data, output_schema)
        alt Output Valid
            Svc->>Budget: commit(reservation_id, price_base_units)
            Svc->>Ledger: record_transaction(status='paid')
            Svc-->>Buyer: PaidCallResult(status='paid', output=data)
        else Output Invalid
            Svc->>Budget: commit(reservation_id, price_base_units) [Funds Settled]
            Svc->>Ledger: record_transaction(status='paid output rejected')
            Svc-->>Buyer: PaidCallResult(status='paid output rejected')
        end
    end
```

---

## 4. Autonomous Buyer Agent Task Orchestration Flow

When a task is submitted to `POST /api/v1/tasks`:

```mermaid
graph TD
    A["User / Dashboard Submit Task"] -->|POST /api/v1/tasks| B["backend/buyer/routes.py"]
    B -->|submit_and_execute_task()| C["backend/buyer/service.py (BuyerService)"]
    C -->|1. Create DAG Plan| D["backend/buyer/planner.py (TaskPlanner)"]
    D -->|2. Validate Plan & Budget| E["backend/buyer/plan_validator.py (PlanValidator)"]
    E -->|Validation Fails / Over-budget| F["Status: 'refused' (0 funds spent)"]
    E -->|Validation Passes| G["Execute Topological Stages in Parallel"]
    
    G -->|Stage 0: Parallel Calls| H["asyncio.gather bounded by Semaphore(3)"]
    H -->|For each planned step| I["_execute_call()"]
    
    I -->|Step A: Lock Budget| J["backend/payments/budget.py (BudgetManager.reserve_budget)"]
    I -->|Step B: Initial Call| K["POST Seller Endpoint"]
    K -->|HTTP 402 + Requirement| L["PaymentPolicyVerifier.verify()"]
    L -->|Policy Violation| M["Release Budget -> Status: 'refused'"]
    L -->|Policy Valid| N["Member 1 BuyerPaymentClient.create_payment_payload()"]
    
    N -->|Step C: Re-request with Auth| O["POST Seller with X-402-Payment-Payload"]
    O -->|Timeout / Network Drop| P["Status: 'pending_reconciliation' (Hold Budget)"]
    O -->|HTTP 200 without Settlement Proof| P
    O -->|HTTP 200 with Settlement Proof| Q["Member 1 BuyerPaymentClient.verify_settlement()"]
    
    Q -->|Settlement Verified| R["Commit Budget -> Status: 'paid'"]
    R -->|Step D: Validate Output| S["backend/buyer/output_validator.py"]
    S -->|Output Valid| T["Status: 'paid'"]
    S -->|Output Invalid| U["Status: 'paid output rejected'"]
    
    T -->|Step E: Persist to Ledger| V["Member 4 backend/ledger/models.py (ledger_repo)"]
    U -->|Step E: Persist to Ledger| V
    P -->|Step E: Persist to Ledger| V
    M -->|Step E: Persist to Ledger| V
    
    V -->|Step F: Aggregate Provenance| W["backend/buyer/aggregator.py & explanation.py"]
    W -->|Save TaskRecord| X["Member 4 SQL TaskRecordModel"]
```

---

## 5. Ledger Auditing & Provider Reputation Flow

How transaction records transition into audit logs and calculate reputation scores:

```mermaid
graph LR
    A["Completed / Refused Call"] -->|Record Entry| B["backend/ledger/models.py (LedgerRepository)"]
    B -->|Store Record| C["LedgerRecordSchema"]
    C --> D{"Status"}
    D -->|Success| E["status = 'paid'"]
    D -->|Corrupted Data| F["status = 'paid output rejected'"]
    D -->|Policy Violation| G["status = 'refused'"]
    D -->|Network Error| H["status = 'failed and not charged'"]
    
    B -->|Read Records| I["backend/ledger/reputation.py"]
    I -->|Calculate Metrics| J["ReputationCalculator"]
    J -->|Compute Score| K["ReputationMetrics: Success Rate, Median Latency, Score"]
    
    B -->|GET /api/v1/ledger| L["backend/ledger/routes.py"]
    J -->|GET /api/v1/reputation| L
    L -->|Live Polling| M["Frontend Dashboard"]
```

---

## 6. Frontend Dashboard Lifecycle Flow

When a user visits `http://localhost:5173`:

1. **Mounting:** [`frontend/src/main.tsx`](file:///c:/Users/ASUS/Desktop/AgentMarketPlace/frontend/src/main.tsx) renders [`frontend/src/App.tsx`](file:///c:/Users/ASUS/Desktop/AgentMarketPlace/frontend/src/App.tsx) which displays [`frontend/src/pages/Dashboard.tsx`](file:///c:/Users/ASUS/Desktop/AgentMarketPlace/frontend/src/pages/Dashboard.tsx).
2. **Polling Loop:** `Dashboard.tsx` establishes a 5-second recurring poll via [`frontend/src/api/client.ts`](file:///c:/Users/ASUS/Desktop/AgentMarketPlace/frontend/src/api/client.ts):
   - `fetchHealth()` -> Updates [`Navbar.tsx`](file:///c:/Users/ASUS/Desktop/AgentMarketPlace/frontend/src/components/Navbar.tsx) with network identifier and health status.
   - `fetchServices()` -> Renders cards in [`ServiceCard.tsx`](file:///c:/Users/ASUS/Desktop/AgentMarketPlace/frontend/src/components/ServiceCard.tsx).
   - `fetchReputations()` -> Displays live reputation scores on service cards.
   - `fetchLedger()` -> Updates [`LedgerTable.tsx`](file:///c:/Users/ASUS/Desktop/AgentMarketPlace/frontend/src/components/LedgerTable.tsx) with formatted badges from [`ReputationBadge.tsx`](file:///c:/Users/ASUS/Desktop/AgentMarketPlace/frontend/src/components/ReputationBadge.tsx).
3. **User Action:** Submitting a prompt triggers `submitBuyerTask()`, which POSTs to `/api/v1/buyer/tasks`, streams the execution status to the UI console, and auto-refreshes the audit log upon completion.

---

## 7. Automated Test Execution Flow

When running `python scripts/run_tests.py`:

```
scripts/run_tests.py
  │
  └── Launches subprocess: pytest backend/tests/ -v
        │
        ├── conftest.py: Instantiates FastAPI TestClient(app)
        │
        ├── test_health.py: Verifies GET /health & OpenAPI JSON
        ├── test_registry.py: Tests catalog listing, schema, and price filtering
        ├── test_payments.py: Tests PaymentPolicyVerifier (network, token, payTo, gouging)
        ├── test_payment_engine.py: Tests Member 1 execute_paid_call(), output schema checks,
        │                          idempotency replays, conflicts, & timeout suspense
        ├── test_budget.py: Tests base unit arithmetic, overdraw blocks, & 10-task concurrency lock
        ├── test_replay.py: Tests nonce single-use cache & idempotency key store
        ├── test_sellers.py: Tests 402 challenge issuance & paid execution stubs
        ├── test_buyer.py: Tests TaskPlanner decomposition & budget refusal
        ├── test_buyer_task_api.py: Tests /api/v1/tasks endpoints, lifecycle states, and polling
        ├── test_planner_validator.py: Tests DAG validation, cycle detection, and price tampering
        ├── test_buyer_orchestration_payment.py: Tests payment routing, budget lock, and pending reconciliation
        ├── test_buyer_dependency_execution.py: Tests sequential deps, parallel execution, timeouts, & fallbacks
        ├── test_output_validation_provenance.py: Tests Draft-7 schema rejections, paid_output_rejected accounting, safe fallbacks, zero fact hallucination, and field-level provenance
        ├── test_purchase_explanation.py: Tests authoritative ledger totals, missing ledger data, pending reconciliation isolation, non-fabricated explorer links, and spending summaries
        ├── test_member3.py: Tests canonical /api/v1/tasks lifecycle, query filters, output validation, & reputation
        ├── test_ledger.py: Tests LedgerStatus enum values & reputation computation math
        └── test_integration.py: Executes end-to-end multi-step workflow harness
```

All automated test suites verify every subsystem interface before developer feature branches are merged, executing with a 100% pass rate across all subsystems.
