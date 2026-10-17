# AGENTICA — Phase 7 Implementation Plan
## Controlled Testnet Settlement, End-to-End Payment Proof, and Release Hardening

**Project:** DI-06 — AGENTICA: Pay-per-Call Agent Economy  
**Tagline:** Discover. Pay. Execute. Trust.  
**Phase:** 7  
**Document status:** Implementation plan — proposed, not evidence of completion  
**Prepared:** 17 October 2026  
**Repository:** `C:\AgentMarket`  
**Expected branch:** `M2` (verify before acting)  
**Prior phase:** Phase 6 — `ACCEPTED WITH LIMITATIONS`  
**Live Base Sepolia settlement:** `BLOCKED BY AUTHORIZATION / NOT RUN` unless and until the user explicitly authorizes a controlled test.

---

## 1. Purpose

Phase 7 moves AGENTICA from a locally tested release candidate toward a demonstrably integrated, controlled testnet workflow. The priority is to close the gap between:

- successful local tests and fake-mode demonstrations;
- read-only connectivity to Base Sepolia;
- verified, transaction-backed payment settlement;
- durable reconciliation between payment, execution, budget, and ledger state.

Phase 6 reports 287 passing backend tests, a successful frontend production build, a deterministic three-service fake-mode demo, a Level 2 subprocess persistence test, and successful read-only Base Sepolia RPC queries. Those results are reported evidence and should be rechecked against actual repository state before Phase 7 work begins.

**Phase 7 must not assume that read-only RPC checks prove payment settlement.** The read-only checks established reported network connectivity and contract metadata readability only. Phase 6 still records live payment settlement as `BLOCKED BY AUTHORIZATION / NOT RUN`.

## 2. Phase 7 Goal

Deliver a release candidate in which AGENTICA's payment and orchestration lifecycle has been reviewed end to end, with a controlled Base Sepolia transaction attempted only after a separate, explicit user authorization and a successful preflight.

The intended end-to-end path is:

1. Discover and validate a seller service.
2. Validate the buyer plan/DAG and enforce its budget.
3. Create an idempotent payment attempt and reserve the exact budget in integer USDC base units.
4. Obtain the payment challenge/requirements through the supported x402 v2 contract.
5. Submit or verify payment using the approved payment flow.
6. Verify authoritative settlement evidence against the expected network, token, recipient, amount, transaction status, and payment attempt.
7. Execute the seller only after the required payment gate passes.
8. Validate seller output independently of payment state.
9. Reconcile payment, execution, budget reservation, and ledger idempotently.
10. Display the result with an accurate distinction between simulated, facilitator-confirmed, and on-chain evidence.

This is a target workflow, not a claim that every step is currently production-ready.

## 3. Phase 6 Baseline and Known Limitations

Use these as reported baseline facts to verify during Stage 0:

- Project: AGENTICA — Pay-per-Call Agent Economy.
- Reported branch: `M2`.
- Reported HEAD: `0beeb33`; do not assume this remains current.
- Reported backend suite: 287 passed in 16.72 seconds.
- Reported frontend build: 1,975 modules transformed successfully.
- Reported fake-mode DAG demo: 0.009000 USDC simulated spend, 0.041000 USDC remaining from a 0.050000 USDC budget.
- Reported live read-only Base Sepolia RPC: chain ID `0x14a34` / 84532; public block and contract metadata queries succeeded.
- Configured USDC address used in Phase 6 reports: `0x036CbD53842c5426634e7929541eC2318f3dCF7e`. Verify against current official Base/Circle documentation before any live use.
- Live settlement: not run.
- PostgreSQL cloud/multi-process behavior: not verified.
- External live provider calls: not demonstrated as part of the fake-mode demo.
- Phase 6 documentation and tests were reported as untracked, and eight tracked files were reported modified. Recheck `git status --short` and preserve all existing changes.

Do not convert these reported facts into independently verified claims unless the corresponding commands or inspections are performed during Phase 7.

## 4. Scope

### In scope

