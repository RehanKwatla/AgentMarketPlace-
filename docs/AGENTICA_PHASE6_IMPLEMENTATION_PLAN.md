# AGENTICA — Phase 6 Implementation Plan
## Controlled Testnet Validation, Trustworthy Settlement, and Release Readiness

**Project:** DI-06 — AGENTICA: Pay-per-Call Agent Economy  
**Tagline:** *Discover. Pay. Execute. Trust.*  
**Phase:** 6  
**Document status:** Proposed implementation plan  
**Last updated:** 17 October 2026  
**Baseline:** Phase 5 release candidate accepted with limitations  
**Repository:** `C:\AgentMarket`  
**Expected working branch:** `M2` (verify current state before work)  

---

## 1. Executive Summary

Phase 6 moves AGENTICA from a tested local/simulated release candidate toward a carefully verified testnet release. The focus is not adding features for their own sake. It is to establish trustworthy evidence for the existing pay-per-call workflow, close remaining deployment and security gaps, improve release reproducibility, and prepare a judge-ready demonstration that clearly separates simulated behavior from real blockchain settlement.

Phase 5 reports:
- 284/284 backend tests passing.
- Frontend production build passing.
- A deterministic three-service demo with a 0.050000 USDC task budget, 0.009000 USDC simulated spend, and 0.041000 USDC remaining.
- Durable persistence and reconciliation behavior covered by automated tests.
- Live Base Sepolia settlement **not run** and blocked pending explicit authorization.
- CORS wildcard configuration and SQLite's multi-worker limitations documented.
- Phase 5 documentation artifacts created but not committed.

These are the reported Phase 5 baseline results, not a substitute for rerunning checks against the actual repository. Phase 6 begins with a read-only baseline verification.

### Phase 6 north star

> Demonstrate that AGENTICA can safely plan, authorize, execute, account for, and explain a pay-per-call workflow—and provide independently checkable evidence of whether each payment was simulated or actually settled on Base Sepolia.

### Target outcome

At the end of Phase 6, AGENTICA should have:
1. A freshly verified and reproducible local release candidate.
2. Explicit, testable separation between simulation and live settlement.
3. A reviewed and authorized testnet verification procedure.
4. Correct payment/reconciliation evidence for each service call.
5. Safer deployment defaults and an actionable operations runbook.
6. A polished demonstration and acceptance report that make no unsupported claims.

**Important:** Phase 6 does not automatically authorize live transactions, paid provider calls, secret handling, or Git mutations. Those remain separate explicit decisions.

---

## 2. Phase 5 Baseline and Known Limitations

| Area | Phase 5 reported status | Phase 6 treatment |
|---|---|---|
| Backend tests | 284 passed | Rerun and capture fresh output; investigate any drift |
| Frontend build | Passed | Rerun; inspect browser/API behavior beyond compilation |
| Three-hop DAG | Simulated demo passed | Keep deterministic demo as the default smoke test |
| Payment accounting | Integer atomic units; simulated spend reconciles | Audit all payment paths and ledger semantics |
| Settlement verification | On-chain verification logic reported implemented | Review code and tests; separately gate actual testnet verification |
| Reconciliation | Pending state and recovery tests reported | Test uncertain, reverted, delayed, and duplicate outcomes |
| Persistence | SQLite and simulated restart tests reported | Establish exactly which restart/concurrency levels are proven |
| SSRF protection | Socket pinning and redirect checks reported | Re-review critical paths and fail-closed behavior |
| Frontend | Production build passed | Verify visible simulated/live labels and failure states |
| CORS | Wildcard allowed in development | Restrict public deployment origins |
| Database | SQLite default; PostgreSQL configured as an option | Verify PostgreSQL migrations, transactions, and concurrency if used |
| Live Base Sepolia settlement | Not run | Optional gated work requiring explicit authorization |
| Git state | Tracked tree reported clean; Phase 5 docs untracked | Preserve files; do not stage or commit without authorization |

---

## 3. Goals and Non-Goals

### 3.1 Goals

