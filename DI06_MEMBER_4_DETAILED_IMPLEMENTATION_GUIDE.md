# DI-06 --- Member 4 Implementation Guide

## Database, Payment Ledger, Reputation, Dashboard, and Deployment

**Project:** DI-06 --- Pay-per-Call Agent Economy\
**Owner:** Member 4\
**Suggested branch:** `feature/dashboard-ledger`\
**Primary stack:** FastAPI, PostgreSQL, React, Vite, TypeScript,
Tailwind CSS\
**Network:** Base Sepolia testnet only for the hackathon demo

------------------------------------------------------------------------

## 1. Mission

Member 4 owns the persistence and visibility layer of the project. The
goal is to make the system's actions inspectable and demo-ready:

1.  Persist services, tasks, payment attempts, verified settlements,
    results, and audit events.
2.  Expose read APIs for the ledger, task spending, service reputation,
    health, and readiness.
3.  Build a frontend that shows available services, task execution,
    spending, results, and payment status.
4.  Integrate with Members 1--3 without independently implementing
    payment logic.
5.  Deploy the app safely and rehearse the end-to-end demo.

**Important:** Member 4 must not invent a second schema or change shared
API contracts unilaterally. Inspect the repository's
`DATABASE_SCHEMA.md` and `API_CONTRACTS.md` first. Treat those files as
the shared source of truth and coordinate any required change with the
team.

------------------------------------------------------------------------

## 2. Definition of Done

Member 4 is done when:

-   [ ] Database migrations run from a clean database and can be applied
    repeatably.
-   [ ] Payment attempts and verified settlements are stored separately.
-   [ ] Amounts are stored as integer USDC atomic units, not
    floating-point numbers.
-   [ ] Ledger records clearly distinguish verified payment, no-charge
    failure, refusal, and uncertain reconciliation.
-   [ ] The frontend reads real backend APIs; no fake payment records or
    transaction hashes are shown as real.
-   [ ] A task's spend can be explained from persisted ledger records.
-   [ ] Service reputation is calculated from persisted outcomes and
    latency data.
-   [ ] Health and readiness endpoints work.
-   [ ] Secrets are not exposed in frontend code, Git, API responses, or
    logs.
-   [ ] The deployed app uses HTTPS and the team can complete the demo
    flow from a clean start.

------------------------------------------------------------------------

## 3. First Actions: Inspect Before Coding

Start by checking the repository and reading these documents:

-   `DATABASE_SCHEMA.md`
-   `API_CONTRACTS.md`
-   `PAYMENT_ENGINE_IMPLEMENTATION.md`
-   `SELLER_AGENTS_IMPLEMENTATION.md`
-   `BUYER_AND_REGISTRY_IMPLEMENTATION.md`
-   `Technology Stack & Environment Setup`
-   `Repository Structure & Git Workflow`

Then:

1.  Confirm the existing backend and frontend folder structure.
2.  Identify the database migration tool already in use. If none exists,
    ask the team and adopt one migration approach consistently.
3.  Confirm the official x402 v2 payment status fields with Member 1.
4.  Confirm the service IDs and service metadata with Member 2.
5.  Confirm task IDs, call IDs, orchestration statuses, and result
    formats with Member 3.
6.  Write down the agreed field names and status values before
    implementing the dashboard.

Do not rename shared fields just to match a frontend preference. Adapt
the frontend to the agreed contract.

------------------------------------------------------------------------

## 4. Database Responsibilities

### 4.1 Tables to verify against the canonical schema

The following are the main data concepts expected in the system. Use the
actual definitions in `DATABASE_SCHEMA.md`; these names are a checklist,
not permission to create conflicting duplicate tables.

  -----------------------------------------------------------------------
  Data concept                        Purpose
  ----------------------------------- -----------------------------------
  `services`                          Registry metadata for seller
                                      services

  `tasks`                             Buyer task, budget, status, and
                                      timestamps

  `task_service_calls`                One planned or executed service
                                      call within a task

  `budget_reservations`               Amount reserved before a
                                      potentially paid call

  `payment_attempts`                  Attempts to authorize or execute a
                                      payment

  `settlements`                       Verified on-chain
                                      payment/settlement evidence

  `task_results`                      Service output and final aggregated
                                      result metadata

  `seller_reputation`                 Cached or derived service
                                      performance statistics, if the
                                      canonical design uses this table

  `audit_events`                      Important security and lifecycle
                                      events
  -----------------------------------------------------------------------

