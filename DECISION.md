# DECISION.md — ARCHITECTURAL & ENGINEERING DECISION RECORDS (ADR)

This document explains the theory, engineering logic, trade-offs, and operational mechanisms behind all key architectural decisions made by the AI Architect for the **DI-06 Pay-Per-Call Agent Economy**.

---

## Decision 1: Four-Member Isolated Modular Architecture

### 1. Context & Problem
In a 24-hour hackathon with four developers, the most common catastrophic failure mode is merge conflicts on shared files (`main.py`, router files, database models) and interface drift (one developer changes an endpoint signature while another is coding against the old one).

### 2. Theory & Logic
- **Conway's Law & Interface-Driven Design:** The software architecture should mirror the team structure.
- By defining all shared schemas (`backend/shared/schemas.py`) and API contracts (`docs/API_CONTRACTS.md`) *before* implementation begins, the contracts become an immutable protocol.
- Each developer owns one isolated subsystem:
  - Member 1: `backend/payments/`
  - Member 2: `backend/sellers/`
  - Member 3: `backend/buyer/` & `backend/registry/`
  - Member 4: `backend/ledger/`, `backend/database/`, `frontend/`
  - Setup Lead: `backend/shared/`, root configs, central mounting.

### 3. How It Works
- Developers work on isolated feature branches (`feature/payments`, etc.).
- No developer touches code in another developer's directory without coordination.
- Shared contracts are frozen on `main` and pulled into feature branches via standard Git merges.

---

## Decision 2: Official x402 v2 Standard over Custom Simulation

### 1. Context & Problem
Developers under tight deadlines often mock payments using dummy JSON fields (e.g. `{"paid": true, "tx": "0x1234"}`). This violates the DI-06 hackathon rules and fails live evaluation.

### 2. Theory & Logic
- The **x402 payment standard** extends standard HTTP semantics using `402 Payment Required` to request programmatic payments across blockchain networks using CAIP-2 identifiers and EIP-712 signatures.
- Standard HTTP headers must be used:
  - `X-402-Requirement` (Challenge issued by seller)
  - `X-402-Payment-Payload` (Authorization signed by buyer)
  - `X-402-Settlement-Proof` (Settlement receipt returned by seller)

### 3. How It Works
- When a buyer hits a seller endpoint without payment headers, the seller emits HTTP 402 with `X-402-Requirement` containing network `eip155:84532`, token address, exact base unit price, and a unique challenge nonce.
- The buyer verifies policy, signs payment authorization, and repeats the request with `X-402-Payment-Payload`.
- Seller verifies via Facilitator / RPC, settles funds, executes business logic, and attaches `X-402-Settlement-Proof`.

---

## Decision 3: Integer USDC Base Unit Arithmetic (No Floating-Point Math)

### 1. Context & Problem
IEEE 754 floating-point numbers (`float` in Python/JavaScript) cannot represent all decimal fractions accurately. For example, in Python:
```python
0.1 + 0.2 == 0.30000000000000004  # True!
```
In financial applications, micro-cents accumulate rounding discrepancies, causing balance reconciliations to fail and budget checks to produce false positives/negatives.

### 2. Theory & Logic
- USDC smart contracts on Base Sepolia define 6 decimal places.
- 1.000000 USDC = 1,000,000 integer base units.
- Operating exclusively on integer base units guarantees exact arithmetic without precision loss.

### 3. How It Works
- `usdc_to_base_units(amount)` uses Python's `Decimal` with `ROUND_HALF_UP` to convert decimal strings to exact integer base units.
- All internal balances, quotas, reservations, and prices are stored and calculated as integers.
- `base_units_to_usdc(units)` formats integers back to standard 6-decimal strings only for external presentation.

---

## Decision 4: Concurrency-Safe Atomic Budget Reservations via Mutex Locks

### 1. Context & Problem
The system must support at least 3 concurrent requests executing in parallel. If three concurrent tasks each check available budget before reserving it without synchronization:
- Initial budget: 5,000 units.
- Task A checks: 5,000 available (needs 3,000) -> OK.
- Task B checks: 5,000 available (needs 3,000) -> OK.
- Both proceed and spend 6,000 units -> **Budget Overdrawn (TOCTOU Race Condition)**.

### 2. Theory & Logic
- **Two-Phase Reservation Pattern:**
  1. *Phase 1 (Reserve):* Atomically decrement available funds and allocate to in-flight reservation ID.
  2. *Phase 2 (Commit or Release):* If call succeeds, commit funds to spent balance; if call fails or is refused, restore reserved funds to available balance.