- Re-establish the actual repository baseline before editing.
- Make simulation and live/testnet modes explicit, visible, and difficult to confuse.
- Audit payment state transitions, proof verification, budget reservation, idempotency, replay protection, and reconciliation.
- Verify that task state, payment state, execution state, and ledger records remain semantically distinct.
- Test persistence and recovery at clearly documented levels.
- Harden configuration, CORS, secret hygiene, and deployment guidance.
- Validate the frontend's explanation of price, budget, status, and settlement evidence.
- Prepare a controlled testnet procedure that is only run after explicit authorization.
- Produce concise evidence and a reliable demonstration runbook.

### 3.2 Non-goals

- No broad rewrite of the payment engine or marketplace architecture without an evidence-backed need.
- No new blockchain network or token selection without a documented decision and approval.
- No real-money mainnet deployment in Phase 6.
- No live Base Sepolia transaction, funded-wallet use, or paid external API call without explicit user authorization.
- No claim that simulated receipts are on-chain transactions.
- No claim of production readiness based only on unit tests or a successful frontend build.
- No speculative AI features that distract from payment correctness and release trust.
- No unauthorized edits to another member's owned subsystem.
- No Git staging, commit, push, merge, rebase, reset, checkout, switch, or stash without explicit authorization.
- No destructive database recovery commands as routine procedures.

---

## 4. Team Ownership and Change Governance

| Owner | Owned area | Phase 6 responsibilities |
|---|---|---|
| Member 1 | `backend/payments/` | Settlement evidence, payment state machine, budget reservation, idempotency, replay defense, reconciliation |
| Member 2 | `backend/sellers/` | Seller verification boundary, provider mode, output validation, SSRF protections, error sanitization |
| Member 3 | `backend/buyer/`, `backend/registry/` | Plan validation, capability selection, DAG dependencies, fallback safety, purchase explanations |
| Member 4 | `backend/ledger/`, `backend/database/`, `frontend/` | Durable ledger, transaction boundaries, frontend status display, database deployment checks |
| Setup Lead | `backend/shared/`, `backend/main.py`, root configuration | Shared contracts, CORS, environment configuration, integration coordination, release sign-off |

### Governance rules

1. Read `AGENTS.md` and `docs/TEAM_WORKFLOW.md` before modifying files.
2. Inspect the current branch, commit, working tree, and untracked files before work.
3. Do not overwrite, delete, stage, or commit existing untracked Phase 5 documentation.
4. Shared schema/API changes require Setup Lead coordination and approval from affected owners.
5. Do not change files outside the assigned ownership boundary without approval.
6. Prefer the smallest targeted change that fixes a demonstrated defect.
7. Record the test or evidence that motivated each change.
8. If the baseline differs from the Phase 5 report, stop and document the difference rather than silently reconciling it.
9. Do not expose secrets in prompts, logs, reports, screenshots, or generated documentation.
10. Never represent a planned or mocked test as a live verification.

---

## 5. Phase 6 Workstreams

## 6.0 — Baseline Reverification and Change Freeze

**Priority:** P0  
**Owner:** Setup Lead + all owners  
**Deliverable:** `docs/PHASE6_BASELINE_AND_CHANGELOG.md`

### Tasks
- Verify current branch, HEAD, upstream tracking, and status using read-only Git commands.
- Record tracked modifications, staged changes, and untracked files separately.
- Confirm that the Phase 5 documents are preserved.
- Rerun the backend test suite: `python -m pytest backend/tests/ -q`.
- Run the frontend production build from `frontend/`: `npm run build`.
- Run the deterministic fake-mode demo with the repository's documented command.
- Capture actual command output, exit codes, durations, and test counts.
- Confirm the actual provider-mode environment variable name and default.
- Compare actual outcomes against Phase 5's reported baseline.

### Acceptance criteria
- The report identifies the exact branch and HEAD observed.
- No Git mutation is performed.
- Test/build/demo results are freshly captured rather than copied from Phase 5.
- Any failures or baseline differences are listed with severity and owner.
- The team agrees on a change freeze until P0 findings are resolved.

---

## 6.1 — Payment Evidence and State-Machine Audit

**Priority:** P0  
**Owner:** Member 1; review by Setup Lead and Member 4  
**Deliverable:** `docs/PHASE6_PAYMENT_EVIDENCE_AUDIT.md`