If the canonical schema uses different table names or combines some
concepts, keep the canonical design and map the API to it. Do not create
both versions.

### 4.2 Data integrity rules

-   Store USDC amounts as integer atomic units (for a six-decimal token,
    one USDC is 1,000,000 atomic units). Confirm the configured token's
    decimals with Member 1 rather than assuming this for every token.
-   Use database transactions for related updates.
-   Add foreign keys for task, service, call, attempt, and settlement
    relationships where appropriate.
-   Add indexes for common lookups: task ID, call ID, service ID,
    status, and creation time.
-   Use UTC timestamps consistently.
-   Make idempotency keys unique within the agreed scope.
-   Do not store private keys, seed phrases, or unnecessary raw
    signatures.
-   Do not mark a payment as settled merely because a request was sent
    or a seller returned HTTP success.
-   Store transaction hashes only when actually supplied and validated
    by the payment engine.
-   Keep enough evidence to explain why a record has its current status.

### 4.3 Payment attempts versus settlements

Keep these concepts distinct:

-   **Payment attempt:** a payment was requested, prepared, submitted,
    or otherwise attempted.
-   **Verified settlement:** the payment engine has confirmed the
    settlement according to the agreed verification rules.
-   **Reconciliation pending:** the outcome is ambiguous and must not be
    treated as a confirmed charge or a confirmed no-charge failure.

A retry must not create a duplicate charge. Preserve the idempotency and
replay-protection model owned by Member 1.

### 4.4 Suggested migration workflow

1.  Create a migration for the canonical schema changes, rather than
    manually editing a production database.
2.  Apply migrations to a clean local database.
3.  Apply migrations to a second database to test repeatability.
4.  Add indexes and constraints after confirming the API query patterns.
5.  Document required environment variables in `.env.example` using
    placeholders only.
6.  Verify that a failed migration leaves the database in a recoverable
    state.

------------------------------------------------------------------------

## 5. Backend API Responsibilities

Use the exact route names and response structures from
`API_CONTRACTS.md`. The routes below are the intended responsibilities;
if the shared contract differs, follow the shared contract and
coordinate changes.

### 5.1 Ledger

`GET /api/v1/ledger`

Purpose: - Return paginated ledger entries. - Support agreed filters
such as task ID, service ID, status, and date range. - Return only
fields needed by the UI. - Sort predictably, normally newest first.

Possible response fields, subject to the canonical contract:

-   `call_id`
-   `task_id`
-   `service_id`
-   `status`
-   `amount_atomic`
-   `currency` or token identifier
-   `transaction_hash` when available
-   `created_at`
-   `updated_at`
-   `failure_reason` or a safe public explanation when applicable

`GET /api/v1/ledger/{call_id}`

Purpose: - Return the lifecycle and evidence for one call. - Show
payment attempt and settlement status separately if the contract exposes
both. - Avoid returning private payment material or secrets.

### 5.2 Task spending

`GET /api/v1/tasks/{task_id}/spend`

Purpose: - Show the task budget, reserved amount, verified spend, and
remaining budget using the agreed contract. - Compute values from
persisted records and the payment engine's canonical status. - Do not
count `pending_reconciliation` as a verified settlement. - Avoid
double-counting retries or multiple attempts for the same logical call.

Be explicit in the UI about the difference between **reserved**,
**verified spend**, and **uncertain/pending** amounts if those values
are exposed by the contract.

### 5.3 Service reputation

`GET /api/v1/services/{service_id}/reputation`

Possible metrics, if supported by the shared schema and API:

-   Total calls
-   Successful calls
-   Failed calls
-   Success rate
-   Average or median latency
-   Most recent outcome
-   Last updated time

Agree with Members 2 and 3 on what counts as success. For example, a
verified payment with a rejected output is not necessarily a successful
service result. Keep payment success and output quality as separate
metrics when possible.

Avoid presenting a reputation score as objective truth if the system has
too little data. Display the sample size and use a neutral "insufficient
data" state for new services.

### 5.4 Health and readiness

`GET /health`

-   Return a lightweight process health response.
-   Do not reveal environment variables or internal secrets.

`GET /ready`

-   Check that required dependencies, especially the database, are
    usable.
