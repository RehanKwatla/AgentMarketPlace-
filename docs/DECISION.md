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

## Decision 9: Fail-Closed Verifier Receipt Verification & Public Error Sanitization

### 1. Context & Problem
In an open payment-gated microservice environment, two edge failure modes exist:
1. A payment verifier might return a falsy/`None` result instead of raising an exception, which if unchecked would allow unauthenticated execution of seller business logic.
2. An unexpected seller crash (e.g., database connection failure, downstream API crash) might leak database passwords, internal URLs, or credentials if raw exception strings are returned to external clients.

### 2. Theory & Logic
- **Fail-Closed Security Posture:** Any ambiguous or empty payment verification outcome MUST be treated as an explicit authorization denial (`HTTP 402 Payment Required`). Business logic must never execute without concrete settlement receipt evidence.
- **Defensive Error Sanitization:** Internal exceptions (`SellerExecutionError`) must log full diagnostic stack traces server-side while emitting sanitized, opaque error messages to clients to prevent secret leakage.

### 3. How It Works
- `backend/sellers/routes.py` checks `if receipt is None:` immediately after calling `verifier.verify_and_settle()`, failing closed with HTTP 402 and `PAYMENT_AUTHORIZATION_FAILED`.
- `_handle_seller_exception` maps `SellerExecutionError` to HTTP 500 with a static sanitized message (`"Internal execution error occurred within seller logic."`), verified by `test_seller_route_internal_exception_sanitization`.

---

## Decision 10: Server-Side Request Forgery (SSRF) Defense-in-Depth for Scraping Seller

### 1. Context & Problem
The scraping seller (`scraping_001`) receives arbitrary client-supplied URLs to extract web content. Malicious buyers could supply `http://localhost`, `http://127.0.0.1`, `http://169.254.169.254` (cloud metadata IP), or internal private LAN IPs (`10.x.x.x`, `192.168.x.x`), turning the seller microservice into an SSRF proxy to steal cloud credentials or compromise backend infrastructure.

### 2. Theory & Logic
- **Pre-Execution Input Boundary:** Scraping requests must be validated before expensive processing or payment settlement.
- **Strict Protocol & Host Restriction:** Only `http` and `https` schemes are permitted. Hostnames are checked against loopback, link-local, cloud metadata, multicast, and RFC 1918 private CIDR blocks using Python's `ipaddress` library and canonical domain filters (`.local`, `.internal`, `.localhost`).
- **Bounded Payloads:** Both request URLs (max 2048 chars) and extracted response content (max 50,000 chars) are strictly bounded to prevent memory exhaustion and DoS.

### 3. How It Works
- `ScrapingSellerInput` in `backend/sellers/schemas.py` validates URLs via `validate_url` classmethod, raising `ValueError` (resulting in HTTP 422) whenever a forbidden destination is supplied.
- Tested and verified by `test_ssrf_protection_blocks_private_and_loopback_destinations` in `backend/tests/test_sellers_payment_integration.py`.

---

## Decision 11: Decoupling Settlement Verification Proof from Seller Execution Failure Handling

### 1. Context & Problem
Payment settlement and seller business execution are distinct failure domains. If a client submits a valid payment that settles with the facilitator/on-chain, but the seller service subsequently times out (HTTP 504), produces invalid output (HTTP 502), or crashes (HTTP 500):
1. Should the seller fabricate a synthetic receipt? (Never).
2. Should the seller return `X-402-Settlement-Proof` on error responses? (No, attaching settlement proof on 5xx codes confuses client payment engines into assuming successful delivery).
3. How is the payment state preserved? The authoritative payment engine and ledger record the settled transaction as `paid` or `paid output rejected`, ensuring buyer funds and reputation scores are accounted for without corrupting HTTP transport semantics.

### 2. Theory & Logic
- **Transport Semantics vs Ledger Accounting:** HTTP error responses (500, 502, 504) represent service delivery failures and must never attach a settlement proof header or fabricate random UUID receipts (`receipt_<random_uuid>`).
- **Zero Fabrication Rule:** Settlement proof is attached ONLY to HTTP 200 responses, containing the verbatim transaction hash or facilitator receipt ID returned by the authentic payment verifier.