### Tasks
- Trace a payment attempt from challenge issuance through authorization, seller verification, settlement evidence, ledger recording, and reconciliation.
- Verify network, token contract, recipient, exact atomic amount, receipt status, and ERC-20 `Transfer` event validation in live verification code.
- Confirm that a transaction hash alone never establishes settlement.
- Verify that synthetic receipts and mock signatures cannot be accepted as live settlement evidence.
- Verify that payment status and execution/output status are not conflated.
- Verify that confirmed payment remains recorded if seller output fails schema validation.
- Verify that timeouts, RPC outages, malformed receipts, and unknown facilitator states fail closed.
- Verify that `PENDING_RECONCILIATION` keeps the reservation held until an authoritative resolution.
- Verify that terminal states cannot silently transition into contradictory states.
- Check that all amounts remain integer atomic units internally.
- Review proof formatting and explorer-link generation; never create a transaction link from a synthetic receipt.

### Acceptance criteria
- Every payment transition has a documented trigger and allowed next state.
- Ambiguous outcomes cannot be reported as `PAID` without authoritative evidence.
- Synthetic proof identifiers are visibly labeled `MOCKED / SIMULATED`.
- On-chain evidence is called verified only after the receipt and transfer log pass checks.
- Unit and integration tests cover success, wrong token, wrong recipient, wrong amount, reverted receipt, missing log, timeout, malformed proof, and RPC outage.
- Any uncovered behavior is listed as a limitation rather than assumed correct.

---

## 6.2 — Reconciliation, Idempotency, and Replay Resilience

**Priority:** P0  
**Owner:** Member 1 + Member 4

**Deliverable:** `docs/PHASE6_RECONCILIATION_AND_IDEMPOTENCY.md`

### Tasks
- Trace idempotency-key generation and payload canonicalization.
- Verify same-key/same-payload requests return the original result without duplicate seller execution or charging.
- Verify same-key/different-payload requests are rejected.
- Verify nonce uniqueness and durable replay detection.
- Test concurrent reconciliation of the same payment attempt.
- Test reconciliation when the receipt is pending, unavailable, definitively reverted, valid, or inconsistent with expected payment fields.
- Verify that ledger insertion and reservation commit/release are atomic or recoverable across failures.
- Test a crash or forced termination at documented lifecycle boundaries where practical.
- Confirm no automatic fallback or retry initiates a second paid call while the first payment remains ambiguous.
- Ensure retry policy distinguishes a definitively uncharged call from an uncertain settlement.

### Acceptance criteria
- Reprocessing one confirmed attempt does not create duplicate ledger entries.
- An ambiguous payment does not release its reservation or trigger a paid fallback.
- Reconciliation is safe to invoke more than once.
- Recovery behavior is supported by actual tests and clearly states whether it covers object recreation, process restart, or multi-process execution.
- Test results identify which scenarios are mocked and which use a real database or external service.

---

## 6.3 — Durable Storage and Database Deployment Verification

**Priority:** P0  
**Owner:** Member 4; support from Member 1

**Deliverable:** `docs/PHASE6_DATABASE_AND_RECOVERY.md`

### Tasks
- Identify the actual database used by local tests, the demo, and deployment.
- Inspect schema initialization/migrations, transaction boundaries, foreign keys, uniqueness constraints, and indexes.
- Verify persistence of tasks, attempts, reservations, ledger records, idempotency results, and replay nonces.
- Test recovery using a genuinely new application process when feasible.
- If PostgreSQL is a release target, run the relevant suite against PostgreSQL rather than inferring compatibility from SQLite tests.
- Verify concurrent reservation and reconciliation behavior against the intended database.
- Document backup and restore procedures.
- Ensure routine recovery does not drop schemas or erase accounting records.
- Document the limits of SQLite in single-process and multi-worker configurations.

### Acceptance criteria
- The chosen release database is explicit.
- Database-specific claims match executed tests.
- Recovery steps preserve payment and ledger evidence.
- Backups are documented before any manual repair.
- PostgreSQL support is called “verified” only if a real PostgreSQL test run was performed.

---

## 6.4 — Seller Boundary, Provider Modes, and SSRF Review

**Priority:** P1  
**Owner:** Member 2

**Deliverable:** `docs/PHASE6_SELLER_SECURITY_REVIEW.md`