-   Return an appropriate non-success status if the application cannot
    serve requests safely.
-   Do not claim readiness if migrations or required configuration are
    missing.

### 5.5 API quality

-   Validate query parameters and pagination limits.
-   Use consistent error response formats.
-   Return appropriate HTTP status codes.
-   Do not expose stack traces, database credentials, private keys, or
    internal payment secrets.
-   Add tests for empty results, invalid IDs, unavailable database, and
    pagination.
-   Use the existing authentication/authorization model if the team has
    defined one; do not invent a conflicting one.

------------------------------------------------------------------------

## 6. Frontend Responsibilities

Use the existing React/Vite/TypeScript/Tailwind setup if present. Keep
the frontend thin: it should display backend state, not independently
decide whether a payment succeeded.

### Page 1 --- Marketplace

Show: - Available registered services - Service description and
category - Price and currency/token details from the registry -
Availability or health status, if supplied by the API - A clear way to
choose a service or begin a task

Do not hardcode a service's price as authoritative when the registry API
provides it.

### Page 2 --- Buyer Task Console

Show: - Task input and budget - Task progress and current status -
Services selected by the planner - Per-call progress - Refusals, errors,
and pending reconciliation states - Final task completion status

The buyer/orchestration flow belongs to Member 3. The UI should call the
agreed API and render the response rather than reimplementing
orchestration in the browser.

### Page 3 --- Payment Ledger

Show: - Call/task identifier - Seller/service - Amount and token -
Payment status - Transaction hash/link only when the hash is real and
the relevant explorer URL is configured - Timestamp - A detail view for
one call

Provide clear labels and explanations for uncertain outcomes. Never
label an unverified payment as "Paid."

### Page 4 --- Task Results

Show: - Final aggregated result - Per-service outputs where
appropriate - Validation status - Errors or fallback information - Links
back to the related ledger entries

Treat seller output as untrusted data. Render it safely as text or
validated structured data; do not inject arbitrary HTML.

### Page 5 --- Seller Reputation

Show: - Service name - Call count/sample size - Success and failure
metrics - Latency - Last observed outcome - A message when there is not
enough data

Avoid misleading rankings when sample sizes are tiny.

### UI quality checklist

-   Responsive layout that works on the demo laptop and mobile widths.
-   Loading, empty, success, partial-success, and error states.
-   Clear distinction between "no charge confirmed" and "outcome still
    being reconciled."
-   No secrets or private keys in browser code or local storage.
-   No fake transactions presented as real.
-   Avoid showing raw stack traces to users.
-   Use accessible labels, keyboard navigation, and readable contrast.
-   Centralize API base URL configuration in a frontend environment
    variable.

------------------------------------------------------------------------

## 7. Status Semantics

Use the exact enum values in the shared contract. The following meanings
should be preserved even if the literal names differ:

  -----------------------------------------------------------------------
  Meaning                             Required interpretation
  ----------------------------------- -----------------------------------
  `paid`                              Settlement is verified; do not
                                      infer this from HTTP success alone

  `paid_output_rejected`              Payment is verified, but the
                                      returned output failed validation
                                      or acceptance

  `refused`                           Request was blocked before payment
                                      was made

  `failed_and_not_charged`            The system has reliable
                                      confirmation that no charge
                                      occurred

  `pending_reconciliation`            Outcome is ambiguous; neither
                                      confirmed paid nor confirmed
                                      no-charge
  -----------------------------------------------------------------------

Never convert `pending_reconciliation` to `failed_and_not_charged` just
to simplify the dashboard. Never tell the user a transaction succeeded
unless the payment engine confirms it.

------------------------------------------------------------------------

## 8. Integration Plan With Other Members

### Member 1 --- Payment engine/security

Ask for: - Canonical payment and settlement status values - Call and
idempotency identifiers - Amount units and token metadata - The
definition of verified settlement - Safe transaction-hash and
explorer-link behavior - How pending reconciliation is represented

Member 4 should persist and display this information, not replace the
payment engine's verification logic.

### Member 2 --- Seller agents

Ask for: - Stable service IDs - Registry fields and pricing
representation - Latency measurement format - Outcome and
schema-validation fields - Which error details are safe to display
publicly

### Member 3 --- Buyer and registry

