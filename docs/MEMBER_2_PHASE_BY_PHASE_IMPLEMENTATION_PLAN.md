# DI-06 — Member 2 Phase-by-Phase Implementation Plan
## Data Seller, Scraping Seller, and Inference Seller

**Project:** Pay-per-Call Agent Economy  
**Track:** Decentralized Intelligence Track — DI-06  
**Role:** Member 2 — Seller Agents  
**Branch:** `feature/sellers`  
**Target network:** Base Sepolia testnet  
**Protocol:** Official x402 v2 integration  
**Suggested backend:** Existing project backend, expected to be Python/FastAPI if that is what the repository currently uses  
**Time limit:** 24-hour hackathon  
**Document purpose:** A phase-gated engineering plan for implementing Member 2's work in a safe, testable order.

> **Important:** This is a plan, not proof that any feature exists or has passed tests. Inspect the current repository before creating or modifying files. Use the repository and agreed shared contracts as the source of truth. Verify current x402 v2 SDK APIs and settlement behavior against official documentation before coding.

---

# 1. Mission

Member 2 builds three distinct paid seller services:

1. **Data Seller** — returns structured data.
2. **Scraping Seller** — extracts bounded information from permitted public webpages.
3. **Inference Seller** — performs a bounded inference task such as summarization or classification.

The three services may live in the same backend process and repository, but each must have its own:
- Stable service ID.
- HTTP endpoint.
- Input model and input JSON Schema.
- Output model and output JSON Schema.
- Description and capability.
- Canonical listed price.
- Registry entry.
- Tests and observable execution outcomes.

All three endpoints must use the official x402 v2 server integration and be callable by an unmodified compatible x402 v2 client.

## 1.1 Member 2 does not own

| Area | Owner | Member 2's integration responsibility |
|---|---|---|
| Buyer planning and orchestration | Member 3 | Provide accurate service metadata, endpoint paths, and schemas |
| Registry API | Member 3 | Supply/confirm seller records using the shared contract |
| Buyer payment authorization and budget reservations | Member 1 | Integrate with the agreed x402 lifecycle; do not implement buyer-side signing |
| Payment policy and settlement verification | Member 1 | Coordinate failure behavior and evidence requirements |
| Database migrations and authoritative ledger | Member 4 | Emit agreed execution metadata; do not create a separate ledger |
| Dashboard and reputation presentation | Member 4 | Provide trustworthy service outcomes and latency inputs |

---

# 2. Phase Overview

| Phase | Name | Priority | Main result | Gate before next phase |
|---|---|---|---|---|
| Phase 0 | Repository and contract audit | P0 | Existing code and dependencies understood | Shared contracts and blockers documented |
| Phase 1 | Shared seller foundation | P0 | Common conventions and test structure | Schemas and error conventions agreed |
| Phase 2 | Data Seller | P0 | Structured data endpoint works locally | Unit/schema tests pass |
| Phase 3 | Scraping Seller | P0/P2 security-critical | Safe bounded scraping endpoint works | SSRF, timeout, and size-limit tests pass |
| Phase 4 | Inference Seller | P0 | Bounded inference endpoint works | Output, timeout, and fallback tests pass |
| Phase 5 | x402 v2 integration | P0 | Three sellers support paid calls | Official SDK lifecycle and interoperability verified |
| Phase 6 | Registry and ledger integration | P1 | Buyer can discover sellers and ledger receives events | Shared contracts agree end-to-end |
| Phase 7 | Security and interoperability hardening | P1/P2 | Replay, failures, and unsafe inputs tested | Required regression tests pass |
| Phase 8 | Deployment and demo | P1 | Public HTTPS sellers and complete demo | Deployed smoke test and team acceptance pass |

**Scheduling principle:** Do not wait until all business handlers are complete before testing payment integration. The earliest high-risk milestone is one seller working end-to-end through the official x402 v2 flow.

---

# 3. Phase 0 — Repository and Contract Audit

**Priority:** P0  
**Suggested time:** 30–60 minutes  
**Coding status:** No new implementation code during this phase.

## Objective

Understand the actual repository, avoid duplicate modules, and resolve shared interface questions before implementation.

## Tasks

### 0.1 Inspect the current repository

