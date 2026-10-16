# AGENTICA --- M2 Phase 2 Implementation Plan

## Seller Agents: Provider Integration, Security, Reliability, and Handoff

**Project:** AGENTICA --- Pay-per-Call Agent Economy\
**Tagline:** Discover. Pay. Execute. Trust.\
**Owner:** Member 2 --- Seller Agents\
**Repository:** `C:\AgentMarket`\
**Status:** Proposed plan; no task is complete until verified in the
repository.

> **Baseline note:** M2 Phase 1 Step 6 was reported as
> `COMPLETE WITH EXTERNAL BLOCKERS`, with 21 seller payment-integration
> tests, 37 seller unit/foundation tests, and 85 total regression tests
> passing. Live Base Sepolia settlement, live scraping, and live
> inference-provider execution were not verified. Re-check the actual
> branch, commit, working tree, and test output before beginning.

------------------------------------------------------------------------

## 1. Executive Summary

Phase 1 established the common seller execution lifecycle and three
seller endpoints. Phase 2 should evolve them from deterministic
demonstration services into controlled, provider-backed services while
preserving payment verification, request/response compatibility, schema
validation, idempotency context, resource bounds, and existing tests.

  -----------------------------------------------------------------------------------
  Seller            Service ID        Phase 1 baseline           Phase 2 target
  ----------------- ----------------- -------------------------- --------------------
  Data Seller       `data_001`        Deterministic validated    Provider adapter
                                      response                   with fake provider
                                                                 and one approved
                                                                 configured data
                                                                 source

  Scraping Seller   `scraping_001`    Input restrictions and     Controlled HTTP
                                      deterministic response     fetching,
                                                                 extraction,
                                                                 redirect/DNS/IP
                                                                 protections, and
                                                                 strict resource
                                                                 limits

  Inference Seller  `inference_001`   Prompt/token/temperature   Configured
                                      bounds and deterministic   inference-provider
                                      response                   adapter, normalized
                                                                 errors, output
                                                                 validation, and
                                                                 cost-aware execution
                                                                 bounds
  -----------------------------------------------------------------------------------

### Core invariant

**Payment not confirmed → seller business logic and provider calls must
not execute.**

A provider failure after payment has settled must not falsify payment
status, imply a refund, fabricate settlement evidence, or hide the real
settlement state.

------------------------------------------------------------------------

## 2. Phase 1 Baseline and Constraints

### 2.1 Reported baseline

-   Branch: `M2`
-   Reported commit: `2c2477f`
-   Reported verdict: `COMPLETE WITH EXTERNAL BLOCKERS`
-   Seller payment-integration suite: 21 passed
-   Seller unit/foundation suite: 37 passed
-   Full project suite: 85 passed
-   Live Base Sepolia settlement: **not tested**
-   Live scraping and inference providers: **deferred**
-   External dependencies: integration of Member 1's reviewed payment
    implementation, confirmed shared interfaces, and funded testnet
    wallets.

These are report-derived results, not guarantees about the current
checkout. Verify them before relying on them.

### 2.2 Seller-owned files

Expected seller scope includes:

-   `backend/sellers/routes.py`
-   `backend/sellers/common.py`
-   `backend/sellers/dependencies.py`
-   `backend/sellers/schemas.py`
-   `backend/sellers/data_seller.py`
-   `backend/sellers/scraping_seller.py`
-   `backend/sellers/inference_seller.py`
-   seller tests under `backend/tests/`
-   M2-specific documentation under `docs/`

Inspect the current repository before creating additional modules. Avoid
duplicate abstractions.

### 2.3 Ownership boundaries

  -----------------------------------------------------------------------
  Area                    Owner                   Rule for M2
  ----------------------- ----------------------- -----------------------
  Seller services,        Member 2                Implement within
  provider adapters,                              seller-owned scope
  seller tests                                    

  `backend/payments/` and Member 1                Do not modify without
  settlement engine                               explicit agreement

  Buyer and registry      Member 3                Coordinate contracts;
                                                  do not implement their
                                                  modules

  Ledger, persistence,    Member 4                Coordinate metadata; do
  dashboard                                       not implement their
                                                  modules

  Shared config, router,  Setup Lead / agreed     Obtain approval before
  schemas, integration    owner                   changes
  decisions                                       

  Main branch and         Setup Lead / team       No unilateral merge or
  cross-team merge        workflow                branch rewriting
  -----------------------------------------------------------------------