### 3. How It Works
- `BudgetManager` uses `asyncio.Lock()` to serialize reservation operations.
- Parallel worker coroutines enter critical section sequentially; if funds are insufficient, `BudgetExceededError` is raised immediately before any network call or payment authorization is issued.
- Verified by unit test `test_concurrent_budget_reservations` in `backend/tests/test_budget.py`.

---

## Decision 5: Four-State Terminal Payment Ledger

### 1. Context & Problem
Binary transaction statuses (`SUCCESS` / `FAILED`) fail to capture the nuances of decentralized micropayments:
- What if payment settled on-chain, but the seller's server crashed or returned corrupt data?
- What if the buyer refused the call because the seller quoted an unauthorized price?

### 2. Theory & Logic
Four explicit terminal states provide complete transparency and accountability:
1. `paid`: Payment settled + seller delivered valid data conforming to schema.
2. `paid output rejected`: Payment settled, but seller returned invalid/corrupted payload. (Used to penalize seller reputation).
3. `refused`: Pre-flight check rejected the transaction before funds were authorized or spent (price gouging, wrong network, insufficient budget).
4. `failed and not charged`: Downstream network timeout or execution crash occurred before settlement (zero loss to buyer).

### 3. How It Works
- Defined as enum `LedgerStatus` in `backend/shared/constants.py`.
- Recorded in `LedgerRecordSchema` and mapped directly into persistent database models and dashboard UI badges.

---

## Decision 6: Output Schema Validation Prior to State Finalization

### 1. Context & Problem
In an open agent marketplace, seller agents could return empty objects `{}`, truncated strings, or error text while returning HTTP 200, effectively stealing buyer micro-payments.

### 2. Theory & Logic
- **Zero-Trust Client Architecture:** An HTTP 200 code with a settlement proof only proves delivery of *an* HTTP response, not *correct* service fulfillment.
- Buyer validates the response against the seller's registered JSON schema (`output_schema`).

### 3. How It Works
- The buyer agent inspects returned data against the registered schema.
- If fields are missing or malformed, the transaction transitions to `paid output rejected` and the reputation engine slashes the seller's reliability score.

---

## Decision 7: Dual Database Engine (PostgreSQL + SQLite Fallback)

### 1. Context & Problem
Developers on Windows/Mac may not have PostgreSQL or Docker installed initially. Requiring an external database just to run unit tests creates setup friction.

### 2. Theory & Logic
- **12-Factor App Portability:** Database connectivity abstracted behind SQLAlchemy ORM.
- If `DATABASE_URL` starts with `sqlite:`, the engine enables SQLite-specific connection arguments (`check_same_thread=False`) and auto-creates directory `./local_data/`.
- If `DATABASE_URL` points to PostgreSQL (e.g. in Docker Compose), it connects with pool pre-ping.

### 3. How It Works
- Tested and verified: unit tests run instantaneously in SQLite mode without external services.
- Production/Docker runs against PostgreSQL with zero code changes.

---

## Decision 8: Zero Private Keys in Frontend (Client Security)

### 1. Context & Problem
Frontend single-page applications (SPAs) bundle JavaScript that is readable by any client. Storing buyer private keys or signing keys in React code is an immediate security vulnerability.

### 2. Theory & Logic
- **Stateless Read-Only Dashboard:** The web UI is strictly an observer and command trigger.
- The dashboard communicates with the backend via authenticated/CORS-enabled REST endpoints.
- All wallet credentials, Base Sepolia private keys, and EIP-712 signers reside exclusively in the backend server memory (`backend/payments/`).

### 3. How It Works
- `frontend/src/api/client.ts` calls backend routes.
- No cryptographic libraries or private keys are present in `frontend/package.json`.

---

## Decision 9: Separation of Task Creation from Payment Execution & Model Alignment

### 1. Context & Problem
Premature payment execution upon task submission violates the principle of least privilege and atomic budgeting. If task parsing fails or budget constraints are violated during decomposition, any upfront payment is lost or requires complex refund reconciliation. Furthermore, multiple team members creating independent database tables leads to schema collisions.