### Tasks
- Confirm all seller endpoints require valid payment verification before invoking paid business logic.
- Verify missing verifier/configuration, malformed payload, invalid proof, and provider outage behavior.
- Verify `SELLER_PROVIDER_MODE=fake` is deterministic and does not make unintended external calls.
- Verify live mode never silently falls back to fake responses.
- Re-review URL scheme and host validation, private/special IP blocking, mixed DNS answers, socket IP pinning, redirect revalidation, response size limits, and timeouts.
- Verify failures in peer-IP inspection or pinning fail closed.
- Review scraped content as untrusted input to inference; prevent it from being treated as system instructions.
- Check input/output schemas, concurrency limits, timeout behavior, and error sanitization.
- Check that sensitive authorization headers, API keys, and wallet material do not enter logs or error payloads.

### Acceptance criteria
- Seller code cannot execute protected provider logic before successful verification.
- Fake and live modes are explicit and observable.
- SSRF protections fail closed when their required safety checks cannot be completed.
- Security tests include malformed URLs, redirects, private IPs, mixed DNS, oversized responses, and provider failures.
- Findings are documented with severity and remediation status.

---

## 6.5 — Frontend Trust, Status Clarity, and Failure UX

**Priority:** P1  
**Owner:** Member 4

**Deliverable:** `docs/PHASE6_FRONTEND_TRUST_AND_UX.md`

### Tasks
- Inspect marketplace discovery, task planning, DAG preview, execution progress, result summary, and ledger views.
- Clearly distinguish:
  - `SIMULATED`
  - `PENDING RECONCILIATION`
  - `VERIFIED ON-CHAIN`
  - `VERIFIED FACILITATOR RECEIPT` (only when the actual verification method supports that claim)
  - `FAILED / NOT CHARGED`
  - `PAID / OUTPUT REJECTED`
- Ensure synthetic receipt identifiers never create misleading BaseScan links.
- Show service price and budget using authoritative backend values.
- Ensure remaining budget is not displayed as final while funds remain reserved in suspense.
- Explain task failure separately from payment failure.
- Provide useful UI states for insufficient budget, invalid plan, seller failure, timeout, reconciliation pending, and output-schema rejection.
- Check network errors, loading states, and empty states.
- Verify that the frontend bundle contains no secrets and that API base URLs are configured safely.

### Acceptance criteria
- A user can tell whether a displayed payment is simulated or verified.
- Cost totals match ledger amounts in atomic units.
- Pending payments are not represented as settled or refunded.
- The UI gives an understandable explanation for failed or blocked steps.
- `npm run build` passes, and relevant UI flows are exercised manually or through existing automated tests.

---

## 6.6 — Configuration, CORS, Secrets, and Dependency Hygiene

**Priority:** P1  
**Owner:** Setup Lead + Member 2 + Member 4

**Deliverable:** `docs/PHASE6_CONFIGURATION_AND_SECURITY.md`

### Tasks
- Audit `.env.example`, configuration parsing, `.gitignore`, Docker build contexts, and deployment templates.
- Confirm no real keys, wallet secrets, seed phrases, or provider tokens appear in tracked files or frontend assets.
- Rotate/revoke any credential known to have been exposed previously; do not copy it into reports or prompts.
- Restrict CORS origins for non-local deployments.
- Validate required environment variables at startup with safe, non-secret error messages.
- Ensure live mode fails closed when mandatory credentials or verifier endpoints are absent.
- Pin or bound critical dependency versions and record the supported Python/Node versions.
- Run available dependency and secret scans; report tools and exact results.
- Ensure logs do not dump payment payloads, signatures, full request bodies, or authorization headers.
- Keep test secrets separate from real testnet credentials.

### Acceptance criteria
- Local development and public deployment configurations are clearly separated.
- Public deployment cannot unintentionally start with wildcard CORS unless explicitly configured for a controlled environment.
- Secret scans and dependency checks have recorded results.
- No secret is printed in audit output.
- Unsupported or untested dependency combinations are documented.

---

## 6.7 — Controlled Base Sepolia Verification Gate (Optional, Explicitly Authorized)

**Priority:** P0 gate; execution is optional and separately authorized  
**Owner:** Member 1; Setup Lead review  
**Deliverable:** `docs/PHASE6_BASE_SEPOLIA_VERIFICATION.md`

**This workstream is a plan only. It does not authorize a transaction.**