Inspect, where present:
- Backend entry point and router registration.
- Existing seller or service modules.
- Pydantic models or equivalent request/response models.
- Existing x402 dependencies and integration code.
- Registry definitions or seed data.
- Database/persistence interfaces.
- Logging and error handling.
- Test framework and test conventions.
- Dependency files and lockfiles.
- `.env.example` or equivalent configuration template.
- Docker and deployment configuration.

Do not assume that a suggested file or module exists.

### 0.2 Read shared project documents

Locate and inspect the relevant available versions of:
- `MEMBER_2_DETAILED_IMPLEMENTATION_PLAN.md`
- `MEMBER_2_SELLER_AGENTS_IMPLEMENTATION.md`
- `DI06_TEAM_OF_4_IMPLEMENTATION_MASTER_PLAN.md`
- `API_CONTRACTS.md`
- `DATABASE_SCHEMA.md`
- `PAYMENT_ENGINE_IMPLEMENTATION.md`
- `BUYER_AND_REGISTRY_IMPLEMENTATION.md`
- `LEDGER_DASHBOARD_IMPLEMENTATION.md`
- Overall architecture and security specification.

If documents conflict, report the conflicting definitions and ask the relevant owners to agree on a canonical version. Do not silently change shared contracts.

### 0.3 Freeze the seller contracts

Agree with Members 1, 3, and 4 on:
- Service IDs.
- Endpoint paths.
- Category enum.
- Request and response field names.
- JSON Schema representation.
- Price field and atomic-unit convention.
- Network and payment configuration source.
- Call ID/idempotency convention.
- Error format and status vocabulary.
- Execution event fields expected by the ledger.
- Seller failure behavior under the selected x402 lifecycle.

Suggested stable service IDs:
- `data.lookup.v1`
- `scraping.extract.v1`
- `inference.summarize.v1`

These IDs are suggestions; keep existing agreed IDs if already defined.

### 0.4 Verify x402 v2 documentation

Use official documentation as the source for protocol APIs:
- x402 documentation: https://www.x402.org/
- Facilitator reference: https://x402.org/facilitator

Confirm:
- Exact SDK package/version compatible with the existing backend.
- Official server integration pattern.
- Supported scheme and network configuration.
- Challenge and verification flow.
- Settlement timing relative to the seller handler.
- Error/timeout behavior.
- Replay guarantees.
- Settlement evidence exposed to application code.

Do not fabricate SDK imports or method names. If a detail cannot be verified, mark it unresolved.

## Deliverables

- Repository audit.
- List of existing seller components.
- Shared-contract checklist.
- x402 SDK verification notes.
- List of blockers and decisions required.

## Acceptance criteria

- [ ] Existing code has been inspected.
- [ ] Shared seller contracts are agreed or clearly marked unresolved.
- [ ] Ownership boundaries with Members 1, 3, and 4 are clear.
- [ ] The x402 SDK and settlement lifecycle are not based on guesses.
- [ ] No application files have been changed during this audit.

---

# 4. Phase 1 — Shared Seller Foundation

**Priority:** P0  
**Suggested time:** 45–75 minutes

## Objective

Establish consistent patterns for all seller modules before implementing the business logic.

## Tasks

### 1.1 Create or reuse the seller module structure

Use the existing repository layout if it already provides an appropriate structure. Otherwise, a possible layout is:

```text
backend/app/sellers/
  common.py
  data/
    router.py
    schemas.py
    service.py
  scraping/
    router.py
    schemas.py
    service.py
  inference/
    router.py
    schemas.py
    service.py
  tests/
    test_data_seller.py
    test_scraping_seller.py
    test_inference_seller.py
    test_seller_x402.py
    test_seller_security.py
```

### 1.2 Establish shared conventions

Define or reuse:
- Request validation conventions.
- Response model conventions.
- Safe error envelope.
- UTC timestamp convention.
- Latency measurement convention.
- Request/call ID propagation.
- Logging format and redaction.
- Maximum request-size policy.
- Configuration loading pattern.
- Test fixtures and test naming.

Do not introduce a new logging library, schema library, or configuration system if the repository already has an appropriate one.

### 1.3 Define common errors

