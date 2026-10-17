# AGENTICA — Phase 4 Implementation Plan
## Production Hardening, Trust, Observability, and Marketplace Readiness

**Project:** DI-06 — Agentica  
**Product category:** AI Agent Marketplace  
**Core concept:** Pay-per-Call Agent Economy  
**Tagline:** *Discover. Pay. Execute. Trust.*  
**Document type:** Implementation plan  
**Status:** Proposed plan — confirm team ownership and acceptance criteria before implementation  
**Last updated:** 17 October 2026

---

## 1. Purpose

Phase 4 moves AGENTICA from a capability-aware prototype toward a dependable, demonstrable agent marketplace. Phase 3 focused on capability-aware discovery and planning, seller/provider integration, budget protection, x402 compatibility, and automated integration testing.

Phase 4 should concentrate on the quality of the complete product: trustworthy payment evidence, persistent and auditable execution records, operational observability, resilient workflows, a usable marketplace experience, deployment readiness, and a reproducible end-to-end demonstration.

**Phase 4 must not begin by rebuilding Phase 3.** Start with a short verification gate, identify the actual remaining gaps, and implement only work that is missing or demonstrably defective.

### Phase 4 outcomes

By the end of the phase, the team should be able to demonstrate that:

1. A buyer can discover and select an eligible seller based on capabilities and constraints.
2. A buyer can submit a task with an explicit budget and receive a clear execution plan.
3. Paid steps use the existing x402/payment interfaces and enforce price, recipient, network, token, replay, idempotency, and budget controls.
4. Payment state and service-delivery state are recorded separately and can be reconciled.
5. Task, call, payment, and error histories remain available through the persistence layer.
6. Operators can understand service health, latency, failures, and uncertain payment outcomes without exposing secrets.
7. The frontend clearly communicates plans, prices, execution progress, results, and payment status.
8. The team can reproduce a documented demo and distinguish mocked results from live-provider and live-testnet evidence.

---

## 2. Baseline and assumptions

The latest user-provided Phase 3 report states that:

- Capability metadata and capability-aware selection/planning are implemented.
- Gemini and Groq inference smoke tests returned successful live responses.
- A buyer workflow completed a scraping → inference pipeline.
- The backend suite reported **275 passed in 7.02 seconds**.
- Live Base Sepolia settlement has **not yet been demonstrated** in the supplied report.
- Git integration/release coordination still requires review.

These are reported results, not an independent inspection of the current repository. Phase 4 Stage 0 must rerun the relevant checks and record the actual current state.

### Known architecture

- **Frontend:** React, Vite, TypeScript.
- **Backend:** Python, FastAPI, Pydantic.
- **Buyer:** capability-aware task selection, planning, DAG execution, budget reservation.
- **Seller services:** data, scraping, inference.
- **Payments:** x402 v2 compatibility, USDC-oriented payment flow, Base Sepolia test network.
- **Persistence/ledger:** PostgreSQL and transaction/task records.
- **External providers:** Gemini and Groq inference; configured data and safe scraping providers.
- **Testing:** pytest, mocked provider/payment tests, in-process integration tests.
- **Git workflow:** separate member ownership, review before integration, no unapproved commits/pushes/merges.

### Non-goals

Unless explicitly approved as a separate scope, Phase 4 does not include:

- Replacing the existing x402 SDK or building a second payment engine.
- Moving real funds or running live transactions without explicit authorization.
- Rewriting the Buyer/Registry capability system.
- Adding a token, speculative blockchain features, or a new chain.
- Claiming production readiness based solely on unit tests or simulated settlement.
- Broadly refactoring another member's subsystem without their approval.

---

## 3. Governance and ownership

Follow `AGENTS.md` and `docs/TEAM_WORKFLOW.md` before making changes.