### Stage A — Read-only preparation
- Review the current testnet network ID, token contract, seller recipient, payment amount, and facilitator/RPC configuration.
- Verify addresses against authoritative project configuration and appropriate official sources.
- Check wallet balance and required gas using read-only queries if configured.
- Confirm the signing key is supplied through a secure local secret mechanism and never printed.
- Review the transaction script and the exact expected side effects.
- Confirm that the test uses Base Sepolia only, not mainnet.
- Prepare a maximum spend limit, number of transactions, rollback/stop conditions, and evidence capture procedure.
- Do not broadcast a transaction during this stage.

### Stage B — Authorization checkpoint
Before any live transaction, obtain explicit authorization that specifies:
- The script or command to run.
- The intended network.
- The maximum testnet amount and number of transactions.
- Whether paid provider calls are permitted.
- The approved wallet configuration and stop conditions.

If authorization is not provided, keep this gate `BLOCKED / NOT RUN`.

### Stage C — Controlled execution, only after authorization
- Execute the approved test only.
- Capture the returned transaction hash without exposing wallet secrets.
- Retrieve the authoritative transaction receipt.
- Verify successful receipt status, token contract, recipient, exact amount, and matching ERC-20 `Transfer` event.
- Verify the resulting ledger record matches the verified transaction.
- Confirm duplicate submission/reconciliation cannot create duplicate ledger entries.
- Stop on any mismatch, unexpected network, unexpected recipient, or unexpected amount.

### Acceptance criteria
- The live gate is marked `VERIFIED IN LIVE ENVIRONMENT` only after authoritative receipt and transfer-log verification.
- The evidence includes the network, transaction hash, receipt status, token, recipient, amount, and matching ledger record.
- No private key or seed phrase is included in evidence.
- If not run, the report states `BLOCKED / NOT RUN` without implying live settlement succeeded.
- A live testnet success does not imply mainnet or production readiness.

---

## 6.8 — Reproducible Demo and Failure Scenarios

**Priority:** P1  
**Owner:** Setup Lead + all members

**Deliverable:** `docs/PHASE6_DEMO_RUNBOOK.md`

### Default demo
- Start backend and frontend using documented commands.
- Use deterministic fake provider mode.
- Show the catalog and prices:
  - `data_001`: 0.002 USDC
  - `scraping_001`: 0.003 USDC
  - `inference_001`: 0.004 USDC
- Preview a three-step DAG with independent scraping/data steps and dependent inference.
- Set a task budget of 0.050000 USDC.
- Execute the workflow and show the final result.
- Show the three ledger entries.
- Show total simulated spend of 0.009000 USDC and remaining budget of 0.041000 USDC.
- Show a clear `SIMULATED` label for synthetic receipts.

### Failure demonstration
Choose at least one deterministic safe scenario:
- Insufficient budget blocks execution before payment.
- Invalid plan/cycle is rejected before execution.
- Seller failure skips dependent steps without charging for skipped work.
- Ambiguous settlement remains pending and blocks fallback.
- Invalid seller output is rejected while confirmed payment evidence is preserved.

### Acceptance criteria
- Demo runs offline without paid API calls or blockchain broadcasts.
- Results are repeatable from a clean documented setup.
- Simulated evidence is clearly labeled in terminal output and UI.
- Failure scenario demonstrates a meaningful safety property.
- Demo script output is captured as generated evidence, not reconstructed manually.

---

## 6.9 — End-to-End Release Acceptance

**Priority:** P0  
**Owner:** Setup Lead + all members

**Deliverable:** `docs/PHASE6_ACCEPTANCE_MATRIX.md`

### Required test categories
1. Backend regression suite.
2. Frontend production build.
3. Registry and service-contract checks.
4. Buyer planning and DAG validation.
5. Budget reservation and insufficient-budget behavior.
6. Payment policy validation.
7. Settlement success and invalid-evidence rejection.
8. Reconciliation and idempotent recovery.
9. Durable storage and restart recovery.
10. Seller payment boundary and provider-mode behavior.
11. SSRF and input/output validation.
12. Frontend simulated/live evidence labeling.
13. Demo workflow and ledger reconciliation.
14. Configuration/secret hygiene.
15. Optional live Base Sepolia gate, only when authorized.