### 3. How It Works
- `backend/sellers/routes.py` extracts `proof` from `SettlementReceipt` and checks that it is a non-empty, genuine string.
- If seller execution fails, `_handle_seller_exception` emits the standard HTTP error status without settlement proof headers.
- Verified by unit tests `test_confirmed_payment_followed_by_seller_timeout_leaves_no_fake_proof` and `test_confirmed_payment_followed_by_invalid_seller_output_fails_closed_502`.

---

## Decision 12: Dual Package Namespace Compatibility (`backend/payments/` & `backend/app/payments/`)

### 1. Context & Problem
The root implementation plan specified `backend/app/payments/` while the existing repository codebase placed payment modules at `backend/payments/`, imported extensively across `main.py`, `buyer_agent.py`, and the test suite. Breaking existing import paths would invalidate tests and team coordination.

### 2. Theory & Logic
- Implement the primary canonical implementation in `backend/payments/`.
- Create a pure re-exporting compatibility package at `backend/app/payments/`.
- Any team member or script importing from either `backend.payments` or `backend.app.payments` resolves identical singleton classes and instances.

### 3. How It Works
- `backend/app/payments/service.py` executes `from backend.payments.service import *`.
- All submodules (`schemas`, `errors`, `policy`, `budget`, `idempotency`, `x402_adapter`, `settlement`) are aliased 1-to-1 with zero duplicated business logic.

---

## Decision 13: Five-State Payment Lifecycle with Suspense (`pending reconciliation`)

### 1. Context & Problem
If an HTTP client transmits an EIP-712 payment authorization to a seller and a network timeout occurs before receiving the HTTP response, the payment may have successfully settled on-chain. Marking this immediately as `failed and not charged` and releasing the budget would cause double-spending or financial unaccountability.

### 2. Theory & Logic
- Introduce an explicit suspense state: `pending reconciliation`.
- When an operation times out after payload transmission, budget reservations are **held** rather than released.
- The attempt is queued for reconciliation against the Base Sepolia RPC or x402 facilitator before any subsequent retry.

### 3. How It Works
- `SettlementTimeoutError` is intercepted in `PaymentService.execute_paid_call()`.
- Result status is set to `PaymentStatus.PENDING_RECONCILIATION`.
- `SettlementVerifier.reconcile_uncertain_attempt()` provides the query path to recheck on-chain receipts without issuing duplicate transactions.

---

## Decision 14: Decoupled x402 Adapter with Strict Fail-Closed Live Signing and Test-Only Fallback

### 1. Context & Problem
Running automated tests on developer machines or offline CI pipelines without Base Sepolia RPC credentials or gas funds must pass reliably, but live payment execution must never fabricate signatures or proceed without authentic cryptographic keys.

### 2. Theory & Logic
- **Fail-Closed Security Boundary:** In live production/testnet mode (`test_mode=False`), `X402Adapter` strictly requires a valid 66-character `BUYER_PRIVATE_KEY` and the `eth_account` library. If either is missing, it fails closed immediately (`PaymentEngineError`).
- Deterministic mock signatures (`0x_mock_sig_...`) are strictly gated behind `test_mode=True`. Mock signatures are never presented as valid live payment authorizations.

### 3. How It Works
- `X402Adapter(test_mode=True)` generates deterministic mock signatures bound to the challenge nonce for unit tests.
- `X402Adapter(test_mode=False)` signs live ECDSA messages or halts execution.
- Tests verify both fail-closed live rejection and deterministic offline signing.

---

## Decision 15: Canonical SHA-256 Request Hashing for Idempotency Collision Prevention

### 1. Context & Problem
A naive idempotency check only looks up the string `idempotency_key`. If a caller reuses the same key with a *different* service or request payload (either accidentally or maliciously), returning the cached result of the previous call leads to silent data corruption.

### 2. Theory & Logic
- Bind the client `idempotency_key` to a canonical SHA-256 hash of the JSON payload.
- Keys must enforce key-to-payload integrity.