- Re-establishing the actual repository baseline.
- Reviewing payment policy, x402 compatibility, settlement verification, attempt association, and reconciliation.
- Improving tests for transaction evidence, ambiguous outcomes, replay, idempotency, concurrency, and payment/output separation.
- Testing genuine process restart recovery and documenting the database guarantees that have actually been exercised.
- Reviewing seller payment gates and provider-mode behavior.
- Reviewing configuration, CORS, secrets, and deployment readiness.
- Reviewing frontend payment-truth labels and explorer-link safety.
- Preparing a bounded Base Sepolia test plan.
- Performing read-only preflight checks.
- Optionally executing one controlled testnet payment **only after explicit authorization and successful safety checks**.
- Producing reproducible evidence and an honest final acceptance decision.

### Out of scope unless separately approved

- Mainnet transactions or real-money operations.
- Broad architectural rewrites.
- Production deployment or public exposure.
- Paid provider calls.
- Unapproved wallet generation, importing, signing, or key storage.
- Changes to another member's owned modules without approval.
- Git staging, commits, pushes, merges, rebases, resets, branch switches, stashes, or clean operations without explicit authorization.
- Claims of production readiness based only on local tests or read-only RPC connectivity.

## 5. Mandatory Safety and Team Rules

### 5.1 Git and repository safety

Before any changes:

1. Read `AGENTS.md` and `docs/TEAM_WORKFLOW.md`.
2. Run read-only `git status --short`, `git branch -vv`, `git log -n 5 --oneline`, `git diff --stat`, and `git diff --cached --stat`.
3. Record current branch, HEAD, tracked modifications, staged changes, and untracked files.
4. Preserve all existing Phase 5 and Phase 6 files and modifications.
5. Do not perform Git mutations unless the user explicitly authorizes the specific operation.

### 5.2 Ownership boundaries

Follow the current `docs/TEAM_WORKFLOW.md` and confirm ownership before editing:

- Member 1: `backend/payments/`
- Member 2: `backend/sellers/`
- Member 3: `backend/buyer/`, `backend/registry/`
- Member 4: `backend/ledger/`, `backend/database/`, `frontend/`
- Setup Lead: `backend/shared/`, `backend/main.py`, root configuration, and integration coordination

These boundaries are based on the Phase 6 project notes and must be reconciled with the repository's current team workflow. Do not edit another owner's module without approval. Shared contract changes require coordination with the Setup Lead and affected owners.

### 5.3 Financial safety

- Phase 7 starts in **read-only/local-test mode**.
- No transaction may be signed or broadcast without a separate, explicit user authorization for the live test.
- Do not ask the user to paste private keys into chat.
- Do not print private keys, seed phrases, API keys, or complete `.env` contents.
- Do not automatically generate or store a wallet.
- Do not make paid external provider calls without separate authorization.
- Keep testnet spend minimal and capped by an explicit preflight policy.
- Never treat synthetic receipts, mock verifiers, HTTP 200, or a transaction hash alone as settlement proof.
- If a payment outcome is ambiguous, preserve suspense/hold state and do not automatically retry in a way that could double-charge.
- Never fabricate evidence.

## 6. Workstreams and Acceptance Criteria

## Stage 0 — Baseline Reverification and Change Inventory (P0)

### Tasks
- Read `AGENTS.md`, `docs/TEAM_WORKFLOW.md`, and relevant Phase 5/6 reports.
- Inspect actual repository state and preserve untracked files.
- Run the backend regression suite: `python -m pytest backend/tests/ -q`.
- Run the frontend production build from `frontend/`: `npm run build`.
- Run the deterministic fake-mode demo only after confirming it cannot broadcast transactions or call paid APIs.
- Inspect dependency/configuration versions relevant to payments and database behavior.
- Capture actual outputs, exit codes, and durations.

### Acceptance criteria
- Baseline branch and HEAD are recorded.
- Test/build/demo outcomes are recorded from actual command output.
- Any discrepancy from Phase 6 reports is documented.
- No Git mutation, live transaction, or paid API call occurs.

**Deliverable:** `docs/PHASE7_BASELINE_AND_CHANGELOG.md`

## Stage 1 — Payment Contract and Settlement Verification Audit (P0)

### Tasks
Review the current payment interfaces, x402 v2 integration, payment policy, and settlement verifier. Do not assume that the previous report's six-point validation is sufficient without inspecting code and tests.