### 2.4 Non-negotiable safeguards

-   Preserve the established payment-verification sequence.
-   Do not invent payment helper names, receipt fields, status values,
    or verifier semantics.
-   A non-empty transaction hash or receipt ID alone is not universal
    proof of settlement finality. Validate actual contract semantics.
-   Do not trust schema-level URL checks as complete SSRF protection.
-   Do not log API keys, payment payloads, authorization headers,
    private keys, or sensitive raw prompts.
-   Do not silently fall back from live mode to fake mode.
-   Do not change service IDs, prices, pay-to addresses, chain/token
    configuration, or public schemas without approved coordination.
-   Do not commit, push, merge, rebase shared branches, force-push, or
    change branches without authorization.

------------------------------------------------------------------------

## 3. Phase 2 Goals and Non-Goals

### Goals

1.  Define typed, injectable provider interfaces for data, scraping, and
    inference.
2.  Keep deterministic fake providers for offline tests.
3.  Add explicitly configured real-provider paths.
4.  Enforce input/output schemas, timeouts, response-size bounds,
    concurrency limits, and sanitized errors.
5.  Make provider mode and execution outcomes observable without
    exposing secrets.
6.  Verify the integrated seller/payment contract and coordinate
    buyer/registry/ledger integration.
7.  Keep the default test suite deterministic and network-independent.

### Non-goals

Phase 2 does not authorize: - Rewriting the payment engine or editing
`backend/payments/`. - Implementing buyer orchestration, registry,
ledger, or dashboard modules. - Arbitrary URL fetching, unrestricted
crawling, browser rendering, or downloaded-code execution. - Arbitrary
LLM tool execution, shell execution, or local-file access. - New chains,
tokens, payment models, or unapproved pricing changes. - Claiming live
interoperability, live provider execution, or on-chain success from
mocked tests.

------------------------------------------------------------------------

## 4. Stage 0 --- Repository Audit and Contract Freeze

**Objective:** Establish the actual starting point and prevent work
against stale assumptions.

### Tasks

1.  Inspect `git status`, current branch, HEAD, remotes, and recent
    commits.
2.  Preserve all existing modifications; do not reset, clean, or
    overwrite work.
3.  Read `docs/TEAM_WORKFLOW.md`, `docs/DECISION.md`, `docs/MEMORY.md`,
    Phase 1 reports, shared schemas, seller schemas, and current tests.
4.  Confirm whether M2 work has been reviewed or integrated through the
    team's approved process.
5.  Inspect the actual merged payment-verifier API and receipt
    semantics. Do not rely only on a previous inspection of another
    remote branch.
6.  Record current route paths, request/response schemas, service IDs,
    prices, pay-to configuration, timeout behavior, and seller error
    mappings.
7.  Run the current baseline commands and capture their actual output.

``` bash
python -m pytest backend/tests/test_sellers_payment_integration.py -v
python -m pytest backend/tests/test_sellers.py backend/tests/test_sellers_foundation.py -v
python scripts/run_tests.py
```

### Deliverable

`docs/M2_PHASE2_STAGE0_BASELINE_AUDIT.md`

### Exit criteria

-   Actual branch, commit, working-tree status, and test results
    documented.
-   Seller contracts and external dependencies listed.
-   Placeholder configuration values identified and referred to the
    responsible owner.
-   No unrelated files modified.

------------------------------------------------------------------------

## 5. Stage 1 --- Provider Interfaces and Configuration

**Objective:** Separate seller business logic from vendor-specific SDKs
and external network calls.

### Proposed structure

Treat this as a proposal; adapt to existing conventions and avoid
unnecessary modules.