| Area | Primary owner | Phase 4 responsibility |
|---|---|---|
| Shared architecture, shared schemas, integration destination | Setup Lead | Approve cross-cutting contracts, release criteria, and shared changes |
| x402, payment verification, settlement and reconciliation semantics | Member 1 | Payment evidence, verification contract, failure-state behavior |
| Seller agents, provider adapters, seller routes, scraping security | Member 2 | Seller reliability, provider correctness, safe error handling |
| Buyer, registry, selector, planner, orchestration | Member 3 | Capability-aware workflow, plan transparency, safe execution |
| PostgreSQL, ledger, persistence, frontend/dashboard, deployment support | Member 4 | Durable records, operational dashboard, migration/deployment checks |

A person may help test another subsystem, but must not directly modify owner-controlled files without permission.

### Git safety requirements

- Verify the branch, upstream, working tree, and commit ancestry before work.
- Do not switch branches, commit, push, merge, rebase, reset, or stash without explicit authorization.
- Do not push a consolidated branch merely because it contains multiple team members' work.
- Keep `.env`, wallet secrets, API keys, and credentials out of Git.
- Use focused changes and tests; record the exact commit used for each test report.
- Obtain owner review for shared contracts and API changes.

---

## 4. Phase 4 workstreams

### Workstream A — Release baseline and contract freeze

**Owner:** Setup Lead, with all members contributing  
**Priority:** P0

#### Tasks

1. Verify branch and repository state.
2. Run the complete backend test suite and any frontend test/build commands available in the repository.
3. Record the actual commit hash, test count, failures, skips, and duration.
4. Verify that the shared service contract, seller schemas, registry metadata, buyer plan schema, payment interface, and ledger records agree.
5. Identify which tests use mocks, which contact live providers, and which verify actual testnet settlement.
6. Define the Phase 4 acceptance criteria and freeze the public API contracts for the duration of implementation unless a change is approved.

#### Acceptance criteria

- A reproducible baseline report exists.
- No branch ambiguity or unexplained uncommitted work remains.
- Contract mismatches are listed with an owner.
- Mocked, live-provider, and live-chain results are clearly distinguished.

---

### Workstream B — Payment evidence and reconciliation

**Owner:** Member 1, coordinated with Members 3 and 4  
**Priority:** P0

This is the most important unresolved release dependency when real pay-per-call transactions are part of the product promise.

#### Tasks

1. Trace the existing x402 flow from challenge creation through buyer authorization, seller verification, settlement response, and ledger update.
2. Document the exact meaning of each payment state; do not use a generic `success` flag to represent both payment and service delivery.
3. Ensure the implementation distinguishes at least:
   - payment not started,
   - payment required,
   - payment authorized/submitted,
   - payment confirmed/settled according to the verifier's actual contract,
   - payment uncertain/pending reconciliation,
   - payment failed,
   - service execution started,
   - service delivery succeeded,
   - service delivery failed after payment.
4. Verify that a seller does not execute paid business logic before the required payment verification.
5. Verify that a nonempty transaction hash is not treated as sufficient evidence of finality by itself.
6. Define how a transaction receipt, network, token contract, amount, sender/recipient, and relevant transfer event are checked where applicable.
7. Verify idempotency and replay protection across retries, timeouts, duplicate requests, and concurrent requests.
8. Ensure uncertain outcomes enter reconciliation rather than triggering a blind second charge.
9. Ensure a provider failure after confirmed payment is represented accurately and is not disguised as a payment failure.
10. Add or update owner-approved tests for every state transition.

#### Live testnet gate

Only after explicit authorization:

- Use a dedicated test wallet and testnet funds.
- Perform one low-value, controlled Base Sepolia transaction.
- Verify the transaction receipt and relevant USDC transfer evidence independently.
- Match the evidence to the buyer call and ledger record.
- Record the transaction hash in the test report, but never record private keys or secrets.
- Repeat no transaction unless the previous outcome is known or safely reconciled.

#### Acceptance criteria