Use the existing API contract if one is defined. Otherwise, propose a simple structured format to the team before implementing it.

Illustrative error:

```json
{
  "error": {
    "code": "INVALID_INPUT",
    "message": "The request does not match this service's input requirements."
  }
}
```

Never expose stack traces, private configuration, payment authorization headers, or secrets.

### 1.4 Define service-level limits

Agree on reasonable limits for:
- Input string length.
- Request body size.
- List/item count.
- Network timeouts.
- Maximum output size.
- Concurrent work.
- Retry behavior.

Keep limits in validated configuration where appropriate, not scattered as inconsistent constants.

## Files

Create or modify only after Phase 0 confirms the actual repository structure. Likely areas are common seller helpers, configuration references, and test scaffolding.

## Tests

- Request/response model validation works.
- Error serialization follows the shared contract.
- Timing helper produces non-negative latency.
- Secret redaction is applied to logs.
- Seller modules can be imported and registered without duplicate routes.

## Acceptance criteria

- [ ] Shared conventions are documented.
- [ ] All three seller modules follow the same conventions.
- [ ] No duplicate configuration or error framework has been introduced.
- [ ] A minimal test can run using the project's existing test command.

---

# 5. Phase 2 — Data Seller

**Priority:** P0  
**Suggested time:** 60–90 minutes

## Objective

Implement a deterministic structured-data service with a clear schema and trustworthy provenance.

## Suggested endpoint

`POST /seller/data/lookup`

Use the existing agreed path if one is already defined.

## Illustrative request

```json
{
  "query": "books about machine learning",
  "limit": 5
}
```

## Illustrative response

```json
{
  "service_id": "data.lookup.v1",
  "items": [
    {
      "label": "Example item",
      "value": "Example value",
      "source": "https://example.org/",
      "observed_at": "2026-10-16T12:00:00Z"
    }
  ],
  "count": 1
}
```

These are examples, not a replacement for the shared API contract.

## Tasks

### 2.1 Define the request schema

Include:
- A required non-empty query.
- A bounded maximum query length.
- A bounded `limit`.
- Explicit handling of missing or unsupported fields.

### 2.2 Define the response schema

Specify:
- Stable service ID.
- List of structured items.
- Item fields and their types.
- Provenance/source fields where applicable.
- Observation timestamp where applicable.
- Count equal to the number of returned items.

### 2.3 Implement the data source

For the hackathon, prefer a small deterministic dataset or a documented, stable source. Avoid making the service dependent on an unreliable external API before the basic path works.

- Normalize the query consistently.
- Apply deterministic filtering/search.
- Return a stable ordering.
- Enforce the requested limit and a server-side maximum.
- Clearly label demo or seeded data.
- Never claim seeded data is live.

### 2.4 Add the endpoint

- Use the existing router conventions.
- Validate the request before business logic runs.
- Call the data service.
- Validate the response model.
- Record latency and safe outcome metadata.
- Keep payment integration for Phase 5 unless an existing pattern is already in place.

### 2.5 Publish the service contract

Provide Member 3 with:
- Service ID.
- Endpoint path.
- Description and capability.
- Request JSON Schema.
- Response JSON Schema.
- Canonical price field/value from the shared configuration.
- Network and pay-to configuration source.

Do not independently invent or duplicate payment terms.

## Required tests

- Valid query.
- Empty query.
- No matching data.
- Limit at minimum and maximum.
- Limit above maximum.
- Count equals returned item count.
- Response validates against published schema.
- Provenance is truthful.
- Handler errors are mapped safely.

## Deliverable

A locally callable Data Seller endpoint with stable, schema-valid JSON and tests.

## Gate to Phase 3

- [ ] Request and response schemas are finalized.
- [ ] Unit tests pass.
- [ ] Member 3 confirms the contract is consumable.
- [ ] Seeded/demo data is labelled honestly.

---

# 6. Phase 3 — Scraping Seller

**Priority:** P0 functionality; P2 security-critical  
**Suggested time:** 90–150 minutes

## Objective

Build a safe, bounded public-webpage extraction service. The URL is untrusted input, so this phase requires explicit security tests.

## Suggested endpoint

`POST /seller/scraping/extract`

## Illustrative request