### 2. Theory & Logic
- **Decoupled Planning vs. Execution:** Creating a task (`POST /api/v1/tasks`) with `execute_now: false` admits the request, verifies input syntax, converts budget to integer USDC atomic units without floats, and sets status to `accepted`.
- **Member 4 Model Alignment:** Uses Member 4's single source of truth `TaskRecordModel` via SQLAlchemy ORM rather than introducing conflicting buyer tables.
- **Verification Gates:** A task cannot reach `completed` until the service outputs pass strict Draft-7 JSON schema validation against the registered seller schema. If output fails, the task state transitions to `refused` or `failed` with zero funds committed for non-conforming responses.

### 3. How It Works
- `TaskRepository` persists task state to `TaskRecordModel`.
- `BuyerService` coordinates atomic budget reservation with Member 1's `BudgetManager`.
- Provenance and purchase explanation records capture all seller receipts and tx hashes transparently.

---

## Decision 10: Deterministic-First DAG Planner, Hard Eligibility Gating, and Pre-Payment Plan Validation

### 1. Context & Problem
In agentic commerce systems, planning without validation leads to hallucinated endpoints, budget overruns, cycles in execution graphs, and payment commitments for invalid or disabled services. Allowing a candidate's high reputation or low price to override a safety failure introduces critical vulnerabilities.

### 2. Theory & Logic
- **Hard Eligibility Gating (Gated Ranking):** A candidate service is never ranked unless it passes ALL hard eligibility gates first: active/enabled status, trusted registry origin, valid 42-char hex `pay_to` address, Base Sepolia network (`eip155:84532`), Base Sepolia USDC token (`0x036CbD53842c5426634e7929541eC2318f3dCF7e`), positive atomic price within budget, and valid Draft-7 input/output schemas. A high ranking never overrides an eligibility check.
- **Explicit DAG Architecture:** Multi-step workflows requiring Scraping, Data, and Inference are modeled as explicit Directed Acyclic Graphs (DAGs) partitioned into topological execution stages. Independent tasks (e.g. Scraping and Data) execute in parallel in Stage 0, while dependent tasks (e.g. Inference summarizing upstream data) execute in Stage 1.
- **Authoritative Price Enforcement:** All prices, recipient addresses, and endpoints are resolved strictly from server-side registry records. Any client-provided prices or payment parameters are discarded.
- **Worst-Case Pre-Computation:** Calculates worst-case total cost, including permitted fallbacks and allowances, before any paid call or budget reservation.
- **Zero Payments on Plan Rejection:** If a plan contains missing dependencies, cycles, schema mismatches, duplicate calls, unsafe concurrency, or exceeds budget, it is rejected immediately and transitions to `refused` before any payment interface is invoked.

### 3. How It Works
- `ServiceSelector.check_eligibility()` filters candidates, and `rank_candidates()` scores remaining eligible candidates via multi-attribute utility (relevance 30%, reputation 35%, price 25%, latency 10%).
- `TaskPlanner.create_plan()` generates an `ExecutionPlan` with dependency graph, topological stages, expected and worst-case cost, fallback allowances, and selection reasons.
- `PlanValidator.validate_plan()` rigorously checks DAG acyclicity, schema compliance via `Draft7Validator`, authoritative server-side registry resolution, and concurrency limits.

---

## Decision 11: End-to-End Orchestration Integration with Member 1 Payments & Member 4 Persistence

### 1. Context & Problem
The Buyer agent cannot operate in a silo. Every paid invocation must interface with Member 1's payment engine (`BuyerPaymentClientInterface`, `PaymentPolicyVerifier`, `BudgetManager`, `SettlementVerifier`) and record immutable transaction history in Member 4's ledger repository (`ledger_repo` and SQLAlchemy `LedgerRecordModel`). Crucially:
1. The buyer module must never sign transactions directly or implement competing replay protection.
2. Concurrent eligible calls ($\ge 3$) must be supported without exceeding budget.
3. Network timeouts or missing settlement proofs after dispatching payment payloads introduce settlement uncertainty; blind retries could result in double-spending.