``` text
backend/sellers/
  providers/
    interfaces.py
    errors.py
    data/
      fake.py
      configured_provider.py
    scraping/
      fetcher.py
      safety.py
      parser.py
    inference/
      fake.py
      configured_provider.py
```

### Requirements

-   Typed request/result models and async-compatible interfaces for
    I/O-bound providers.
-   A normalized exception hierarchy for configuration missing, timeout,
    rate limit, upstream failure, rejected request, and invalid provider
    response.
-   Dependency injection for fake and configured providers.
-   Explicit `fake/demo` versus `live` mode.
-   Live mode fails clearly when required configuration is missing; no
    silent fake fallback.
-   Secrets come from environment/configuration or the established
    secret store.
-   No network calls during module import or test collection.
-   Timeouts, output limits, and concurrency bounds are configurable and
    validated.
-   Provider configuration must not mutate payment amount, recipient,
    network, or token.
-   Startup diagnostics may report provider mode, but never credential
    values.

### Tests

-   Fake provider injection works for all sellers.
-   Missing live configuration fails safely.
-   Provider selection is deterministic.
-   Importing modules does not initiate network calls.
-   Existing routes and payment enforcement remain unchanged.

### Deliverable

Provider interfaces, dependency wiring, configuration validation, and
focused tests.

### Exit criteria

All sellers can use fakes offline; live mode is explicit; no existing
API or payment gate regression.

------------------------------------------------------------------------

## 6. Stage 2 --- Data Seller Provider

**Objective:** Replace hard-coded demonstration behavior with a
provider-backed implementation without sacrificing deterministic tests.

### Tasks

1.  Audit the actual `DataSellerInput`, `DataSellerOutput`, and
    registry/catalog schema. Do not assume a ticker-only market-data
    example is the final domain requirement.
2.  Agree on one data source and its licensing, credentials, rate
    limits, and data freshness expectations.
3.  Define a provider interface such as
    `get_data(request) -> normalized_result`.
4.  Implement a deterministic fake provider for tests/demo mode.
5.  Implement one configured provider only after the source and
    credentials are approved.
6.  Normalize the provider response into the current public response
    schema.
7.  Validate numeric values, units/currency, timestamps, required
    fields, and stale/missing data where relevant.
8.  Add provenance fields only if compatible with the current
    API/catalog contract; otherwise coordinate a versioned schema
    change.
9.  Distinguish valid "no data" from provider failure.
10. Define bounded handling for timeout, rate limit, malformed upstream
    output, and missing configuration.
11. Keep all provider calls behind the established payment gate.

### Tests

-   Valid provider response
-   Missing record / valid no-data result
-   Missing required fields
-   Wrong types and malformed response
-   Timeout and rate limit
-   Missing live credentials
-   Output schema validation
-   Payment failure results in zero provider calls

### Exit criteria

Offline tests are deterministic; configured-provider behavior is
isolated behind mocks or opt-in integration tests; all returned success
payloads match the agreed schema.

------------------------------------------------------------------------

## 7. Stage 3 --- Scraping Seller: Safe Fetching and Extraction

**Objective:** Introduce controlled fetching without turning the service
into an SSRF or resource-exhaustion primitive.

### Security requirement

Schema-level URL validation is only the first layer. The fetcher must
validate the destination actually used for the connection and every
redirect destination. DNS rebinding and redirects can bypass checks that
happen only before connection.

### Tasks

1.  Freeze the request contract and supported content types.
2.  Use a dedicated HTTP client with connect, read, and total timeouts.
3.  Set connection limits and strict response-byte and extracted-text
    limits.
4.  Allow only approved HTTP/HTTPS schemes and approved ports.
5.  Normalize hostnames and reject unsafe URL forms, including embedded
    credentials where not required.
6.  Reject loopback, private, link-local, multicast, unspecified,
    reserved, and metadata destinations for IPv4 and IPv6.
7.  Bind destination validation to the actual connection to avoid a
    check-then-connect DNS gap.
8.  Disable automatic redirects or follow redirects manually with a
    strict count limit.
9.  Revalidate scheme, host, resolved IP, port, and destination policy
    at every redirect hop.