```json
{
  "url": "https://books.toscrape.com/",
  "max_items": 5
}
```

## Illustrative response

```json
{
  "service_id": "scraping.extract.v1",
  "source_url": "https://books.toscrape.com/",
  "title": "Books to Scrape",
  "text_excerpt": "A short extracted excerpt...",
  "items": [],
  "fetched_at": "2026-10-16T12:00:00Z"
}
```

Finalize the item schema based on the extraction capability you actually implement.

## Tasks

### 3.1 Define request and response models

- Accept only the fields required for the scraping task.
- Bound URL length and `max_items`.
- Define maximum excerpt length and item count.
- Return the final source URL only after validating redirects.
- Use a UTC timestamp for actual fetch time.
- Ensure the response model matches the published JSON Schema.

### 3.2 Implement URL policy

For the first demo, use an explicit allowlist of approved hosts. Avoid arbitrary public URLs until protections are complete.

Reject:
- Unsupported URL schemes.
- URLs containing embedded credentials.
- Localhost and loopback addresses.
- Private, link-local, multicast, reserved, and cloud metadata destinations.
- Disallowed ports where the deployment policy restricts ports.
- Redirects to disallowed hosts or IP ranges.

### 3.3 Implement SSRF protections

- Parse and normalize the URL.
- Validate the hostname and DNS-resolved addresses.
- Block prohibited destination IP ranges.
- Re-check every redirect target.
- Apply a strict redirect limit.
- Consider DNS rebinding and validate the actual connection destination where the networking stack permits.
- Prefer a controlled egress policy or proxy if available.

**Do not assume URL parsing alone prevents SSRF.**

### 3.4 Implement safe fetching

- Use an existing maintained HTTP client where possible.
- Set connect and read timeouts.
- Limit response bytes while downloading, not only after the full response is loaded.
- Validate content type.
- Respect robots.txt, website terms, and rate limits.
- Do not bypass login, CAPTCHA, paywall, or access controls.
- Use a descriptive User-Agent.
- Do not fetch unbounded linked resources or execute JavaScript.

### 3.5 Parse and extract

- Use an existing maintained HTML parser if available.
- Remove script/style content from extracted text.
- Extract only the fields described by the service contract.
- Limit item count and text length.
- Treat webpage text as untrusted content.
- Do not follow instructions embedded in fetched pages.
- Avoid returning entire pages or unnecessary HTML.

### 3.6 Handle failures

Return safe, structured errors for:
- Disallowed host.
- Invalid URL.
- Timeout.
- Unsupported content type.
- Oversized response.
- Fetch failure.
- Parse failure.

Coordinate payment semantics with Member 1. Do not independently label a failure `failed_and_not_charged` unless the payment lifecycle and settlement evidence support it.

## Required tests

- Approved public demo host.
- Disallowed hostname.
- Localhost and private IP.
- Redirect to private IP.
- Unsupported URL scheme.
- Embedded credentials.
- Timeout.
- Oversized response.
- Invalid content type.
- Malformed HTML.
- Output-size and item-count limits.
- Redirect limit.
- No script execution.
- Safe error responses.
- Schema validation.

## Deliverable

A bounded, SSRF-resistant scraping endpoint that returns structured, schema-valid results.

## Gate to Phase 4

- [ ] Approved-host happy path works.
- [ ] Unsafe destinations and redirects are blocked.
- [ ] Timeout and response-size limits are enforced.
- [ ] Security tests pass.
- [ ] Website policy restrictions are respected.

---

# 7. Phase 4 — Inference Seller

**Priority:** P0  
**Suggested time:** 60–120 minutes

## Objective

Implement a narrow, predictable inference service. Begin with summarization rather than an open-ended autonomous agent.

## Suggested endpoint

`POST /seller/inference/summarize`

## Illustrative request

```json
{
  "text": "A short passage to summarize.",
  "style": "concise",
  "max_words": 100
}
```

## Illustrative response

```json
{
  "service_id": "inference.summarize.v1",
  "summary": "A concise summary of the supplied text.",
  "language": "en",
  "word_count": 6
}
```

The exact schema must specify allowed styles, maximum input size, output bounds, and how language is determined.

## Tasks

### 4.1 Define schemas