### 2. Theory & Logic
- **Delegated Cryptographic Authorization:** The buyer layer (`BuyerService`) never handles private keys or signs transactions directly. Instead, it delegates payload creation to `BuyerPaymentClientInterface.create_payment_payload` and settlement verification to `BuyerPaymentClientInterface.verify_settlement`.
- **Atomic Concurrency Bounding:** `BudgetManager.reserve_budget` locks funds under an `asyncio.Lock` prior to challenge negotiation. Concurrent stage calls are bounded by an `asyncio.Semaphore(3)` and grouped topologically so that independent calls run simultaneously without race conditions.
- **Strict Settlement Evidence Gates:** Calls are marked `PAID` *only* if the seller returns verified settlement evidence (facilitator receipt or on-chain tx hash). If the seller returns HTTP 200 without valid settlement evidence, or if the network times out *after* payment authorization was dispatched, the call immediately transitions to `PENDING_RECONCILIATION`. The reserved budget is retained (never refunded or double-spent) until an explicit reconciliation process resolves the on-chain status.
- **Member 4 Persistence Synchronization:** Every call status transition (`paid`, `paid output rejected`, `refused`, `failed and not charged`, `pending reconciliation`) is recorded to Member 4's `ledger_repo` with deterministic call IDs (`call_{task_id[:8]}_step{step_id}_{service_id}`) and idempotency keys (`idem_{task_id}_{step_id}_{service_id}`).

### 3. How It Works
- `BuyerPaymentClient` implements `BuyerPaymentClientInterface` by integrating with `PaymentPolicyVerifier`, `SettlementVerifier`, and `web3`.
- `BuyerService._execute_call()` coordinates the sequence:
  1. Reserve budget atomically via `BudgetManager`.
  2. Send initial HTTP request to seller endpoint; receive 402 challenge.
  3. Validate challenge against `PaymentPolicyVerifier`.
  4. Obtain signed payload from `BuyerPaymentClient`.
  5. Dispatch payload in `X-402-Payment-Payload` header.
  6. Catch post-dispatch timeouts and missing settlement proofs -> `PENDING_RECONCILIATION`.
  7. On verified settlement proof -> `PAID`, validate output schema; commit budget.
  8. Synchronously record call in `TaskRecordModel` and Member 4's `ledger_repo`.

---

## Decision 12: Dependency-Aware Asynchronous Execution, Strict Input Isolation, & Safe Fallbacks

### 1. Context & Problem
In complex agent workflows requiring Data (`data.lookup.v1`), Scraping (`scraping.extract.v1`), and Inference (`inference.summarize.v1`), naïve execution creates several failure modes:
1. Running dependent calls before upstream outputs exist causes runtime failures.
2. If an upstream dependency fails, executing downstream calls wastes payments on unfulfillable requests.
3. Sending unvalidated or extraneous metadata to sellers violates API contracts.
4. Starting a fallback service when the primary call had an uncertain settlement risks double-spending.
5. Starting a fallback whose price exceeds the remaining budget causes financial overruns.

### 2. Theory & Logic
- **Topological & Dependency Gating:** Stage 0 executes independent calls (Data & Scraping) concurrently bounded by `asyncio.Semaphore(3)`. Stage 1 (Inference) depends on Stage 0. Prior to reserving budget or executing a dependent call, the buyer checks that all upstream dependencies succeeded (`CallStatus.SUCCEEDED`) and produced valid outputs. If any upstream dependency failed or was not charged, the dependent call is automatically skipped (`FAILED_AND_NOT_CHARGED`) with zero funds spent.
- **Strict Input Isolation:** Each seller receives only the validated fields defined by Member 2's contracts:
  - Data seller: `DataSellerInput(symbol=...)`
  - Scraping seller: `ScrapingSellerInput(url=...)`
  - Inference seller: `InferenceSellerInput(prompt=..., max_tokens=..., temperature=...)`
  When Inference depends on upstream calls, its `prompt` is synthesized strictly from validated upstream outputs (e.g. market rates and extracted text).
- **Two-Phase Fallback Safety:**
  - Fallbacks are **STRICTLY FORBIDDEN** if the primary call resulted in an uncertain payment outcome (`PENDING_RECONCILIATION`), as the payment may settle on-chain.
  - If the primary call failed with a clean non-payment error (`FAILED_AND_NOT_CHARGED`), the budget reservation is released, and the fallback's price is checked against `budget_mgr.available_budget`. If the fallback price exceeds available funds, it is rejected and not executed.
- **Member 4 Audit Completeness:** All call records store explicit `step_id`, `depends_on`, `service_id`, `amount_paid`, and `tx_hash` synchronized with Member 4's `ledger_repo` and SQL `LedgerRecordModel`.

---

## Decision 13: Seller-Output Schema Validation, Transparent Aggregation, & Field-Level Provenance