10. Do not forward caller credentials, cookies, or authorization headers
    to arbitrary destinations.
11. Stream response bodies and stop once the size limit is reached.
12. Accept only explicitly supported content types; reject
    unsupported/binary responses unless separately approved.
13. Parse content with bounded processing. Do not execute JavaScript,
    render pages, or run downloaded content.
14. Treat extracted page content as untrusted data. Prompt-injection
    text in a page must not become an instruction to the seller or any
    model.
15. Return only agreed metadata; never expose internal network addresses
    or sensitive resolver details.
16. Add unit tests for URL policy and mock-transport tests for
    redirects, body limits, status codes, and errors.
17. Keep live public-target tests opt-in and separate from normal CI.

### Required negative tests

-   `file://`, `ftp://`, and unsupported schemes
-   localhost/internal hostnames
-   IPv4 and IPv6 loopback, private, link-local, and metadata targets
-   unusual numeric IP forms and URL user-info tricks
-   public URL redirecting to a blocked destination
-   redirect loop and redirect-count overflow
-   DNS answers changing between validation and connection
-   oversized response and oversized extracted text
-   slow response and timeout
-   unsupported content type
-   malformed HTML/parser failure
-   upstream 4xx/5xx and rate limit
-   page content containing prompt-injection instructions

### Exit criteria

Destination checks are enforced at connection time; redirects are
revalidated; response bytes, text, redirects, and duration are bounded;
tests demonstrate blocked destinations are not contacted; no network
call occurs before payment confirmation.

------------------------------------------------------------------------

## 8. Stage 4 --- Inference Seller: Configured Model Provider

**Objective:** Add bounded inference while keeping the model unable to
execute arbitrary actions.

### Tasks

1.  Confirm the existing input/output schema and current
    prompt/token/temperature limits.
2.  Define an inference provider interface and keep a deterministic fake
    implementation.
3.  Select one approved provider based on existing dependencies and team
    decisions; do not invent a provider or model choice without checking
    the repository.
4.  Configure model/provider identifiers server-side, not from arbitrary
    user-provided endpoints.
5.  Enforce prompt, token, temperature, timeout, concurrency, and
    output-size limits locally and at the provider where possible.
6.  Normalize provider output into the current response schema.
7.  Handle empty output, refusal, malformed output, context overflow,
    rate limiting, timeout, and provider outage.
8.  Sanitize provider exceptions; never return secret configuration, raw
    internal prompts, or hidden reasoning.
9.  Do not execute model-generated code or allow arbitrary tool, shell,
    file, or network access.
10. Add mocked provider tests; real provider tests must be opt-in.

### Retry and cost policy

Do not retry blindly. Provider calls may be billable. Any retry policy
needs a bounded attempt count, an overall deadline, and explicit billing
semantics. Start with no retry unless the provider's idempotency and
billing behavior are understood.

### Tests

-   Valid output and schema normalization
-   Empty/malformed output
-   Refusal and provider errors
-   Prompt and token boundaries
-   Timeout and rate limit
-   Missing credentials
-   Secret sanitization
-   No provider call on payment rejection

### Exit criteria

Live mode is explicit; outputs are schema-validated and bounded; errors
are sanitized; default tests never call the real provider.

------------------------------------------------------------------------

## 9. Stage 5 --- Shared Execution Lifecycle and Reliability

**Objective:** Apply consistent limits and outcomes across all sellers.

### Tasks

1.  Review `BaseSellerService` and preserve input validation, timeout
    handling, output validation, metrics, and sanitized exceptions.
2.  Ensure network-bound work is genuinely asynchronous or safely
    offloaded. `asyncio.wait_for` does not reliably terminate arbitrary
    blocking synchronous operations.
3.  Enforce an overall deadline across the entire provider operation.
4.  Limit concurrent requests with per-provider or per-seller
    semaphores.
5.  Standardize error categories for timeout, upstream failure, rate
    limit, invalid response, and missing configuration.
6.  Record request/correlation ID, execution duration, outcome, and
    output-validation status through existing hooks.
7.  Distinguish payment rejection, input rejection, provider failure,
    invalid provider output, and successful validated execution.