- Required non-empty text.
- Maximum input length.
- Enumerated style values.
- Bounded maximum word count.
- Response summary and metadata.
- Clear behavior for empty or unsupported inputs.

### 4.2 Implement a provider adapter

Inspect existing dependencies first. Reuse the configured provider if one is already part of the project and appropriate.

- Keep provider-specific code behind a small adapter.
- Keep API credentials server-side.
- Set connection/read timeouts.
- Bound input and output.
- Handle rate limits and provider errors.
- Do not expose arbitrary tools or URL fetching to callers.
- Treat user text as content, not as instructions to change payment policy or seller configuration.

### 4.3 Define fallback behavior

If an inference provider is not available:
- Use a deterministic extractive fallback only if it is useful and clearly disclosed, or
- Return a truthful service-unavailable error.

Never claim a real model generated output when a deterministic fallback was used.

### 4.4 Validate output

- Normalize provider output.
- Enforce the requested maximum word count using a documented method.
- Validate the final response model.
- Avoid returning raw provider payloads.
- Record latency and a safe outcome code.

## Required tests

- Valid summary.
- Empty text.
- Oversized input.
- Unsupported style.
- Provider timeout.
- Provider error.
- Malformed provider response.
- Output limit.
- Missing provider configuration.
- Secret leakage.
- Response-schema validation.

## Deliverable

A bounded inference endpoint with truthful provider/fallback behavior and tests.

## Gate to Phase 5

- [ ] Endpoint produces schema-valid output.
- [ ] Timeouts and output limits work.
- [ ] Missing provider configuration is handled explicitly.
- [ ] No credentials are exposed.
- [ ] Fallback behavior is documented honestly.

---

# 8. Phase 5 — Official x402 v2 Integration

**Priority:** P0 — critical path  
**Suggested time:** 2–4 hours, depending on SDK readiness

## Objective

Make each seller callable through the official x402 v2 payment flow and compatible with an unmodified x402 v2 client.

## Prerequisite

Before coding this phase, Member 1 and Member 2 must agree on:
- SDK/package/version.
- Server and client integration pattern.
- Network and token configuration.
- Payment scheme.
- Price representation.
- Recipient configuration.
- Challenge/authorization behavior.
- Settlement timing.
- Handler error and timeout behavior.
- Replay and idempotency guarantees.
- Evidence passed to the application/ledger.

## Tasks

### 5.1 Implement one seller first

1. Choose the simplest seller endpoint, typically Data Seller.
2. Add the official x402 v2 server integration using verified documentation.
3. Configure the canonical price and payment terms.
4. Call it using the team's unmodified compatible x402 v2 client.
5. Verify the actual payment lifecycle with Member 1.
6. Verify the ledger receives truthful attempt and settlement data.
7. Save the test procedure and result in the project documentation.

Do not proceed to all three sellers until the first path is understood.

### 5.2 Extend to the other sellers

- Apply the same tested integration pattern to Scraping and Inference.
- Keep each seller's service identity and terms distinct.
- Avoid copying stale examples without checking SDK requirements.
- Ensure all endpoints use the same agreed conventions.

### 5.3 Verify payment terms

The seller's published terms and payment challenge must be consistent with the trusted registry/configuration. The buyer-side payment engine independently checks:
- Price.
- Network.
- Token.
- Recipient.
- Scheme.
- Expiry.
- Request/resource binding where supported.

Member 2 must not create a second, conflicting source of payment terms.

### 5.4 Verify replay behavior

- Test repeated requests using the same call/authorization context.
- Confirm the official SDK's replay guarantees.
- Add application-level idempotency only where required and in coordination with Member 1.
- Do not let a duplicate authorization unlock multiple paid responses.

### 5.5 Verify failure lifecycle

Test:
- Handler validation failure.
- Handler exception.
- Scraping timeout.
- Inference provider timeout.
- Invalid output.
- Network timeout during payment/settlement.

The actual result depends on the selected protocol lifecycle. Preserve uncertain outcomes for reconciliation; do not guess whether a payment occurred.

## Required tests