Verify at minimum:

- Expected CAIP-2 network / chain ID.
- Successful transaction receipt status.
- Correct configured token contract, checked against official deployment documentation before live use.
- Correct seller `payTo` recipient.
- Exact amount comparison using integer base units.
- Valid ERC-20 `Transfer` event signature and ABI fields.
- Correct association among transaction hash, challenge nonce, payment attempt, service, recipient, and expected amount.
- Handling of missing, malformed, reverted, or not-yet-available receipts.
- RPC outage, timeout, rate limiting, and malformed JSON-RPC responses.
- Multiple matching or conflicting transfer logs.
- Repeated verification and nonce replay.
- Synthetic/facilitator receipt semantics versus direct on-chain settlement.
- Confirmation/finality policy and any chain-reorganization assumptions.

Add negative tests for demonstrated gaps within the payment owner's scope. Do not change payment code across ownership boundaries without approval.

### Acceptance criteria
- Each validation rule has a source-level explanation and a corresponding test where practical.
- Invalid evidence fails closed.
- A transaction hash by itself is never accepted as proof.
- The implementation cannot accidentally accept a payment for a different attempt or seller.
- Uncertain outcomes remain pending reconciliation rather than being marked paid.

**Deliverables:**
- `docs/PHASE7_PAYMENT_VERIFICATION_AUDIT.md`
- `docs/PHASE7_PAYMENT_NEGATIVE_TESTS.md`

## Stage 2 — Payment State Machine, Budget, and Reconciliation (P0)

### Tasks
Audit the relationship among payment attempts, execution state, budget reservations, and ledger rows.

Exercise:

- Same idempotency key + same canonical request.
- Same key + different request payload.
- Replayed payment nonce.
- Concurrent requests competing for the same budget.
- Seller failure before payment confirmation.
- Seller failure after confirmed payment.
- Output schema rejection after confirmed payment.
- RPC timeout before a definitive outcome.
- Recovery of pending reconciliation.
- Repeated reconciliation of already resolved attempts.
- Duplicate ledger prevention.
- Budget hold release only when authoritative state permits it.
- No automatic fallback after an ambiguous payment attempt.

### Acceptance criteria
- Confirmed payment is not erased if downstream execution fails.
- No duplicate charge or ledger row occurs in tested idempotent paths.
- Pending outcomes preserve the correct reservation/suspense state.
- Budget calculations use integer base units.
- State transitions are documented and tested.

**Deliverable:** `docs/PHASE7_RECONCILIATION_AND_BUDGET_AUDIT.md`

## Stage 3 — Durable Persistence and Database Concurrency (P0/P1)

### Tasks
- Verify persistence across fresh objects and separate child processes using an isolated temporary database.
- Confirm that idempotency, consumed nonces, pending reconciliation, and active reservations survive process termination.
- Review database constraints and transaction boundaries.
- Identify SQLite limitations for concurrent/multi-worker deployment.
- If a PostgreSQL test instance is already approved and available, run isolated integration tests against it.
- Do not claim PostgreSQL or distributed concurrency is verified unless it was actually tested.
- Do not modify production data or point tests at a production database.

### Acceptance criteria
- Level 1 object recreation and Level 2 process restart are distinguished in documentation.
- Level 3 PostgreSQL/multi-process concurrency is marked `NOT RUN` unless actually exercised.
- Tests use isolated temporary data.
- Recovery behavior is deterministic and does not double-settle attempts.

**Deliverable:** `docs/PHASE7_DATABASE_DURABILITY_AND_CONCURRENCY.md`

## Stage 4 — Seller, Provider, and SSRF Security (P1)

### Tasks
- Confirm all seller endpoints reject missing or invalid payment evidence before business logic executes.
- Verify fake/live provider modes and ensure live mode never silently falls back to fake data.
- Review URL parsing, DNS resolution, mixed DNS answers, IPv4/IPv6 special ranges, redirects, and socket IP pinning.
- Confirm inability to validate a peer IP fails closed.
- Review request/response size limits and timeouts.
- Treat scraped content as untrusted and test prompt-injection isolation.
- Confirm errors are sanitized and secrets are not logged.
- Do not perform external probing or exploit testing against systems without permission.