8.  Preserve the truth if a provider fails after payment has settled. Do
    not imply refund/reversal unless confirmed by the payment subsystem.
9.  Never fabricate settlement proof or remove the actual payment record
    because provider execution failed.
10. Coordinate idempotency semantics with Members 1 and 3. Forward the
    agreed key/context; do not create a conflicting cross-module policy.
11. Test cancellation, concurrency, timeout, schema failure, and
    sanitized errors.

### Exit criteria

All sellers use the common lifecycle; external calls have bounded time,
size, and concurrency; metrics are useful but contain no secrets;
existing payment tests remain green.

------------------------------------------------------------------------

## 10. Stage 6 --- Payment, Buyer, Registry, and Ledger Integration

**Objective:** Verify the actual shared contracts without rewriting
other members' modules.

### Member 1 --- Payments

Confirm against integrated code: - verifier method signature and payload
model - receipt type and terminal status semantics - whether receipt
creation guarantees confirmed settlement - replay/nonce behavior -
handling of pending or uncertain settlement - source and meaning of
`tx_hash` / `facilitator_receipt_id`

M2 must not edit `backend/payments/`. Report any mismatch and coordinate
with Member 1.

### Member 3 --- Buyer and Registry

Confirm: - service IDs, request/response schemas, prices, and timeout
expectations - registry metadata matches actual seller behavior - buyer
budget is not exceeded - behavior when payment settles but
seller/provider execution fails - retry/fallback behavior does not cause
unintended duplicate spending

### Member 4 --- Ledger and Dashboard

Agree which seller execution fields are required: request/correlation
ID, service ID, execution status, latency, provider mode, and safe error
category. Member 4 owns persistence/dashboard implementation; M2 should
expose only agreed fields.

### Setup Lead

Approve shared config, router, schema, and API contract changes and
coordinate integration.

### Testnet gate

Do not run live payment tests until: - payment implementation is
reviewed and integrated - Base Sepolia chain, USDC contract, amounts,
and seller recipient addresses are verified from approved
configuration - test wallets have appropriate test assets - secrets are
not stored in source, reports, prompts, or logs - the team approves the
low-value test and reconciliation process

### Exit criteria

Contract-level tests pass using mocks. Any live run is explicitly
labeled, records the actual transaction/environment safely, and is
reported separately from mock results. A non-empty proof string is not
treated as finality unless the integrated contract guarantees it.

------------------------------------------------------------------------

## 11. Stage 7 --- Test Matrix and Regression

  -----------------------------------------------------------------------
  Area                    Required cases          Expected result
  ----------------------- ----------------------- -----------------------
  Payment gate            Missing, empty,         Zero seller/provider
                          malformed, rejected,    executions
                          unavailable verifier    

  Payment policy          Wrong service, amount,  Rejected by established
                          chain, token, recipient payment boundary

  Receipt semantics       Missing receipt,        No false success;
                          invalid status, missing follows actual receipt
                          proof                   contract

  Input schema            Missing, malformed,     Rejected before
                          oversized, wrong types  provider call

  Provider mode           Fake, live, missing     Explicit mode; no
                          configuration           silent fake fallback

  Provider response       Missing fields, wrong   Rejected or normalized;
                          types, oversized output never mislabeled as
                                                  valid

  Timeout                 Connect/read/total      Bounded failure
                          deadline exceeded       

  Concurrency             Calls exceed configured Concurrency remains
                          limit                   bounded

  Scraping SSRF           Private/metadata IPs,   Blocked before
                          IPv6, redirects, DNS    prohibited destination
                          changes                 is contacted

  Inference safety        Oversized prompt, token Request bounded and
                          violation,              error classified
                          refusal/error           

  Error sanitization      Exception contains      Secret absent from
                          key/token/credentials   response and logs

  Idempotency/replay      Duplicate key or        Agreed shared
                          replayed payload        semantics; no
                                                  unintended duplicate
                                                  execution

  Interoperability        Unmodified compatible   Compatibility
                          x402 client             demonstrated by an
                                                  actual test

  Regression              Existing seller tests   No regression
                          and full suite          
  -----------------------------------------------------------------------