- Missing payment produces a protocol-compliant x402 v2 challenge.
- Valid unmodified client can pay/call the seller.
- Invalid/expired authorization is rejected by the official integration.
- Price/network/token/recipient configuration is correct.
- Replayed authorization cannot produce multiple paid responses.
- Settlement evidence reaches the payment/ledger path.
- Handler failures are represented according to the actual settlement lifecycle.
- All three sellers pass the same interoperability checks.

## Deliverable

Three independently callable seller endpoints protected by the official x402 v2 server integration.

## Gate to Phase 6

- [ ] One real low-value Base Sepolia payment has been verified end-to-end.
- [ ] All three seller endpoints work with the selected official integration.
- [ ] Replay behavior is tested.
- [ ] Failure and settlement behavior is documented.
- [ ] No secret or payment authorization data is logged.

---

# 9. Phase 6 — Registry and Ledger Integration

**Priority:** P1  
**Suggested time:** 60–90 minutes

## Objective

Make sellers discoverable and observable through the team's shared registry and ledger.

## 6.1 Registry integration with Member 3

For each service, provide:
- Stable service ID.
- Name and category.
- Public endpoint URL.
- Canonical price in the agreed representation.
- Network and pay-to configuration references.
- Input JSON Schema.
- Output JSON Schema.
- Description and capabilities.
- Enabled/disabled state.

Confirm that:
- The advertised endpoint exists.
- The schemas match actual request and response models.
- The price matches the configured x402 challenge.
- The category matches the required enum.
- The public URL is reachable from the buyer deployment.

Member 3 owns registry API behavior. Member 2 supplies and verifies seller-specific metadata.

## 6.2 Ledger integration with Member 4

Provide the agreed operational metadata:
- Call ID.
- Service ID.
- Start/end timestamps or latency.
- Outcome/error code.
- Input/output validation result where appropriate.
- Safe settlement reference only when available from the trusted payment integration.

Do not let the seller handler declare authoritative payment status on its own. Member 1's payment engine and Member 4's ledger own settlement truth.

## 6.3 Reputation inputs

Ensure real execution outcomes and latency can be used to calculate:
- Success rate.
- Median latency.
- Schema-rejection/failure counts.
- Current listed price.

Do not hard-code reputation scores or report self-assessed success rates.

## Acceptance criteria

- [ ] All three sellers are registered.
- [ ] Registry metadata matches the actual endpoints and schemas.
- [ ] Canonical price configuration is consistent.
- [ ] Seller outcomes and latency reach the shared persistence path.
- [ ] The ledger distinguishes attempted calls from verified settlements.

---

# 10. Phase 7 — Security and Interoperability Hardening

**Priority:** P1/P2  
**Suggested time:** 90–150 minutes

## Objective

Test the failure cases likely to be exercised by judges.

## Required test groups

### 7.1 Seller contract tests
- Each input schema rejects invalid data.
- Each output schema validates successful results.
- Maximum input/output sizes are enforced.
- Errors use the shared safe format.

### 7.2 x402 protocol tests
- Official x402 v2 client can call all three sellers.
- Missing payment receives the expected challenge.
- Invalid/expired authorization is rejected.
- Replay behavior is correct.
- Payment terms match registry data.
- Failure behavior follows the verified SDK lifecycle.

### 7.3 Scraping security tests
- Local/private/link-local/metadata targets blocked.
- Redirects to disallowed destinations blocked.
- DNS and destination validation reviewed.
- Timeouts and size limits enforced.
- Unsupported schemes and embedded credentials rejected.
- Website policies respected.

### 7.4 Inference safety tests
- Oversized inputs rejected.
- Provider timeouts handled.
- Provider output is validated.
- Input text cannot change payment recipient, price, or server policy.
- Credentials are not exposed.

### 7.5 Operational security
- No private keys or API secrets in Git.
- No signatures or authorization headers in logs.
- Public error responses contain no stack traces.
- Environment templates use placeholders only.
- Dependencies and lockfiles are reviewed.

## Acceptance criteria

- [ ] Required seller tests pass.
- [ ] Replay/interoperability tests pass.
- [ ] Scraper security tests pass.
- [ ] Failure statuses are not fabricated.
- [ ] Secret scan passes.
- [ ] Remaining known limitations are documented.

---

# 11. Phase 8 — Deployment and Demo