- Payment and delivery state are separate.
- Invalid payment data fails closed.
- Duplicate/replayed requests cannot cause duplicate charges.
- Uncertain outcomes remain pending reconciliation.
- Live settlement is marked **VERIFIED IN LIVE ENVIRONMENT** only with real chain evidence. If not authorized or unavailable, mark it **BLOCKED** or **NOT RUN**.

---

### Workstream C — Durable task and transaction history

**Owner:** Member 4, coordinated with Members 1 and 3  
**Priority:** P0

#### Tasks

1. Audit the current PostgreSQL schema and persistence path.
2. Define durable records and relationships for:
   - task,
   - plan/step,
   - service call,
   - payment attempt,
   - settlement evidence,
   - delivery outcome,
   - reconciliation case,
   - relevant audit event.
3. Use stable IDs and idempotency keys to correlate the buyer, seller, payment, and ledger records.
4. Make state transitions safe under concurrent updates.
5. Add or verify database transactions around operations that must be atomic.
6. Define migration and rollback procedures.
7. Verify that restart/reload does not silently lose task history or make an uncertain payment appear successful.
8. Ensure secrets, raw payment credentials, and unnecessary sensitive payloads are not persisted.
9. Add tests for duplicate writes, concurrent updates, persistence failures, and restart recovery.

#### Acceptance criteria

- Task and payment histories survive application restart.
- Each paid call can be traced across task, service, payment, and ledger identifiers.
- Financial amounts use integer base units or a rigorously validated decimal representation; floating-point arithmetic is not used for settlement amounts.
- Database failures do not create false success states.
- Migrations are repeatable and documented.

---

### Workstream D — Buyer workflow reliability and user-visible explanations

**Owner:** Member 3  
**Priority:** P1

#### Tasks

1. Verify the capability-aware selector and planner against the actual registry contract.
2. Ensure hard constraints are checked before payment reservation or paid execution.
3. Ensure the proposed plan exposes each service, operation, price, expected dependency, and maximum planned cost.
4. Revalidate the service price, recipient, network, token, and eligibility immediately before payment.
5. Ensure independent DAG steps can execute concurrently only where the plan allows it and budget reservation remains atomic.
6. Ensure dependent steps do not run after an upstream failure.
7. Ensure invalid outputs are not passed downstream or presented as successful results.
8. Ensure partial completion is represented clearly when one paid step succeeds and a later step fails.
9. Make the final explanation report actual service calls and observed costs, not planned or estimated values presented as actual.
10. Keep retries bounded and idempotent; never retry uncertain payment outcomes blindly.

#### Acceptance criteria

- The plan can be inspected before execution.
- The buyer explains why each service was eligible and selected.
- Budget cannot be exceeded under concurrent calls.
- Failed or invalid steps do not produce misleading final success.
- The user can distinguish planned cost, reserved budget, actual spend, and unspent budget.

---

### Workstream E — Seller and provider operational hardening

**Owner:** Member 2  
**Priority:** P1

#### Tasks

1. Verify fake/live mode selection and fail-closed behavior when live configuration is missing.
2. Confirm tests do not accidentally make live provider calls.
3. Confirm provider responses are parsed and validated against seller output schemas.
4. Confirm timeouts, rate limits, malformed responses, and upstream errors are normalized and sanitized.
5. Ensure provider/model metadata reflects the provider and model actually used.
6. Review the Gemini and Groq model names against the currently configured provider account before a demo; do not assume a model name remains available indefinitely.
7. Verify that live provider failures do not silently fall back to fake output.
8. Review prompt/input limits and output token limits.
9. Re-audit scraping URL restrictions, DNS resolution, pinned connections, redirect checks, response-size limits, and peer-address verification.
10. Ensure scraped page content is treated as untrusted input and cannot override system/developer instructions.
11. Ensure secrets never appear in application logs or error responses.

#### Acceptance criteria