### Evidence classification
Use one of these exact labels for each result:
- `VERIFIED BY AUTOMATED TESTS`
- `VERIFIED BY CODE INSPECTION`
- `VERIFIED IN LIVE ENVIRONMENT`
- `MOCKED / SIMULATED`
- `NOT RUN`
- `BLOCKED`
- `FAILED`

Do not use “verified” without specifying the verification method.

### Acceptance criteria
- Every P0 item is passed or explicitly marked blocked with an owner and reason.
- Failed tests are not hidden by rerunning only the passing subset.
- The final report records exact commands, outputs, durations, and environment.
- No release claim exceeds the available evidence.

---

## 7. Recommended Execution Order

| Order | Workstream | Reason |
|---:|---|---|
| 1 | 6.0 Baseline reverification | Prevents changes based on stale or inaccurate reports |
| 2 | 6.1 Payment evidence/state machine | Highest trust and financial correctness risk |
| 3 | 6.2 Reconciliation/idempotency | Prevents duplicate charging and unresolved accounting |
| 4 | 6.3 Persistence/database | Validates durability assumptions |
| 5 | 6.4 Seller/provider security | Protects the payment-to-execution boundary |
| 6 | 6.6 Configuration and secrets | Reduces deployment and credential risk |
| 7 | 6.5 Frontend trust/UX | Makes the actual system state understandable |
| 8 | 6.8 Demo runbook | Creates repeatable judge-facing evidence |
| 9 | 6.7 Optional live testnet gate | Run only after preparation and explicit authorization |
| 10 | 6.9 Final acceptance | Consolidates actual evidence and limitations |

Parallelize only when ownership is clear and shared contracts are stable.

---

## 8. Release Gates

### Gate A — Baseline integrity
- [ ] Actual branch, HEAD, and worktree state recorded.
- [ ] Phase 5 untracked artifacts preserved.
- [ ] Full backend test suite freshly run.
- [ ] Frontend build freshly run.
- [ ] Fake-mode demo freshly run.

### Gate B — Payment correctness
- [ ] Live-mode settlement cannot accept synthetic evidence.
- [ ] Transaction hash alone cannot establish payment.
- [ ] Token, network, recipient, amount, and transfer log are validated.
- [ ] Ambiguous settlement remains pending.
- [ ] Output failure does not falsify payment history.

### Gate C — Recovery and duplicate protection
- [ ] Same idempotency key with same payload does not double-execute.
- [ ] Same key with different payload is rejected.
- [ ] Nonce replay is rejected durably.
- [ ] Reconciliation is idempotent.
- [ ] Pending reservations remain held until authoritative resolution.

### Gate D — Seller and deployment safety
- [ ] Seller business logic cannot run before required payment verification.
- [ ] Fake/live provider modes fail safely.
- [ ] SSRF checks fail closed.
- [ ] Secrets are absent from tracked files, logs, and client bundle.
- [ ] Public deployment CORS is restricted.
- [ ] Database choice and recovery steps are explicit.

### Gate E — Product and demonstration
- [ ] Simulated/live status is unmistakable.
- [ ] UI costs match authoritative backend/ledger values.
- [ ] Demo works offline.
- [ ] At least one failure scenario demonstrates a safety invariant.
- [ ] Evidence is captured from actual execution.

### Gate F — Optional live testnet
- [ ] Explicit authorization received.
- [ ] Approved network, wallet, amount, and stop conditions recorded.
- [ ] Transaction receipt and ERC-20 transfer verified.
- [ ] Ledger record matches verified on-chain evidence.
- [ ] No unexpected transactions or amounts occurred.

If Gate F is not authorized, it remains `BLOCKED / NOT RUN` and does not prevent a clearly labeled offline/demo release candidate.

---

## 9. Required Phase 6 Deliverables

Create these files in `docs/` as work progresses:

1. `PHASE6_BASELINE_AND_CHANGELOG.md`
2. `PHASE6_PAYMENT_EVIDENCE_AUDIT.md`
3. `PHASE6_RECONCILIATION_AND_IDEMPOTENCY.md`
4. `PHASE6_DATABASE_AND_RECOVERY.md`
5. `PHASE6_SELLER_SECURITY_REVIEW.md`
6. `PHASE6_FRONTEND_TRUST_AND_UX.md`
7. `PHASE6_CONFIGURATION_AND_SECURITY.md`
8. `PHASE6_BASE_SEPOLIA_VERIFICATION.md`
9. `PHASE6_DEMO_RUNBOOK.md`
10. `PHASE6_ACCEPTANCE_MATRIX.md`
11. `PHASE6_FINAL_ACCEPTANCE_REPORT.md`