Run the existing commands and any new focused tests. Keep normal CI
network-independent. Use markers/environment gates for provider and
testnet tests. Do not weaken or remove security assertions to make tests
pass.

------------------------------------------------------------------------

## 12. Stage 8 --- Documentation, Demo, and Handoff

### Documents to create/update

-   `docs/M2_PHASE2_IMPLEMENTATION_PLAN.md` --- this plan
-   `docs/M2_PHASE2_STAGE0_BASELINE_AUDIT.md`
-   `docs/M2_PHASE2_PROVIDER_CONTRACTS.md`
-   `docs/M2_PHASE2_SECURITY_TEST_REPORT.md`
-   `docs/M2_PHASE2_INTEGRATION_REPORT.md`
-   `docs/M2_PHASE2_FINAL_VERIFICATION_REPORT.md`

Create reports as work happens; do not pre-fill them as completed.
Record exact commands, actual results, files changed, decisions, known
limitations, and blockers.

### Defensible demo flow

1.  Show service metadata consistent with the registry.
2.  Send a request without valid payment and show that no provider is
    called.
3.  Demonstrate the agreed verification path using a mock, clearly
    labeled, or an approved testnet payment.
4.  Show a provider-backed or explicitly labeled fake response.
5.  Show response schema validation.
6.  Show a provider failure without falsifying settlement status.
7.  Show safe execution metadata through the agreed shared contract.
8.  Confirm logs and output do not reveal secrets.

Never present mocked settlement or fake provider output as real
on-chain/live-provider activity.

------------------------------------------------------------------------

## 13. Execution Order and Dependencies

  ---------------------------------------------------------------------------------
  Order             Stage                   Dependency        Exit gate
  ----------------- ----------------------- ----------------- ---------------------
  0                 Audit and contract      Current checkout  Baseline and
                    freeze                                    interfaces verified

  1                 Provider                Stage 0           Injectable fakes; no
                    interfaces/config                         API regression

  2                 Data provider           Stage 1 and       Provider tests/schema
                                            approved source   pass

  3                 Scraping fetcher        Stage 1           SSRF/resource-bound
                                                              tests pass

  4                 Inference provider      Stage 1 and       Mocked provider tests
                                            approved provider pass

  5                 Shared lifecycle        Stages 2--4       Timeouts,
                                                              concurrency, errors,
                                                              metrics verified

  6                 Cross-team integration  Reviewed shared   Integration tests
                                            contracts         pass; live test
                                                              separately gated

  7                 Regression              Stages 0--6       Full suite passes

  8                 Documentation/handoff   Actual            Reports accurate and
                                            implementation    reviewed
                                            results           
  ---------------------------------------------------------------------------------

Offline provider work should not wait for testnet funding. Live
settlement testing must wait for the external prerequisites.

------------------------------------------------------------------------

## 14. Definition of Done

Phase 2 may be marked `COMPLETE` only when all applicable items are
demonstrated.

### Architecture and behavior

-   [ ] Provider interfaces are used by seller services.
-   [ ] Fake providers are deterministic and injectable.
-   [ ] Live mode is explicit; missing configuration fails safely.
-   [ ] Public contracts remain compatible or approved changes are
    documented.
-   [ ] Data seller configured-provider path is tested.
-   [ ] Scraping connection and redirect destinations are checked
    safely.
-   [ ] Inference provider path is bounded and output-validated.
-   [ ] All external calls have timeout, concurrency, and size limits.
-   [ ] Provider errors are classified and sanitized.

### Payment correctness

-   [ ] No provider call occurs before valid confirmed settlement.
-   [ ] Service/price/network/token/recipient rules match the integrated
    contract.
-   [ ] Receipt and proof semantics are verified against actual code.
-   [ ] Provider failure after settlement is represented truthfully.
-   [ ] Replay/idempotency follows the agreed cross-module contract.

### Tests and handoff

-   [ ] Existing seller tests pass.
-   [ ] New provider, SSRF, timeout, output-validation, and sanitization
    tests pass.