### Acceptance criteria
- Payment gate precedes seller execution.
- Invalid internal or metadata destinations are blocked.
- Redirect destinations are revalidated.
- Provider misconfiguration fails closed.
- Security tests run successfully and outputs are recorded.

**Deliverable:** `docs/PHASE7_SELLER_AND_PROVIDER_SECURITY.md`

## Stage 5 — Frontend Payment Truth and Operator UX (P1)

### Tasks
Review the frontend components that display task results, payment statuses, ledger details, and explorer links.

Confirm the UI distinguishes:
- Simulated settlement.
- Facilitator receipt (with precise semantics).
- Verified on-chain transaction.
- Pending reconciliation.
- Paid but output rejected.
- Failed / not charged.
- Unknown or unavailable verification state, if supported.

Review:
- Exact monetary display and conversion from base units.
- No BaseScan links for synthetic receipt identifiers.
- Transaction links only for correctly validated transaction hashes.
- Pending/suspense explanations.
- Clear separation of payment success from seller-output success.
- UI behavior when backend responses are missing or contradictory.

### Acceptance criteria
- UI labels do not overstate the underlying evidence.
- Synthetic receipts are never represented as on-chain transaction hashes.
- The production frontend build passes.
- Any visual changes remain within Member 4's ownership or are approved.

**Deliverable:** `docs/PHASE7_FRONTEND_TRUST_AND_ACCEPTANCE.md`

## Stage 6 — Configuration, Secrets, and Deployment Readiness (P1)

### Tasks
- Review `.env.example`, `.gitignore`, runtime settings, CORS, provider mode, RPC configuration, and payment limits.
- Ensure no secret values are printed in reports.
- Use a secret scanner or targeted scan without printing matching secret values.
- Review current Git history carefully; regex matches must be triaged and not automatically called secrets.
- Verify production CORS uses explicit trusted origins.
- Confirm missing live configuration fails closed.
- Review dependency pinning and known private-API dependencies.
- Document whether deployment configuration has actually been tested.

### Acceptance criteria
- No secrets are exposed in the report.
- Production CORS behavior is covered by tests.
- Required live configuration is validated before any live operation.
- Unverified cloud deployment claims are labeled accurately.

**Deliverable:** `docs/PHASE7_CONFIGURATION_AND_RELEASE_SECURITY.md`

## Stage 7 — Base Sepolia Read-Only Preflight (P0, no transaction)

### Tasks
Perform bounded read-only checks against the configured Base Sepolia RPC:

- `eth_chainId`
- `eth_blockNumber`
- Optional `eth_getBlockByNumber`
- Read-only `eth_call` for the configured token's public metadata, if needed.

Before relying on the configured token address, verify it against official Base/Circle deployment documentation. Metadata alone does not authenticate a contract.

Record actual raw responses, UTC timestamp, endpoint, and classification. Never invent responses or hardcode a block number.

### Acceptance criteria
- Chain ID matches the expected network.
- RPC response is structurally valid.
- Token configuration is checked against an authoritative source where possible.
- Results are labeled `VERIFIED IN LIVE ENVIRONMENT`.
- This stage makes no transaction and does not mark payment settlement verified.

**Deliverable:** `docs/PHASE7_BASE_SEPOLIA_PREFLIGHT.md`

## Stage 8 — Controlled Testnet Settlement Gate (OPTIONAL; EXPLICIT AUTHORIZATION REQUIRED)

This stage is not automatically authorized by the existence of this plan, by successful read-only checks, or by prior user interest in Path 1.

### Preconditions
All must be true before any signing or broadcast:

1. The user explicitly authorizes a controlled Base Sepolia payment in a separate message.
2. The exact script and its behavior have been inspected.
3. The token address, chain ID, seller recipient, amount, and gas assumptions have been checked.
4. The payment implementation and critical negative tests pass.
5. A dedicated testnet wallet is provisioned by the user outside chat.
6. The private key remains local and is never pasted into chat or committed.
7. A strict one-call spend cap is enforced. The initial proposed service is `data_001`, with a price of 0.002000 USDC (2,000 base units), subject to verification against the actual current registry/configuration.
8. Testnet ETH gas availability and testnet USDC balance are checked read-only.
9. The user has reviewed and approved the exact transaction intent and maximum spend.
10. A safe stop/abort path exists.