### 3. How It Works
- `compute_payload_hash(payload)` serializes dictionaries with sorted keys and compact separators.
- If `key` exists and hash matches: return cached result.
- If `key` exists and hash differs: immediately raise `IdempotencyConflictError` (`HTTP 409`).

---

## Decision 16: Suspense Ledger Isolation (Safe Non-Terminal Handling for Uncertain Payments)

### 1. Context & Problem
The shared `LedgerStatus` enum in `backend/shared/constants.py` defines only four terminal statuses (`paid`, `paid output rejected`, `refused`, `failed and not charged`). If a timed-out attempt (`pending reconciliation`) was written to the shared ledger as `refused`, an uncertain in-flight payment where funds may have settled on-chain would be recorded falsely as a terminal failure with zero funds paid.

### 2. Theory & Logic
- Uncertain payments must never be recorded as terminal failures or terminal successes in the shared ledger.
- The Payment Engine manages an internal suspense store (`self._pending_reconciliations`) and holds the budget reservation until definitive on-chain reconciliation occurs.
- Adding `PENDING_RECONCILIATION` to the shared `LedgerStatus` requires cross-team coordination with Setup Lead and Member 4 (tracked as an explicit Phase 1 deferred item / blocker).

### 3. How It Works
- When `SettlementTimeoutError` occurs, `PaymentService` skips writing to `ledger_repo` and preserves the attempt record in `self._pending_reconciliations`.
- Query helpers `get_pending_reconciliations()` and `get_pending_reconciliation()` expose suspense records.
- When on-chain confirmation or definitive failure is verified in Phase 2, the resolved terminal status is written to the shared ledger.

---

## Decision 17: Dual-Header Support for Official x402 SDK & Application Interoperability

### 1. Context & Problem
Official x402 SDK (v2.25.0) uses HTTP headers such as `PAYMENT-REQUIRED` (or `X-PAYMENT`), `PAYMENT-SIGNATURE`, and `PAYMENT-RESPONSE` with Base64-encoded JSON payloads. Existing application sellers use `X-402-Requirement`, `X-402-Payment-Payload`, and `X-402-Settlement-Proof`. Dropping either breaks backward compatibility or official SDK clients.

### 2. Theory & Logic
The adapter must bridge both standards simultaneously without forcing unilateral breaking changes on other team members.

### 3. How It Works
- `X402Adapter.build_payment_headers()` emits BOTH official SDK headers (`PAYMENT-SIGNATURE`, `X-PAYMENT`) and application headers (`X-402-Payment-Payload`).
- `parse_challenge_from_headers()` accepts either `PAYMENT-REQUIRED`, `X-PAYMENT`, or `X-402-Requirement`.
- `extract_settlement_proof()` checks `PAYMENT-RESPONSE`, `X-PAYMENT-RESPONSE`, and `X-402-Settlement-Proof`.

---

## Decision 18: Strict 6-Point On-Chain Settlement Verification & ERC-20 Transfer Log Decoding

### 1. Context & Problem
A transaction hash alone (`0x...`) or receipt status `0x1` does not prove payment settlement. A reverted transaction, a transaction on the wrong network, a transfer of a worthless custom token, or a transfer to the wrong recipient would all register as valid if only receipt existence was checked.

### 2. Theory & Logic
Settlement verification must enforce a comprehensive 6-point cryptographic and on-chain log audit:
1. Target CAIP-2 network check (`eip155:84532`).
2. Receipt execution status check (`status == 0x1`).
3. Contract address verification (must match official Base Sepolia USDC `0x036CbD53842c5426634e7929541eC2318f3dCF7e`).
4. Event log topic decoding: ERC-20 `Transfer(address,address,uint256)` topic `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef`.
5. Recipient address verification: Transfer `to` parameter matches seller `payTo`.
6. Integer value verification: Transfer `value` integer uint256 matches exact price in base units.

### 3. How It Works
- `decode_and_validate_transfer_logs()` decodes 32-byte padded addresses and big-endian amounts using `web3`.
- `verify_full_settlement()` rejects the settlement if any of the 6 points fail.
- `SellerPaymentVerifier` provides Member 2 with this verification pipeline.