Ask for: - Task and call ID conventions - Task lifecycle statuses -
Planned versus executed service calls - Final result format - Partial
success and fallback representation - Exact API contracts the frontend
should call

### Shared integration rule

Create one small example response for each API and get agreement before
building UI against it. If a contract change is necessary, announce it
and update the shared contract document and tests in the same change.

------------------------------------------------------------------------

## 9. Suggested 24-Hour Schedule

### Hours 0--2: Align and scaffold

-   Read the architecture, schema, API contracts, and workflow docs.
-   Confirm status enums and identifiers with all three members.
-   Create the branch and run the project locally.
-   Verify database connection and migration tooling.

**Checkpoint:** everyone agrees on IDs, amount units, and payment
statuses.

### Hours 2--5: Minimum persistence and ledger

-   Implement or verify the canonical migrations.
-   Add repository functions for ledger reads and task spend.
-   Connect the ledger API to real persisted data.
-   Add basic tests.

**Checkpoint:** one testnet payment flow can be traced to a persisted
ledger record once Member 1's vertical slice is available.

### Hours 5--9: Build the dashboard shell

-   Create shared navigation and layout.
-   Implement Marketplace and Payment Ledger views.
-   Add loading, empty, and error states.
-   Connect to actual API responses.

**Checkpoint:** the UI can display service metadata and real ledger
records.

### Hours 9--13: Task results and reputation

-   Implement task-spend and service-reputation APIs.
-   Add Task Results and Seller Reputation pages.
-   Validate calculations and edge cases.
-   Ensure uncertain payment states are displayed honestly.

**Checkpoint:** the dashboard explains what happened during a task and
how much is verified as spent.

### Hours 13--17: Integration and deployment

-   Integrate with the live branches or agreed API mocks.
-   Configure deployment environment variables.
-   Run migrations in the deployment environment.
-   Configure HTTPS and health/readiness checks.

**Checkpoint:** deployed frontend can reach the deployed backend and
database.

### Hours 17--20: Security and failure testing

-   Test database outage and API error behavior.
-   Test duplicate calls and repeated refreshes.
-   Verify no double-counting of retries.
-   Search logs, frontend bundles, and repository history for secrets.
-   Confirm pending reconciliation stays pending.

### Hours 20--24: Freeze and demo rehearsal

-   Avoid nonessential features and risky refactors.
-   Fix demo-blocking bugs only.
-   Test the complete flow from a clean browser session.
-   Prepare a short explanation of ledger status and spending.
-   Keep a known-good commit and deployment available.

------------------------------------------------------------------------

## 10. Minimum Test Plan

### Database and persistence

-   [ ] Migrations apply to a clean database.
-   [ ] Foreign-key and uniqueness constraints work.
-   [ ] Duplicate idempotency keys are handled according to the shared
    contract.
-   [ ] Atomic-unit amounts are preserved exactly.
-   [ ] A payment attempt without verified settlement is not counted as
    verified spend.

### Ledger and spend APIs

-   [ ] Empty ledger returns a valid empty response.
-   [ ] Pagination and filters work.
-   [ ] Unknown call/task IDs return the agreed not-found response.
-   [ ] Repeated attempts do not double-count one logical charge.
-   [ ] `pending_reconciliation` is not treated as confirmed payment or
    confirmed no-charge.

### Reputation

-   [ ] Zero-call services show insufficient data, not a misleading 0%
    quality conclusion.
-   [ ] Success rate and latency are calculated consistently.
-   [ ] Payment success and output validation are not accidentally
    conflated.

### Frontend

-   [ ] Loading, empty, error, and partial-success states render.
-   [ ] UI uses API data rather than fabricated records.
-   [ ] Arbitrary seller output cannot execute as HTML or script.
-   [ ] The UI does not expose secrets.
-   [ ] The interface is usable at the demo screen size.

### Deployment

-   [ ] `/health` responds.
-   [ ] `/ready` reflects database readiness.
-   [ ] HTTPS is enabled.
-   [ ] Required environment variables are documented without real
    secrets.
-   [ ] Logs are useful but do not include secrets or sensitive payment
    material.

------------------------------------------------------------------------

## 11. Security Rules

1.  Never put private keys, seed phrases, or signing secrets in the
    frontend.
2.  Never commit `.env` files containing real credentials.
3.  Keep `.env.example` values clearly fake or blank.
4.  Never fabricate a transaction hash or imply a payment was verified
    when it was not.