- Fake mode is deterministic and isolated in tests.
- Live mode fails closed when configuration is missing.
- No silent fake fallback occurs in live mode.
- Provider failures produce sanitized, actionable errors.
- Scraping protections remain fail-closed.
- Live provider claims are supported by actual live request evidence.

---

### Workstream F — Frontend marketplace and operations dashboard

**Owner:** Member 4, with API requirements from Members 1 and 3  
**Priority:** P1

#### User-facing capabilities

1. **Service discovery**
   - Show service name, category, supported capabilities, price, network, and active status.
   - Clearly distinguish declared capability metadata from measured performance or reputation.
2. **Task submission**
   - Accept a natural-language task and explicit maximum budget.
   - Show validation errors before execution.
3. **Plan review**
   - Display the proposed steps, dependencies, service prices, and maximum cost.
   - Require an explicit user action before paid execution if that is the agreed product flow.
4. **Execution progress**
   - Show queued, running, succeeded, failed, and blocked steps.
   - Distinguish service failure from payment uncertainty.
5. **Payment transparency**
   - Show planned cost, reserved budget, actual spend, and remaining budget.
   - Display transaction evidence only when verified.
   - Link to a network-appropriate explorer when a valid transaction hash exists.
6. **Results**
   - Display validated outputs and the services used.
   - Show partial failure and reconciliation states honestly.
7. **History**
   - Allow users to inspect past tasks, service calls, costs, and outcomes.

#### Acceptance criteria

- UI state is derived from backend status, not guessed locally.
- A refresh does not turn an uncertain payment into success.
- Error and pending states are clear.
- No private keys or API secrets are exposed to the browser.
- UI does not claim “paid” or “settled” without corresponding backend evidence.

---

### Workstream G — Observability, audit trail, and security

**Owner:** Setup Lead coordinating all subsystem owners  
**Priority:** P1

#### Tasks

1. Introduce or standardize a correlation ID across task, step, service call, payment, and ledger events.
2. Record structured logs for lifecycle events without logging secrets or raw authorization payloads.
3. Define metrics for:
   - task completion and failure rate,
   - service latency,
   - provider timeout/error rate,
   - payment verification failures,
   - pending reconciliation count and age,
   - budget reservation failures,
   - invalid output count.
4. Add health/readiness checks that distinguish process health from external dependency health.
5. Add alerts or dashboard indicators for growing reconciliation backlog and repeated provider failures if monitoring infrastructure is available.
6. Review access control for task history and payment data.
7. Review CORS, request size limits, rate limits, authentication, error messages, and production configuration.
8. Verify that the system does not expose secrets or sensitive internal details in logs, responses, or frontend bundles.
9. Document incident handling for uncertain payment, provider outage, and database outage.

#### Acceptance criteria

- A failed task can be traced across components using a correlation ID.
- Operational metrics distinguish payment failure from delivery failure.
- Health checks do not claim external dependencies are healthy merely because the API process is running.
- Security review findings have an owner and resolution status.

---

### Workstream H — Deployment and reproducible demonstration

**Owner:** Setup Lead and Member 4, with all subsystem owners  
**Priority:** P1

#### Tasks

1. Audit the current Docker, environment, and deployment configuration.
2. Ensure configuration is supplied through environment variables or a secret manager.
3. Verify `.env` and credential files are ignored by Git.
4. Define separate local/test and live-testnet configuration profiles.
5. Ensure the default automated test suite uses mocks and does not spend funds or call paid APIs unexpectedly.
6. Add a health-check procedure and startup validation for required configuration.
7. Document database migration steps and a rollback strategy.
8. Create a clean-environment setup procedure.
9. Create a deterministic demo path using fake providers/mocked payments for reliability.
10. Create a separate live demo path only for explicitly authorized live providers and testnet payments.
11. Record the exact commit, configuration mode, and evidence type used in the demo.
12. Prepare a fallback demo plan that clearly labels simulated payments and does not misrepresent them as real transactions.

#### Acceptance criteria