### 1. Context & Problem
In a decentralized pay-per-call agent economy, sellers may return responses with invalid content types (e.g. `text/html` error pages), malformed JSON, missing required fields, or type mismatches. If the buyer agent naively aggregates these responses or hallucinates missing data, downstream users receive corrupt findings. Furthermore, when a micropayment has already settled on-chain (`tx_hash` or facilitator receipt verified) but the delivered output is invalid, the buyer cannot silently erase the cost or claim the call was free; nor can it report the failure as a successful finding.

### 2. Theory & Logic
- **Rigorous Draft-7 Schema Validation:** `OutputValidator` validates raw responses against the exact Draft-7 output JSON Schema registered for the seller version. Rejections explicitly check Content-Type headers (`application/json`), parse malformed JSON, verify top-level dictionaries, and detail missing required fields and type errors.
- **Irrevocable Cost Accounting (`PAID_OUTPUT_REJECTED`):** When payment is verified by Member 1's `SettlementVerifier` but schema validation fails, the status is set to `CallStatus.PAID_OUTPUT_REJECTED` (matching Member 4's `LedgerStatus.PAID_OUTPUT_REJECTED`). The on-chain `tx_hash` and `amount_paid_usdc` are permanently preserved in the ledger and task record. The money was spent, and the seller's reputation score is penalized for non-compliance.
- **Zero-Hallucination Result Aggregation:** `ResultAggregator` aggregates ONLY validated outputs from `CallStatus.SUCCEEDED` calls into `market_data`, `web_sources`, and `summary`. Rejected outputs are quarantined in `rejected_outputs`, while execution failures and unverified payments are quarantined in `failed_calls`. Under no circumstances are synthetic facts invented to replace missing data.
- **Deterministic Field-Level & Result-Level Provenance:** Every aggregated finding in `market_data` and `summary` is explicitly linked in a `provenance` record specifying: `target_field`, `service_id`, `call_id`, `step_id`, `category`, `schema_version`, `timestamp`, `payment_reference`, and `validation_status: "valid"`.
- **Transparent Execution Disclosures:** When outputs are rejected or calls fail, transparent disclosure notices are appended to the user-facing summary detailing the producing service ID and schema error reason.

---

## Decision 14: Authoritative Ledger Reconciliation, Itemized Spending Summaries, & Non-Fabricated Explorer Links

### 1. Context & Problem
In agent marketplaces, users and auditors require transparent explanations of every micropayment. If the buyer agent derives verified spending from local in-memory counters or planned prices, discrepancies emerge between the buyer's reported total and Member 4's authoritative audit ledger. Furthermore, generating fake or illustrative explorer links for non-hash tokens or unsettled calls misleads users and undermines trust.

### 2. Theory & Logic
- **Authoritative Ledger Reconciliation:** `ExplanationGenerator` queries Member 4's `ledger_repo` for every service call record. Verified spending is calculated exclusively from ledger records with verified settlement proofs (`tx_hash` / facilitator receipt) in terminal states (`paid` or `paid output rejected`).
- **Missing & Ambiguous Ledger Isolation:**
  - If a ledger entry is missing, it is NOT counted in verified spending; a warning is recorded.
  - If a call is in `pending reconciliation` or lacks on-chain confirmation, its amount is quarantined under `uncertain_pending_usdc` and subtracted from available remaining budget, but never presented as verified spend.
- **Seven-Part Itemized Spending Accounting:** Pure integer base-unit arithmetic guarantees exact precision across:
  1. `budget_allocated_usdc`: Initial budget allocation.
  2. `estimated_cost_usdc`: Pre-execution planned cost ceiling.
  3. `verified_spent_usdc`: Sum of verified on-chain settled payments from ledger.
  4. `reserved_budget_usdc`: Funds held for pending reconciliations.
  5. `uncertain_pending_usdc`: Ambiguous amounts awaiting on-chain resolution.
  6. `refunded_amount_usdc`: Released unspent funds returned to buyer.
  7. `remaining_budget_usdc`: Available unspent funds (`budget - verified_spent - uncertain_pending`).
- **Strict Explorer Link Validation (Zero Fabrication):** Base Sepolia explorer links (`https://sepolia.basescan.org/tx/{tx_hash}`) are generated strictly when a verified 66-character hex hash starting with `0x` is present. Placeholder tokens, mock strings, or receipts return `None`.
- **Fact-Based Service Selection Explanations:** Explanations cite actual registry reputation scores and median latencies when verified call history exists; when a service has no history, the narrative explicitly states `"No prior reputation history in ledger"` without hallucinating scores.