5.  Do not trust frontend-calculated spending; the backend is
    authoritative.
6.  Treat service output as untrusted.
7.  Do not expose internal exception details in public API responses.
8.  Do not mark uncertain outcomes as failures or successes for
    presentation convenience.
9.  Keep the demo on Base Sepolia testnet; do not switch to mainnet for
    a hackathon demonstration.
10. Follow the payment engine's verification and reconciliation rules
    owned by Member 1.

------------------------------------------------------------------------

## 12. Git Workflow

Use the agreed repository workflow. A typical sequence is:

``` bash
git checkout main
git pull
git checkout -b feature/dashboard-ledger

# Make small, reviewable changes.
git add .
git commit -m "feat: add persisted payment ledger APIs"

git push -u origin feature/dashboard-ledger
```

Before opening or merging a pull request:

-   Run backend tests and frontend build.
-   Confirm migrations are included.
-   Check that shared API contracts are unchanged or updated with team
    approval.
-   Ensure no secrets or local database files are committed.
-   Request review from the members whose APIs or data models you
    integrated.

Use the actual branch and merge strategy documented in
`Repository Structure & Git Workflow` if it differs from this example.

------------------------------------------------------------------------

## 13. Ready-to-Copy Prompt for Antigravity / Coding Agent

``` text
You are implementing Member 4's work for DI-06 — Pay-per-Call Agent Economy.

Your scope:
- PostgreSQL persistence and migrations
- Payment ledger read APIs
- Task spend API
- Seller reputation API
- Health and readiness endpoints
- React/Vite/TypeScript/Tailwind dashboard
- Integration tests, security checks, and deployment configuration

Before coding:
1. Inspect the repository structure and read DATABASE_SCHEMA.md,
   API_CONTRACTS.md, PAYMENT_ENGINE_IMPLEMENTATION.md,
   SELLER_AGENTS_IMPLEMENTATION.md, and BUYER_AND_REGISTRY_IMPLEMENTATION.md.
2. Treat those documents as the source of truth.
3. Do not invent a parallel schema, change status enums, or rename shared fields
   without documenting the change and getting team agreement.
4. Identify the existing migration tool, frontend setup, and API patterns.

Requirements:
- Persist service, task, call, reservation, payment-attempt, settlement,
  result, reputation, and audit concepts according to the canonical schema.
- Store token amounts as integer atomic units; confirm token decimals with the
  payment owner.
- Keep payment attempts separate from verified settlements.
- Never treat an HTTP success or submitted transaction as verified settlement.
- Preserve pending reconciliation as an uncertain state.
- Prevent retries from being double-counted in spend calculations.
- Implement the agreed ledger, task-spend, reputation, health, and readiness APIs.
- Build Marketplace, Buyer Task Console, Payment Ledger, Task Results, and
  Seller Reputation views using real backend APIs.
- Add loading, empty, error, and partial-success states.
- Treat seller output as untrusted; do not render arbitrary HTML.
- Keep secrets out of frontend code, logs, and Git.
- Add tests for migrations, amount precision, ledger status handling,
  duplicate attempts, API errors, and frontend error states.
- Do not fabricate transaction hashes, payment records, or success statuses.
- Keep all payment verification logic in Member 1's payment engine.
- Use Base Sepolia testnet configuration for the demo.

Work in small steps. First report the repository structure and the contracts
you found. Then implement the smallest working vertical slice, run tests, and
summarize changed files, commands run, results, and remaining blockers.
Do not claim tests or deployment succeeded unless you actually ran and verified them.
```

------------------------------------------------------------------------

## 14. What to Tell the Team at the First Checkpoint

Send a short update containing:

-   Which canonical schema and API contract version you are implementing
-   Which migrations are complete
-   Whether the ledger reads persisted records
-   Which fields/statuses you need confirmed from Members 1--3
-   Whether the frontend is connected to real APIs
-   Current blockers and the next checkpoint

**Priority order if time gets tight:**

1.  Canonical schema and migrations
2.  Persisted ledger with truthful status semantics
3.  Task spend API
4.  Minimal dashboard showing real services and ledger entries
5.  Task results and reputation
6.  Deployment hardening and visual polish
7.  Optional charts or extra analytics

Do not sacrifice payment correctness, truthful status reporting, or
secret handling to add cosmetic features.