---

## Decision 19: Durable Persistence Layer for Idempotency, Budget Locks, and Crash Recovery

### 1. Context & Problem
In-memory caches for idempotency, nonces, and budget reservations are wiped clean upon process restart, worker reload, or crash. This creates vulnerability to replay attacks, double spending, and lost in-flight reconciliations.

### 2. Theory & Logic
Payment attempts, nonces, and budget holds must be backed by durable database tables with transactional integrity.

### 3. How It Works
- Created `PaymentAttemptModel` and `BudgetReservationModel` in `backend/payments/models.py`.
- `DurablePaymentRepository` persists attempts atomically and tracks reservation lifecycle (`reserved` -> `committed` / `released`).
- `IdempotencyStore` falls back to querying the database when an idempotency key or nonce is not found in memory.
- `PaymentService.get_pending_reconciliations()` hydrates suspense records from `payment_attempts` table on startup.

---

## Decision 20: Deterministic-First DAG Planner, Hard Eligibility Gating, and Pre-Payment Plan Validation (Member 3)

### 1. Context & Problem
In agentic commerce systems, planning without validation leads to hallucinated endpoints, budget overruns, cycles in execution graphs, and payment commitments for invalid or disabled services.

### 2. Theory & Logic
- **Hard Eligibility Gating:** A candidate service is never ranked unless it passes ALL hard eligibility gates first: active/enabled status, trusted registry origin, valid 42-char hex `pay_to` address, Base Sepolia network (`eip155:84532`), Base Sepolia USDC token (`0x036CbD53842c5426634e7929541eC2318f3dCF7e`), positive atomic price within budget, and valid Draft-7 input/output schemas.
- **Explicit DAG Architecture:** Multi-step workflows requiring Scraping, Data, and Inference are modeled as explicit Directed Acyclic Graphs (DAGs) partitioned into topological execution stages. Independent tasks execute in parallel in Stage 0, while dependent tasks execute in Stage 1.
- **Authoritative Price Enforcement:** All prices, recipient addresses, and endpoints are resolved strictly from server-side registry records.

### 3. How It Works
- `ServiceSelector.check_eligibility()` filters candidates, and `rank_candidates()` scores remaining eligible candidates via multi-attribute utility.
- `TaskPlanner.create_plan()` generates an `ExecutionPlan` with dependency graph, topological stages, expected and worst-case cost, fallback allowances, and selection reasons.
- `PlanValidator.validate_plan()` rigorously checks DAG acyclicity, schema compliance via `Draft7Validator`, authoritative server-side registry resolution, and concurrency limits.

---

## Decision 21: End-to-End Buyer Orchestration Integration with Member 1 Payments & Member 4 Persistence (Member 3)

### 1. Context & Problem
The Buyer agent cannot operate in a silo. Every paid invocation must interface with Member 1's payment engine (`BuyerPaymentClientInterface`, `PaymentPolicyVerifier`, `BudgetManager`, `SettlementVerifier`) and record immutable transaction history in Member 4's ledger repository.

### 2. Theory & Logic
- **Delegated Cryptographic Authorization:** The buyer layer (`BuyerService`) never handles private keys or signs transactions directly. Instead, it delegates payload creation to `BuyerPaymentClientInterface.create_payment_payload` and settlement verification to `BuyerPaymentClientInterface.verify_settlement`.
- **Atomic Concurrency Bounding:** `BudgetManager.reserve_budget` locks funds under an `asyncio.Lock` prior to challenge negotiation. Concurrent stage calls are bounded by an `asyncio.Semaphore(3)`.
- **Strict Settlement Evidence Gates:** Calls are marked `PAID` *only* if the seller returns verified settlement evidence (facilitator receipt or on-chain tx hash). If the seller returns HTTP 200 without valid settlement evidence, or if the network times out after payment authorization was dispatched, the call immediately transitions to `PENDING_RECONCILIATION`.
- **Member 4 Persistence Synchronization:** Every call status transition (`paid`, `paid output rejected`, `refused`, `failed and not charged`, `pending reconciliation`) is recorded to Member 4's `ledger_repo`.