### Execution restrictions
- One explicitly approved test call only.
- No mainnet.
- No automatic retries after an ambiguous outcome.
- No broad batch, DAG, or multi-hop live spend.
- No secret output or key handling in chat.
- If any precondition fails, stop and report `BLOCKED` or `FAILED`; do not improvise.
- Do not run a script merely because its filename implies verification. Inspect the code first.
- The user must explicitly authorize the transaction before this stage begins; the current plan itself is not authorization.

### Post-transaction evidence, if authorized and executed
- Transaction hash captured from the actual submission result.
- Independent read-only receipt query.
- Receipt success status and expected transfer log verified.
- Correct chain, token, recipient, amount, and attempt association confirmed.
- Ledger/reconciliation record matches the verified transaction.
- Duplicate verification does not create a duplicate ledger entry.
- Frontend shows the correct evidence classification.
- Report any confirmation/finality limitation.

### Acceptance criteria
If the controlled test is not separately authorized or cannot safely run:
`BLOCKED BY AUTHORIZATION / NOT RUN`.

If it runs and succeeds, classify only the verified transaction and associated end-to-end path as live-tested. Do not generalize one successful transaction into production readiness.

**Deliverable:** `docs/PHASE7_CONTROLLED_TESTNET_SETTLEMENT.md`

## Stage 9 — End-to-End Acceptance Matrix and Failure Scenarios (P0)

Build an acceptance matrix covering at least:

1. Backend regression.
2. Frontend production build.
3. Service registry and capability validation.
4. Buyer DAG validation.
5. Budget reservation and overdraw rejection.
6. Payment policy enforcement.
7. Settlement evidence verification.
8. Wrong network rejection.
9. Wrong token rejection.
10. Wrong recipient rejection.
11. Insufficient amount rejection.
12. Missing/malformed/reverted receipt handling.
13. RPC timeout and pending reconciliation.
14. Duplicate idempotency key with same payload.
15. Same key with changed payload.
16. Nonce replay.
17. Concurrent budget reservation.
18. Seller pre-execution payment gate.
19. Seller output rejection after payment.
20. Provider fail-closed behavior.
21. SSRF/DNS/redirect protections.
22. Process-restart persistence.
23. PostgreSQL integration, if actually run.
24. Frontend simulated/live proof distinction.
25. Deterministic fake-mode three-hop demo.
26. Read-only Base Sepolia preflight.
27. Controlled live settlement, only if separately authorized.
28. No transaction broadcast when authorization is absent.
29. Configuration/CORS checks.
30. Evidence/report consistency.

For each case record:
- Test ID.
- Requirement.
- Command or test name.
- Actual result and exit status.
- Evidence classification.
- Status: `PASS`, `FAIL`, `BLOCKED`, or `NOT RUN`.
- Known limitation.

**Deliverable:** `docs/PHASE7_END_TO_END_ACCEPTANCE_MATRIX.md`

## Stage 10 — Final Regression, Documentation, and Release Decision (P0)

### Tasks
- Run the full backend suite.
- Run the frontend production build.
- Run the fake-mode demo after inspecting its side effects.
- Run focused tests for any modified areas.
- Review the complete diff and ownership approvals.
- Confirm that no unauthorized Git mutation, live transaction, or paid API call occurred.
- Update the Phase 7 reports with actual evidence.
- Preserve previous phase reports and clearly note any changed conclusions.
- Do not commit or push without explicit user authorization.

### Final verdict options
Use exactly one:

- `ACCEPTED`
- `ACCEPTED WITH LIMITATIONS`
- `BLOCKED`
- `FAILED`

Use `ACCEPTED` only when all required acceptance criteria for the declared scope are met and no material untested limitation is hidden. If live settlement is optional and not authorized, the report may still accept the offline/testnet-preparation scope, but must retain the explicit live-settlement limitation.

**Deliverables:**
- `docs/PHASE7_FINAL_ACCEPTANCE_REPORT.md`
- `docs/PHASE7_RELEASE_RUNBOOK.md`

---

## 7. Evidence Classification Rules