- A new developer can set up and run the project using documented steps.
- The normal test suite does not require live credentials.
- Deployment starts only with valid configuration.
- Demo steps are reproducible.
- Simulated and live evidence are visibly distinguished.

---

## 5. Recommended implementation order

| Order | Work item | Owner(s) | Dependency | Completion evidence |
|---:|---|---|---|---|
| 1 | Baseline, branch and contract audit | Setup Lead + all | None | Baseline report and approved acceptance criteria |
| 2 | Payment state and settlement evidence audit | M1 + M3 + M4 | Work item 1 | State-transition tests and documented verifier semantics |
| 3 | Persistence and reconciliation | M4 + M1/M3 | Stable state model | Database tests, recovery tests, correlated records |
| 4 | Buyer plan/execution transparency | M3 | Stable contracts | Planner and DAG tests; honest cost/status output |
| 5 | Seller/provider hardening | M2 | Provider contracts | Provider tests, security tests, live-mode isolation |
| 6 | Frontend integration | M4 + M1/M3 | API state contracts | UI tests or documented manual acceptance checks |
| 7 | Observability/security review | Setup Lead + all | Core state model | Security checklist, correlation IDs, metrics |
| 8 | Deployment and demo rehearsal | Setup Lead + M4 + all | Previous work | Reproducible demo and release checklist |
| 9 | Final acceptance review | Setup Lead + all | All required items | Signed-off Phase 4 report |

**Parallelization:** Workstreams C, D, and E can proceed in parallel after the Stage 0 contract audit, provided owners coordinate API and state changes. Frontend work should consume agreed contracts rather than inventing its own status semantics.

---

## 6. Test strategy

### Automated tests

Run the current project-approved command. The latest reported backend command is:

```bash
python -m pytest backend/tests/ -v
```

Also run the frontend tests/build if scripts are present in `package.json`.

Required categories:

- Unit tests for models, schemas, state transitions, and amount conversions.
- Integration tests for buyer → registry → seller contracts.
- DAG tests for dependency success/failure and concurrency.
- Payment tests for invalid signatures, wrong network/token/recipient/amount, replay, idempotency, and uncertain outcomes.
- Persistence tests for transaction boundaries, duplicate writes, restart recovery, and concurrent updates.
- Provider tests for missing configuration, timeouts, upstream failures, malformed outputs, and no silent fallback.
- Security tests for scraping SSRF, redirect revalidation, payload limits, secret redaction, and authentication.
- Frontend tests/build and manual acceptance checks where automated coverage is unavailable.

### Live tests

Live tests must be opt-in and explicitly authorized:

- Gemini/Groq smoke tests may incur API usage.
- Base Sepolia tests may spend testnet funds and must use a dedicated test wallet.
- Live multi-hop tests must use real provider evidence and real settlement evidence if the demo claims a paid transaction.
- If live tests are not performed, mark them **NOT RUN** or **BLOCKED**.

### Evidence labels

Every report must label evidence as one of:

- **VERIFIED BY AUTOMATED TESTS**
- **VERIFIED IN LIVE ENVIRONMENT**
- **MOCKED / SIMULATED**
- **NOT RUN**
- **BLOCKED**

Do not combine these labels into one generic “passed” result.

---

## 7. Definition of Done

Phase 4 is complete when all applicable acceptance criteria are met and reviewed by the Setup Lead.

### Functional
- [ ] Service discovery exposes valid capability metadata.
- [ ] Buyer plans are inspectable before paid execution.
- [ ] Hard constraints and maximum budget are enforced.
- [ ] Multi-step workflows handle dependency failures correctly.
- [ ] Partial task completion is represented honestly.
- [ ] Task and service-call history is available.

### Payments and financial integrity
- [ ] Payment verification semantics are documented.
- [ ] Payment and delivery states are separate.
- [ ] Replay and duplicate-charge protections are tested.
- [ ] Uncertain outcomes enter reconciliation.
- [ ] Actual spend and remaining budget are accurate.
- [ ] Live Base Sepolia settlement is verified if required by the release promise.