**Priority:** P1  
**Suggested time:** 60–120 minutes plus debugging buffer

## Objective

Make the three sellers reachable over public HTTPS and demonstrate them through the buyer.

## Tasks

1. Confirm hosting method with the team.
2. Configure public HTTPS endpoints for each seller.
3. Store secrets only in the hosting provider's secret settings.
4. Configure CORS only if browser calls need it; keep seller payment operations server-side.
5. Add or verify health/readiness endpoints.
6. Run deployed schema and endpoint smoke tests.
7. Test all three sellers from the deployed buyer environment.
8. Confirm ledger events and settlement references are available.
9. Freeze service IDs, schemas, and prices before the final demo.
10. Document known fallback behavior and limitations.

## Three-category demo flow

The demo task should require all three categories:

1. Data Seller retrieves related structured information.
2. Scraping Seller extracts a bounded set of details from an approved public page.
3. Inference Seller summarizes the validated information.
4. Buyer validates each response and combines the results.
5. Ledger shows one call attempt per execution and verified settlement evidence when settlement occurred.
6. The buyer explanation shows service selection, listed prices, actual verified spend, and remaining budget.

Never fake transaction hashes or settlement evidence. If a provider or site fails, state the fallback or failure honestly.

## Acceptance criteria

- [ ] All three public HTTPS endpoints work.
- [ ] The buyer can reach all three.
- [ ] Schemas and prices match registry records.
- [ ] Ledger entries are visible.
- [ ] Settlement evidence is real and verified.
- [ ] Demo can be repeated reliably.

---

# 12. Cross-Member Integration Matrix

| Integration | Member 2 provides | Other member provides | Required proof |
|---|---|---|---|
| Member 2 ↔ Member 1 | Seller endpoint, service-specific terms, handler behavior | Official client/payment adapter, policy checks, settlement lifecycle | One seller paid end-to-end; replay and failure tests |
| Member 2 ↔ Member 3 | Service IDs, paths, descriptions, request/response schemas | Registry API and buyer orchestration | Buyer discovers and successfully calls each seller |
| Member 2 ↔ Member 4 | Call IDs, latency, outcome metadata | Persistence, ledger, reputation calculations | Every attempt appears with truthful status/evidence |
| Member 2 ↔ integration owner | Small pull requests, tests, docs | Shared contracts and release process | Clean merge and deployed smoke test |

If an interface is not defined, flag it as a team decision. Do not silently invent a new contract.

---

# 13. Environment and Configuration Plan

Inspect the existing configuration before proposing new variables. Reuse established names if they already exist.

Potential configuration categories:

| Variable category | Purpose | Secret? | Owner |
|---|---|---|---|
| Application environment | Local/test/production behavior | No | Team/backend owner |
| Public base URL | Public seller endpoint generation | No | Deployment owner |
| x402 network | Approved testnet identifier | No | Member 1, coordinated with Member 2 |
| Token configuration | Verified testnet payment token | Usually not secret, but must be verified | Member 1 |
| Seller recipient configuration | Approved pay-to address | Not a private key; still validate | Member 1 / team |
| Inference provider key | Provider authentication | **Yes** | Inference integration owner |
| HTTP timeout limits | Resource bounds | No | Member 2 |
| Scraping allowlist | Permitted target hosts | No | Member 2 |

Do not create a new `.env` file containing real credentials. Update `.env.example` only with placeholders after the configuration contract is agreed.

---

# 14. Recommended 24-Hour Schedule

| Elapsed time | Priority work | Expected checkpoint |
|---|---|---|
| 0–1 h | Phase 0 audit and shared contracts | No unresolved critical interface assumptions |
| 1–2 h | Phase 1 foundation and schemas | Common conventions and tests ready |
| 2–3.5 h | Phase 2 Data Seller | Local schema-valid endpoint |
| 3.5–6 h | Phase 3 Scraping Seller | Safe fetch and security tests |
| 6–7.5 h | Phase 4 Inference Seller | Bounded inference and fallback |
| 3–7 h, parallel where possible | Member 1 pairing for first x402 seller | One paid seller path proven as early as possible |
| 7–10 h | Phase 5 all-seller x402 integration | Three paid seller endpoints |
| 10–12 h | Phase 6 registry/ledger integration | Buyer discovers sellers; ledger receives events |
| 12–15 h | Phase 7 hardening | Replay, failure, schema, SSRF, interoperability tests |
| 15–18 h | Phase 8 deployment | Public HTTPS endpoints |
| 18–21 h | End-to-end regression and fixes | Three-category paid workflow |
| 21–24 h | Freeze, rehearse, contingency | Stable demo and documented limitations |