---

## Decision 22: Dependency-Aware Asynchronous Execution, Strict Input Isolation, & Safe Fallbacks (Member 3)

### 1. Context & Problem
In complex agent workflows requiring Data, Scraping, and Inference, running dependent calls before upstream outputs exist causes runtime failures. If an upstream dependency fails, executing downstream calls wastes payments.

### 2. Theory & Logic
- **Topological & Dependency Gating:** Stage 0 executes independent calls (Data & Scraping) concurrently bounded by `asyncio.Semaphore(3)`. Stage 1 (Inference) depends on Stage 0. Prior to reserving budget or executing a dependent call, the buyer checks that all upstream dependencies succeeded (`CallStatus.SUCCEEDED`) and produced valid outputs. If any upstream dependency failed, the dependent call is skipped (`FAILED_AND_NOT_CHARGED`) with zero funds spent.
- **Strict Input Isolation:** Each seller receives only the validated fields defined by Member 2's contracts (`DataSellerInput`, `ScrapingSellerInput`, `InferenceSellerInput`).
- **Two-Phase Fallback Safety:** Fallbacks are **STRICTLY FORBIDDEN** if the primary call resulted in an uncertain payment outcome (`PENDING_RECONCILIATION`). If the primary call failed with a clean non-payment error, the budget reservation is released, and the fallback price is checked against available budget before executing.

---

## Decision 23: Seller-Output Schema Validation, Transparent Aggregation, & Field-Level Provenance (Member 3)

### 1. Context & Problem
In a decentralized pay-per-call agent economy, sellers may return responses with invalid content types or corrupted JSON. When micropayments settle on-chain but delivered outputs are invalid, the buyer cannot silently erase the cost or report failure as success.

### 2. Theory & Logic
- **Rigorous Draft-7 Schema Validation:** `OutputValidator` validates raw responses against the exact Draft-7 output JSON Schema registered for the seller version.
- **Irrevocable Cost Accounting (`PAID_OUTPUT_REJECTED`):** When payment is verified by Member 1's `SettlementVerifier` but schema validation fails, the status is set to `CallStatus.PAID_OUTPUT_REJECTED`. The on-chain `tx_hash` and `amount_paid_usdc` are permanently preserved in the ledger and task record.
- **Zero-Hallucination Result Aggregation:** `ResultAggregator` aggregates ONLY validated outputs from `CallStatus.SUCCEEDED` calls into `market_data`, `web_sources`, and `summary`.
- **Deterministic Field-Level & Result-Level Provenance:** Every aggregated finding is explicitly linked in a `provenance` record specifying: `target_field`, `service_id`, `call_id`, `step_id`, `category`, `schema_version`, `timestamp`, `payment_reference`, and `validation_status: "valid"`.

---

## Decision 24: Authoritative Ledger Reconciliation, Itemized Spending Summaries, & Non-Fabricated Explorer Links (Member 3)

### 1. Context & Problem
Users and auditors require transparent explanations of every micropayment. If the buyer agent derives verified spending from local in-memory counters or planned prices, discrepancies emerge between the buyer's reported total and Member 4's authoritative audit ledger.

### 2. Theory & Logic
- **Authoritative Ledger Reconciliation:** `ExplanationGenerator` queries Member 4's `ledger_repo` for every service call record. Verified spending is calculated exclusively from ledger records with verified settlement proofs in terminal states (`paid` or `paid output rejected`).
- **Seven-Part Itemized Spending Accounting:** Pure integer base-unit arithmetic guarantees exact precision across `budget_allocated_usdc`, `estimated_cost_usdc`, `verified_spent_usdc`, `reserved_budget_usdc`, `uncertain_pending_usdc`, `refunded_amount_usdc`, and `remaining_budget_usdc`.
- **Strict Explorer Link Validation (Zero Fabrication):** Base Sepolia explorer links (`https://sepolia.basescan.org/tx/{tx_hash}`) are generated strictly when a verified 66-character hex hash starting with `0x` is present. Placeholder tokens or mock strings return `None`.