### Reliability and security
- [ ] Fake/live provider modes are isolated.
- [ ] No silent fake fallback occurs in live mode.
- [ ] Provider and database errors fail safely.
- [ ] Scraping protections remain enabled.
- [ ] Secrets are excluded from source control, logs, and browser bundles.
- [ ] Health and operational status are meaningful.

### Product and deployment
- [ ] Frontend displays service, plan, execution, cost, and payment states accurately.
- [ ] Deployment and environment setup are documented.
- [ ] Database migrations and recovery procedures are documented.
- [ ] Demo can be reproduced from a clean environment.
- [ ] Live and simulated evidence are clearly distinguished.

### Governance
- [ ] Current branch and integration destination are agreed.
- [ ] All owner-controlled changes are reviewed.
- [ ] Regression suite passes on the final candidate commit.
- [ ] Known limitations and deferred items are documented.
- [ ] Setup Lead signs off on the Phase 4 completion report.

---

## 8. Risks and mitigations

| Risk | Impact | Mitigation | Owner |
|---|---|---|---|
| Mocked payment mistaken for real settlement | Misleading demo and financial risk | Require real receipt/transfer evidence for live claims | M1 |
| Payment succeeds but service fails | User trust and reconciliation issue | Separate payment/delivery states and expose recovery status | M1 + M3 + M4 |
| Duplicate request after timeout | Duplicate charge or execution | Idempotency, replay checks, reconciliation before retry | M1 + M3 |
| Budget overspend under concurrency | Financial integrity failure | Atomic reservations and concurrency tests | M3 + M4 |
| Provider/model availability changes | Failed inference calls | Configurable models, startup checks, sanitized errors | M2 |
| SSRF or malicious scraped content | Internal access or prompt injection | Pinned connections, redirect checks, untrusted-content handling | M2 |
| Branch contains mixed member changes | Accidental release or overwrite | Owner review and explicit integration plan | Setup Lead |
| Secrets leak through logs or Git | Account compromise | Secret scanning, `.env` ignore rules, redaction, rotation | All |
| UI claims payment before confirmation | Misleading user state | Derive UI from authoritative backend state | M4 + M1 |
| Phase scope expands indefinitely | Delayed completion | Prioritize P0 items and require approval for scope additions | Setup Lead |

---

## 9. Required Phase 4 deliverables

1. `docs/PHASE4_IMPLEMENTATION_PLAN.md` — this plan.
2. `docs/PHASE4_BASELINE_AUDIT.md` — actual repository, contract, and test baseline.
3. `docs/PHASE4_PAYMENT_RECONCILIATION.md` — payment states, evidence requirements, and recovery rules.
4. `docs/PHASE4_TEST_AND_DEMO_RUNBOOK.md` — repeatable test and demo instructions.
5. `docs/PHASE4_SECURITY_REVIEW.md` — findings, owners, and remediation status.
6. `docs/PHASE4_FINAL_ACCEPTANCE_REPORT.md` — completion matrix with evidence labels.

Create or update these documents only after checking the team's documentation ownership and approval rules.

---

## 10. Immediate next action

**Begin with the Phase 4 baseline audit, not broad implementation.**

1. Verify the actual branch and working tree.
2. Run the full backend regression suite and frontend build/tests if available.
3. Confirm whether the previous successful buyer workflow used a real payment verifier or a mock.
4. Ask Member 1 to confirm the live settlement verification path and acceptance criteria.
5. Ask the Setup Lead to approve the integration destination and Phase 4 priorities.
6. Start the P0 workstreams only after the baseline and ownership are clear.

This sequence preserves the reported Phase 3 progress while focusing Phase 4 on evidence-backed payment integrity, durable operations, user trust, and a reproducible marketplace demonstration.