These are estimates, not guarantees. If payment integration is blocked, prioritize getting one seller working end-to-end and resolve the blocker with Member 1 before polishing other features.

---

# 15. Risk Register

| Risk | Impact | Mitigation | Escalation |
|---|---|---|---|
| SDK integration is based on outdated examples | Paid path fails or is insecure | Verify official x402 v2 docs and tested version | Member 1 |
| Seller challenge price differs from registry | Buyer refuses or payment terms are unsafe | One canonical source and integration test | Members 1 and 3 |
| Settlement happens before handler failure | Failure may still be charged | Verify lifecycle; represent outcome truthfully | Members 1 and 4 |
| Scraper reaches internal network | SSRF security failure | Allowlist, DNS/IP and redirect validation, egress restrictions | Member 2 + integration owner |
| Scraping site becomes unavailable | Demo failure | Use permitted stable site and documented fixture fallback | Member 2 |
| Inference provider is unavailable | Inference demo failure | Explicit fallback or safe unavailable error | Member 2 |
| Schema drift | Buyer rejects valid-looking results | Shared schema definitions and contract tests | Members 2 and 3 |
| Duplicate seller implementation | Integration conflicts | Audit repository before creating files | All members |
| Secrets leak into browser/logs/Git | Security failure | Server-only secrets, redaction, secret scan | All members |
| Integration happens too late | No working end-to-end demo | Test one paid seller early | Team lead |

---

# 16. Definition of Done

## Data Seller
- [ ] Request and response schemas are documented.
- [ ] Structured lookup works.
- [ ] Provenance is truthful.
- [ ] Output schema and tests pass.

## Scraping Seller
- [ ] Approved host can be fetched.
- [ ] SSRF and redirect protections work.
- [ ] Timeouts and size limits work.
- [ ] Output is bounded and schema-valid.
- [ ] Website rules are respected.

## Inference Seller
- [ ] Bounded inference works.
- [ ] Provider/fallback behavior is truthful.
- [ ] Input/output limits and timeouts work.
- [ ] Output schema and tests pass.

## Payment and integration
- [ ] Official x402 v2 integration is used.
- [ ] Unmodified x402 v2 client can call each seller.
- [ ] Replay behavior is tested.
- [ ] Payment failure/settlement lifecycle is understood.
- [ ] Registry metadata matches actual services.
- [ ] Operational outcomes reach the shared ledger path.

## Deployment
- [ ] Public HTTPS endpoints work.
- [ ] No secrets are committed or logged.
- [ ] Deployed smoke tests pass.
- [ ] Three-category demo works and shows truthful payment evidence.

---

# 17. Immediate Next Actions for Member 2

Execute these in order:

1. Inspect the existing repository and read the shared contracts.
2. Report what seller code already exists; do not duplicate it.
3. Resolve the exact x402 v2 SDK and lifecycle questions with Member 1.
4. Freeze service IDs, endpoint paths, schemas, and metadata with Member 3.
5. Agree the operational event interface with Member 4.
6. Complete Phase 1 foundation and schema tests.
7. Implement the Data Seller and get one paid endpoint working as early as possible.
8. Implement the Scraping Seller with SSRF protections.
9. Implement the Inference Seller with bounded behavior and honest fallback.
10. Integrate all three with x402 v2.
11. Run contract, security, replay, and interoperability tests.
12. Deploy, run the three-category workflow, and rehearse.

## Final engineering rule

**Member 2 owns the seller's business logic and advertised schema. Member 1 owns buyer-side payment authorization and settlement policy. Member 3 owns buyer planning and registry APIs. Member 4 owns the authoritative ledger and dashboard.**

Do not let seller code bypass the payment integration, invent payment status, override registry terms, or claim settlement without verified evidence.
