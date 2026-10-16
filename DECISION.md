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

## Decision 9: Deterministic-First Planning & Untrusted LLM Boundary

### 1. Context & Problem
Allowing an LLM to freely decide payment recipients, tokens, networks, or prices creates critical attack surfaces (e.g., prompt injection leading to funds draining or spoofed addresses).

### 2. Theory & Logic
- **Never Trust Model-Generated Pricing or Addresses:** Every service ID in an execution plan must be strictly resolved through the server-side registry.
- Recipient addresses, token addresses, CAIP-2 network identifiers, and prices are fetched directly from authoritative server memory / database.
- A deterministic rule-based planner parses prompt intent and decomposes it into a Directed Acyclic Graph (DAG) with known dependencies (Scraping and Data parallel; Inference dependent on upstream outputs).
- Budget reservations must cover worst-case plan cost before any HTTP calls or payments commence.

### 3. How It Works
- Implemented in `backend/buyer/planner.py`, `backend/buyer/plan_validator.py`, and `backend/buyer/selector.py`.
- Verified in `backend/tests/test_member3.py` and `backend/tests/test_buyer.py`.

---

## Decision 10: In-Process ASGI Transport for Zero-Socket Automated Testing

### 1. Context & Problem
When running automated tests via pytest, `httpx.AsyncClient` attempting to make live network HTTP requests to `http://localhost:8000` will fail with `ConnectError` because no live OS TCP socket is open during unit testing.

### 2. Theory & Logic
- **In-Memory ASGI Dispatch:** Using `httpx.ASGITransport(app=app)` allows `httpx.AsyncClient` to directly execute requests against the FastAPI app in-memory without binding a physical port or needing a separate background server process.

### 3. How It Works
- `BuyerService._execute_call` inspects `endpoint_url`. If targeting `localhost` or `127.0.0.1`, it attaches `ASGITransport(app=app)`.
- If deployed to live Docker or external staging, it falls back to standard HTTP networking automatically.