-   [ ] Full regression suite passes.
-   [ ] Default CI is network-independent.
-   [ ] Live tests are opt-in and reported separately.
-   [ ] No secrets appear in logs or docs.
-   [ ] Cross-team interfaces are reviewed.
-   [ ] Git actions follow the team workflow and authorization rules.

If local implementation and tests pass but live provider/testnet
prerequisites remain unavailable, report
`COMPLETE WITH EXTERNAL BLOCKERS`, not full end-to-end completion.

------------------------------------------------------------------------

## 15. Risks and Mitigations

  -----------------------------------------------------------------------
  Risk                                Mitigation
  ----------------------------------- -----------------------------------
  Actual payment API differs from     Inspect integrated Member 1 code
  assumptions                         and confirm receipt semantics

  SSRF through redirect/DNS rebinding Validate the destination at
                                      connection time and revalidate
                                      every redirect

  Blocking work survives timeout      Prefer async clients or bounded
                                      executor isolation

  Provider response shape changes     Normalize and validate every result

  Fake output mistaken for live       Explicit provider mode and truthful
  output                              metadata

  Retries create extra cost           No retries by default; bounded
                                      policy only after billing semantics
                                      are understood

  Logs expose secrets                 Redacted structured logging and
                                      leakage tests

  Cross-module contract drift         Freeze contracts and obtain owner
                                      reviews

  Placeholder recipient values        Verify through approved
                                      configuration; never assume
                                      placeholder addresses are usable

  Scope creep                         Follow stage gates; defer stretch
                                      goals
  -----------------------------------------------------------------------

### Defer until the core path is stable

-   Multi-provider routing/fallback
-   Advanced caching
-   Streaming inference
-   Browser rendering or JavaScript execution for scraping
-   Broad crawling
-   Arbitrary model tool execution
-   New chains/tokens/payment models
-   Advanced reputation scoring

------------------------------------------------------------------------

## 16. Antigravity Execution Protocol

Implement **one stage at a time** using this plan as the source of
truth.

Before editing: 1. Inspect branch, status, recent commits, and relevant
files. 2. Read team workflow and current shared contracts. 3. Identify
seller-owned versus shared files. 4. Report interface mismatches before
cross-module changes. 5. Preserve all existing user changes.

During implementation: - Stay on the authorized branch. - Keep the patch
limited to the active stage. - Do not edit payment, buyer, registry,
ledger, dashboard, shared router, or shared schemas without explicit
owner approval. - Do not commit, push, merge, rebase shared branches,
force-push, or change branches unless explicitly authorized. - Do not
invent helper names, receipt fields, statuses, SDKs, or configuration
names; inspect and confirm first. - Add tests with each feature. - Run
focused tests after each stage and the full regression suite at defined
gates. - Never weaken a security test simply to pass. - Do not call live
providers or spend testnet funds without explicit configuration and
approval. - Document limitations honestly.

At each stage end, report: 1. Verdict: `COMPLETE`,
`COMPLETE WITH EXTERNAL BLOCKERS`, or `INCOMPLETE` 2. Files changed 3.
Decisions and rationale 4. Tests run and exact results 5. Security
checks 6. Remaining issues/external dependencies 7. Git status, without
unauthorized Git actions 8. The next safe stage

------------------------------------------------------------------------

## 17. Final Status Template

Fill this only after implementation; do not pre-mark tasks complete.

``` text
M2 Phase 2 Verdict:
[INCOMPLETE / COMPLETE WITH EXTERNAL BLOCKERS / COMPLETE]

Branch and commit:
Working tree:
Stage 0 audit:
Stage 1 provider contracts:
Stage 2 data seller:
Stage 3 scraping seller:
Stage 4 inference seller:
Stage 5 lifecycle/reliability:
Stage 6 cross-team integration:
Stage 7 regression:
Stage 8 documentation/handoff:

Focused seller tests:
Full regression tests:
Live provider tests:
Live Base Sepolia settlement:
External blockers:
Known security limitations:
Files changed:
Next action:
```

**End of plan.**