Do not overwrite Phase 5 files. Keep the new deliverables untracked unless the user explicitly authorizes staging or committing.

---

## 10. Risk Register

| Risk | Severity | Mitigation | Owner |
|---|---|---|---|
| Synthetic receipt mistaken for on-chain payment | Critical | Explicit evidence types, UI badges, no fake explorer links | M1 + M4 |
| Ambiguous payment retried or fallback charged | Critical | Durable suspense state, idempotency, reconciliation tests | M1 + M3 |
| Seller executes before payment verification | Critical | Fail-closed route boundary and integration tests | M1 + M2 |
| Ledger and payment attempt diverge after crash | High | Durable transaction boundaries, reconciliation, recovery tests | M1 + M4 |
| SSRF/DNS rebinding bypass | High | Fail-closed IP pinning, redirect revalidation, adversarial tests | M2 |
| Secret exposure in repo/logs/bundle | Critical | Secret scanning, redaction, secure environment configuration | Setup Lead + all |
| Wildcard CORS in public deployment | High | Environment-specific trusted origins | Setup Lead |
| SQLite contention in multi-worker deployment | High | Use and test PostgreSQL for that deployment profile | M4 |
| Unsupported “production-ready” claims | High | Evidence labels and limitations section in final report | Setup Lead |
| Unapproved transaction or paid API call | Critical | Explicit authorization checkpoint and strict spend cap | All |
| Accidental Git mutation or loss of untracked docs | High | Read-only baseline; no mutation without permission | All |

---

## 11. Final Acceptance Report Template

The final Phase 6 report must include:

### Summary
- Release verdict: `ACCEPTED`, `ACCEPTED WITH LIMITATIONS`, or `BLOCKED`.
- Branch, HEAD, and working-tree state.
- Actual backend test result.
- Actual frontend build result.
- Actual fake-mode demo result.
- Live testnet gate status.

### Evidence
For every important claim, record:
- Claim.
- Evidence classification.
- Exact command/test or source path.
- Actual result.
- Limitations.
- Owner.

### Payment truth
- Simulated service calls and amounts.
- Actual on-chain transactions, if authorized and verified.
- Pending/reconciled payment attempts.
- Ledger consistency result.

### Known limitations
Explicitly list any untested PostgreSQL behavior, unrun live settlement, unverified production deployment, unresolved security findings, or unsupported claims.

### Final verdict guidance
- `ACCEPTED`: all required gates for the stated release scope pass.
- `ACCEPTED WITH LIMITATIONS`: local/offline scope passes, with material gates explicitly unrun or blocked.
- `BLOCKED`: a critical payment, security, data-integrity, or reproducibility defect remains unresolved.

Never mark the overall project production-ready solely because automated tests and a frontend build pass.

---

## 12. Immediate Next Action

**Start with Workstream 6.0 only.** Use read-only commands to verify the current repository state and capture fresh test/build/demo output. Do not begin broad refactoring until the baseline is known.

Do not stage or commit documentation, change branches, broadcast a transaction, use funded wallet credentials, or invoke paid external APIs without explicit authorization.

---

## Phase 6 Definition of Done

Phase 6 is complete when:
- [ ] The baseline is freshly reproduced and documented.
- [ ] Payment and execution state semantics are verified.
- [ ] Ambiguous settlement and duplicate/replay cases are tested.
- [ ] Persistence claims match the actual restart/database tests performed.
- [ ] Seller/provider security and configuration risks are reviewed.
- [ ] Frontend evidence labels and monetary displays are truthful.
- [ ] The offline demo and at least one failure scenario are repeatable.
- [ ] Optional live testnet settlement is either verified after authorization or clearly left blocked/not run.
- [ ] All required deliverables exist and the final acceptance verdict matches the evidence.
- [ ] No unauthorized Git, financial, or cross-owner actions occurred.

**Phase 6 principle:** Trust is not a UI label or a test count. It is a claim supported by verifiable evidence.