Use these labels consistently:

- **VERIFIED BY AUTOMATED TESTS** — a test command was actually executed and its result captured.
- **VERIFIED BY CODE INSPECTION** — the relevant implementation was inspected; this does not prove runtime behavior.
- **VERIFIED BY INTEGRATION TEST** — the integrated path actually ran and output was captured.
- **VERIFIED IN LIVE ENVIRONMENT** — the check ran against the actual named live/testnet service and the result was captured.
- **MOCKED / SIMULATED** — a fake provider, mock receipt, local simulator, or synthetic response was used.
- **NOT RUN** — the check was not executed.
- **BLOCKED** — a precondition or authorization prevented execution.
- **FAILED** — the check ran and failed.

Never classify a local fake-mode demo as live settlement. Never classify read-only RPC connectivity as payment verification.

## 8. Required Phase 7 Documentation

Create these documents as the relevant stages are completed:

1. `docs/PHASE7_BASELINE_AND_CHANGELOG.md`
2. `docs/PHASE7_PAYMENT_VERIFICATION_AUDIT.md`
3. `docs/PHASE7_PAYMENT_NEGATIVE_TESTS.md`
4. `docs/PHASE7_RECONCILIATION_AND_BUDGET_AUDIT.md`
5. `docs/PHASE7_DATABASE_DURABILITY_AND_CONCURRENCY.md`
6. `docs/PHASE7_SELLER_AND_PROVIDER_SECURITY.md`
7. `docs/PHASE7_FRONTEND_TRUST_AND_ACCEPTANCE.md`
8. `docs/PHASE7_CONFIGURATION_AND_RELEASE_SECURITY.md`
9. `docs/PHASE7_BASE_SEPOLIA_PREFLIGHT.md`
10. `docs/PHASE7_CONTROLLED_TESTNET_SETTLEMENT.md`
11. `docs/PHASE7_END_TO_END_ACCEPTANCE_MATRIX.md`
12. `docs/PHASE7_FINAL_ACCEPTANCE_REPORT.md`
13. `docs/PHASE7_RELEASE_RUNBOOK.md`

Do not create empty reports to imply completion. Mark stages not yet executed as planned, `NOT RUN`, or `BLOCKED`.

## 9. Definition of Done

Phase 7 is complete for its declared scope only when:

- The repository baseline and all changes are accounted for.
- Payment verification is reviewed at source level with appropriate negative tests.
- Payment, execution, budget, and ledger states remain consistent in tested success and failure paths.
- Idempotency and replay protections are tested.
- Persistence claims distinguish local SQLite, subprocess restart, and PostgreSQL/multi-process behavior.
- Seller payment gates and SSRF/provider safeguards have relevant test evidence.
- Frontend payment states accurately reflect the strength of the underlying evidence.
- Configuration and CORS claims are supported by code and tests.
- The fake-mode demo remains explicitly simulated.
- Read-only Base Sepolia checks are accurately documented.
- Any live transaction is separately authorized, tightly capped, and independently verified—or clearly remains blocked/not run.
- The final acceptance report includes actual evidence, known limitations, and a defensible verdict.
- No unauthorized Git mutation, paid API call, or financial action occurred.

## 10. Recommended Execution Order

Execute stages in this order:

1. Stage 0 — Baseline.
2. Stage 1 — Payment verification.
3. Stage 2 — Reconciliation and budget.
4. Stage 3 — Persistence and concurrency.
5. Stage 4 — Seller/provider security.
6. Stage 5 — Frontend trust.
7. Stage 6 — Configuration/security.
8. Stage 7 — Read-only testnet preflight.
9. Stage 9 — Acceptance matrix and failure scenarios.
10. Stage 10 — Final regression and report.
11. Stage 8 — Controlled live settlement only if the user separately authorizes it after reviewing the findings.

This order deliberately places the optional live transaction after the code audit and acceptance work, not before it.

---

## Final Status at Plan Creation

**Phase 7 status: PLANNED — NOT EXECUTED.**

**Live Base Sepolia payment settlement: BLOCKED BY AUTHORIZATION / NOT RUN.**

This document is a plan. It is not evidence that any Phase 7 stage has been implemented, tested, deployed, or accepted.
