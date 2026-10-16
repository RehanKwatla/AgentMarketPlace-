# DI-06 — Member 2 Detailed Implementation Plan
## Data Seller, Scraping Seller, and Inference Seller

**Project:** Pay-per-Call Agent Economy  
**Hackathon track:** Decentralized Intelligence Track — DI-06  
**Owner:** Member 2  
**Git branch:** `feature/sellers`  
**Primary responsibility:** Implement the three seller agents and their paid HTTP endpoints  
**Payment protocol:** Official x402 v2 integration  
**Target network:** Base Sepolia testnet  
**Backend assumption:** Python + FastAPI + Pydantic, unless the existing repository already uses an established equivalent  
**Timebox:** 24-hour hackathon  
**Status:** Implementation plan; verify SDK APIs and payment lifecycle against current official documentation before coding

---

# 1. Mission and Definition of Success

Member 2 owns the **seller side** of the DI-06 marketplace. The buyer must be able to discover and pay for three distinct service categories:

1. **Data Seller** — returns structured data.
2. **Scraping Seller** — extracts bounded information from a permitted public webpage.
3. **Inference Seller** — performs a bounded AI task such as summarization or classification.

All three may run inside one FastAPI application and one repository for the hackathon, but they must be distinct services with separate service IDs, endpoint paths, descriptions, input/output schemas, prices, and registry records.

## 1.1 Final outcomes

At completion:

- All three seller endpoints run locally and on a public HTTPS deployment.
- Each endpoint has a clear input contract and output JSON Schema.
- Each service is registered in the shared service registry.
- Each paid endpoint uses the **official x402 v2 server integration**.
- An unmodified x402 v2 buyer/client can call each seller.
- Seller outputs match the published schema.
- Replay and duplicate-call behavior is tested.
- Errors, timeouts, and latency are observable by the shared ledger.
- Scraping is constrained against SSRF and respects site rules.
- No private key, payment authorization, or API secret is exposed.
- The team can demonstrate a single buyer task using Data + Scraping + Inference.

## 1.2 What Member 2 does not own

Member 2 does **not** own:
- Buyer planning and service selection — Member 3.
- Final payment authorization, buyer-side budget reservation, or wallet signing — Member 1.
- Authoritative budget accounting, ledger UI, and reputation dashboard — Member 4.
- Final registry API implementation — Member 3, with persistence coordination from Member 4.

Member 2 must coordinate with these members rather than duplicating their responsibilities.

---

# 2. Architecture and Request Lifecycle

```text
                        Service Registry (Member 3)
                 service ID, endpoint, price, schemas, terms
                                   |
                                   v
                           Buyer Agent (Member 3)
                                   |
                       official x402 v2 client request
                                   |
                                   v
                     +-----------------------------+
                     | Seller HTTP endpoint        |
                     |                              |
                     | 1. x402 server integration  |
                     | 2. Request validation       |
                     | 3. Bounded service handler   |
                     | 4. Output schema validation |
                     | 5. Shared event/metrics hook |
                     +-----------------------------+
                          |          |          |
                          v          v          v
                       Data       Scraping   Inference
                       Seller      Seller     Seller
                          \          |          /
                           \         |         /
                            v        v        v
                          Buyer validates result
                                   |
                                   v
                          Ledger / audit (Member 4)
```

## 2.1 General lifecycle

The exact HTTP 402 and settlement sequence depends on the current official x402 v2 SDK and configured facilitator. Confirm it with Member 1 before finalizing handlers.

Conceptual flow:

1. Client sends a request to the seller endpoint.
2. The official x402 server integration returns the protocol-compliant payment challenge when payment is required and not yet provided.
3. The client follows the official x402 v2 payment flow.
4. The server integration verifies the payment authorization and performs or coordinates settlement according to its supported lifecycle.
5. Only an authorized request reaches the paid business operation, as enforced by the SDK integration.
6. Seller validates input and runs bounded work.
7. Seller validates its output against the same schema advertised in the registry.
8. Seller returns structured JSON and emits safe operational metadata to the shared persistence/metrics interface.
9. Buyer independently validates the returned output before using it.
10. The payment engine and ledger decide/record payment status from actual verified evidence, not from the seller's HTTP status alone.

**Do not hand-roll x402 headers, signatures, verification, or settlement.** Keep SDK-specific code in a small adapter or router layer.

---

# 3. Repository Ownership and File Layout

Adapt this to the team's existing repository; do not create duplicate modules if equivalent files already exist.

```text
backend/
  app/
    main.py
    core/
      config.py
      logging.py
    sellers/
      __init__.py
      common.py
      registry_seed.py            # optional seed data only; coordinate ownership
      data/
        __init__.py
        router.py
        schemas.py
        service.py
      scraping/
        __init__.py
        router.py
        schemas.py
        service.py
      inference/
        __init__.py
        router.py
        schemas.py
        service.py
      tests/
        test_data_seller.py
        test_scraping_seller.py
        test_inference_seller.py
        test_seller_x402.py
        test_seller_security.py
  tests/
    integration/
      test_all_sellers.py
```

## 3.1 Module responsibilities

| File | Responsibility |
|---|---|
| `common.py` | Shared bounded request helpers, timestamps, latency timing, safe error models |
| `data/schemas.py` | Pydantic request/response models and schema definitions |
| `data/service.py` | Data lookup business logic only |
| `data/router.py` | HTTP endpoint and x402 integration |
| `scraping/schemas.py` | URL request and bounded extraction response models |
| `scraping/service.py` | URL safety checks, fetching, parsing, extraction |
| `scraping/router.py` | Paid scraping endpoint and HTTP mapping |
| `inference/schemas.py` | Summarization/classification request and response models |
| `inference/service.py` | Bounded inference and provider adapter |
| `inference/router.py` | Paid inference endpoint and HTTP mapping |
| `registry_seed.py` | Optional canonical seed records, only if the team agrees Member 2 owns seed definitions |
| `tests/` | Unit, protocol integration, schema, replay, and security tests |

**Ownership boundary:** Member 2 owns the seller handlers and their advertised schemas. Member 3 owns registry APIs. Member 4 owns database migrations and authoritative ledger storage. Agree on how seller events are emitted; avoid creating a second competing ledger.

---

# 4. Shared Contract — Agree Before Coding

Arrange a short contract freeze with Members 1, 3, and 4.

## 4.1 Required service metadata

Each service registry record must include the fields required by the project:

```json
{
  "service_id": "data.lookup.v1",
  "name": "Structured Data Lookup",
  "category": "data",
  "endpoint_url": "https://YOUR_PUBLIC_HOST/seller/data/lookup",
  "price_atomic": 1000,
  "network": "eip155:84532",
  "pay_to": "0xYOUR_TESTNET_RECIPIENT",
  "input_schema": {},
  "output_schema": {},
  "description": "Returns bounded structured data for a query.",
  "enabled": true
}
```

This is an **illustrative shape**, not a final schema. Agree field names with Member 3. Never place private keys in registry records.

## 4.2 Required categories and IDs

Use stable IDs unless the team agrees on alternatives before integration:

| Seller | Service ID | Category | Example endpoint |
|---|---|---|---|
| Data | `data.lookup.v1` | `data` | `POST /seller/data/lookup` |
| Scraping | `scraping.extract.v1` | `scraping` | `POST /seller/scraping/extract` |
| Inference | `inference.summarize.v1` | `inference` | `POST /seller/inference/summarize` |

## 4.3 Shared rules to agree

- One canonical listed price per service.
- Price expressed internally as integer USDC base units.
- One canonical network identifier and testnet token configuration.
- One server-side pay-to address per service or approved payment configuration.
- Exact Pydantic models and JSON Schemas.
- Stable status enum and error response shape.
- Call/request ID and idempotency conventions.
- Safe way to emit latency and outcome metadata to Member 4.
- How seller failure interacts with the selected x402 settlement lifecycle.

Never duplicate the same service price or wallet address in several independent files. Load from validated configuration or the shared registry source.

---

# 5. Common Seller Engineering Rules

Apply these to all three sellers.

## 5.1 Input validation

- Use Pydantic request models.
- Reject unknown or malformed critical fields where appropriate.
- Set explicit string, list, and payload limits.
- Reject empty queries and invalid limits.
- Validate before expensive work.
- Return structured, non-sensitive errors.

## 5.2 Output validation

- Build response objects using Pydantic response models.
- Validate the response before returning it.
- Publish the JSON Schema corresponding to the same response model.
- Keep output bounded; never return an unbounded scraped page or raw provider dump.
- Include source/provenance fields when appropriate.
- Buyer validation remains mandatory even if the seller validates its own response.

## 5.3 Timeouts and resource bounds

- Use explicit connection and read timeouts for network/provider calls.
- Set maximum request body and response sizes.
- Limit scraping redirects and extracted items.
- Avoid unbounded concurrency, recursion, retries, or model output.
- Make retries finite and safe; do not retry payment flows blindly.

## 5.4 Logging

Safe operational fields can include:
- service ID
- internal call ID
- elapsed time
- outcome category
- schema-validation result
- non-sensitive error code

Never log:
- private keys
- payment signatures or authorization headers
- raw payment payloads
- API provider secrets
- full user payloads unless strictly necessary and approved

## 5.5 Error handling

Use one agreed safe error envelope. For example:

```json
{
  "error": {
    "code": "INVALID_INPUT",
    "message": "The request does not match this service's input requirements."
  }
}
```

Do not expose stack traces, filesystem paths, environment values, secrets, or internal provider responses to the client.

---

# 6. Seller A — Data Seller

## 6.1 Purpose

Return structured data matching the user's query. For a hackathon demo, prefer a small, deterministic and documented dataset over an unreliable external dependency.

## 6.2 Endpoint

`POST /seller/data/lookup`

Example request:

```json
{
  "query": "books about machine learning",
  "limit": 5
}
```

Example response:

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

The example is illustrative; publish the final exact response model and schema.

## 6.3 Implementation steps

1. Define `DataLookupRequest` with bounded `query` and `limit`.
2. Define `DataItem` and `DataLookupResponse`.
3. Create a small seed dataset with clear source/provenance labels.
4. Implement normalized text search and deterministic ordering.
5. Apply the requested limit, with a server-side maximum.
6. Include `count` equal to the number of returned items.
7. Include source and observation time when those claims are valid.
8. Validate the response with the Pydantic model.
9. Add the paid endpoint using the official x402 v2 server integration.
10. Add the canonical service record through the agreed registry seed mechanism.
11. Add unit tests for empty queries, no matches, limits, schema validity, and provenance.

## 6.4 Data quality rules

- Do not invent live values or pretend a static dataset is live.
- Label seeded/demo content clearly.
- Keep the response deterministic for predictable testing.
- Avoid arbitrary file paths or SQL supplied by the user.
- If the service queries a database, use parameterized queries and a read-only role.

## 6.5 Acceptance tests

- Valid query returns schema-valid JSON.
- Empty query is rejected.
- `limit` cannot exceed the configured maximum.
- No-match query returns an empty list and `count: 0`.
- Returned count matches item count.
- Provenance is present and truthful.
- x402 v2 challenge and paid-call flow work.

---

# 7. Seller B — Scraping Seller

## 7.1 Purpose

Fetch a permitted public page and return bounded, structured extracted information. This seller has the largest security surface because the caller controls a URL.

## 7.2 Endpoint

`POST /seller/scraping/extract`

Example request:

```json
{
  "url": "https://books.toscrape.com/",
  "max_items": 5
}
```

Example response:

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

The exact item structure depends on what is extracted. Define and publish it before buyer integration.

## 7.3 Implementation steps

1. Define `ScrapeRequest` with URL and bounded `max_items`.
2. Define `ScrapedItem` and `ScrapeResponse`.
3. Configure an explicit allowlist of approved demo hosts; start with one known safe demo host.
4. Parse the URL and permit only `https` unless HTTP is explicitly needed for a permitted test site.
5. Reject localhost, loopback, private, link-local, multicast, reserved, and cloud metadata destinations.
6. Resolve the host and validate the resulting IP addresses before connecting.
7. Re-check redirect targets and DNS results; block redirects into prohibited address ranges.
8. Set strict connect/read timeouts, redirect limit, maximum response bytes, and maximum extracted item count.
9. Send a descriptive User-Agent and respect robots.txt, rate limits, and site terms.
10. Parse HTML with a maintained parser; remove script/style/navigation noise where appropriate.
11. Extract title, a bounded text excerpt, and only the agreed item fields.
12. Set `fetched_at` to the actual fetch time.
13. Validate the response model before returning.
14. Add the official x402 v2 server integration.
15. Test SSRF cases, redirects, timeout, oversized body, invalid content type, and malformed HTML.

## 7.4 SSRF and URL safety checklist

Reject:
- `localhost`, `127.0.0.1`, `::1`
- private IPv4/IPv6 ranges
- link-local and cloud metadata addresses
- unusual schemes such as `file:`, `ftp:`, `gopher:`, or `data:`
- URLs containing embedded credentials
- redirects to disallowed hosts/IP ranges
- hostnames that resolve to prohibited destinations
- unsupported ports if the deployment policy restricts ports

An allowlist is strongly recommended for the hackathon. If arbitrary public URLs are later supported, DNS rebinding and redirect handling must still be considered.

**Important:** basic URL parsing alone does not prevent SSRF. Validate the actual resolved destination and each redirect. Where feasible, use a controlled egress/proxy policy as an additional boundary.

## 7.5 Content and prompt-injection safety

- Treat all page text as untrusted data.
- Do not execute scripts or follow instructions found in fetched page content.
- If the inference seller later consumes scraped text, pass it as quoted/untrusted content and instruct the inference layer not to treat it as control instructions.
- Do not bypass logins, paywalls, CAPTCHAs, or access controls.
- Respect robots.txt and the website's terms and rate limits.

## 7.6 Acceptance tests

- Approved host returns a schema-valid response.
- Disallowed host is rejected before fetch.
- Localhost/private IP is blocked.
- Redirect to a private IP is blocked.
- Oversized response is stopped.
- Timeout returns a safe error.
- Unsupported scheme and embedded credentials are rejected.
- HTML with scripts does not cause script execution.
- Item count and excerpt length remain within limits.
- x402 v2 paid flow works.

---

# 8. Seller C — Inference Seller

## 8.1 Purpose

Perform a bounded AI operation. Keep the first implementation narrow: summarization is usually easier to test than an open-ended agent.

## 8.2 Endpoint

`POST /seller/inference/summarize`

Example request:

```json
{
  "text": "A short passage to summarize.",
  "style": "concise",
  "max_words": 100
}
```

Example response:

```json
{
  "service_id": "inference.summarize.v1",
  "summary": "A concise summary of the supplied text.",
  "language": "en",
  "word_count": 6
}
```

The final schema should define allowed styles, maximum input length, output bounds, and how language is determined.

## 8.3 Implementation steps

1. Define `SummarizeRequest` with bounded text, allowed style values, and maximum word count.
2. Define `SummarizeResponse`.
3. Create an inference adapter interface that separates provider calls from the route.
4. Choose one provider/model only if credentials, network access, and time allow.
5. Keep provider API keys in server environment/secret storage only.
6. Set a strict provider timeout, token/output limit, and input size limit.
7. Treat user-supplied text as untrusted data, not as instructions to change seller behavior.
8. Avoid exposing arbitrary system prompts, tools, or URL fetching to the caller.
9. Normalize provider output and validate it against `SummarizeResponse`.
10. Enforce the requested maximum word count as a postcondition, using a documented method.
11. If no provider is available, use a clearly documented deterministic fallback or return a truthful unavailable error; do not claim a real LLM generated the result.
12. Add the official x402 v2 server integration.
13. Test long input, empty input, provider timeout, malformed provider output, and output word limit.

## 8.4 Provider strategy

For a 24-hour hackathon:
- **Preferred:** one reliable configured inference provider with strict timeouts and a small response limit.
- **Fallback:** a deterministic extractive summary if disclosed as fallback behavior.
- **Avoid:** building multi-provider routing, tool-calling agents, or complex prompt orchestration before the paid path works.

## 8.5 Acceptance tests

- Valid request returns schema-valid output.
- Empty/oversized input is rejected.
- Unsupported style is rejected.
- Output respects the word limit.
- Provider timeout produces a safe, truthful failure.
- Missing provider configuration is handled explicitly.
- API key never appears in logs or response.
- x402 v2 paid flow works.

---

# 9. x402 v2 Integration — Critical Shared Work

This section is a coordination checklist, not a custom protocol implementation.

## 9.1 Required behavior

- Use the official x402 v2 server SDK/middleware supported by the chosen stack.
- Keep network, token, pay-to address, scheme, and price in validated server configuration/registry terms.
- Make each endpoint independently discoverable and payable.
- Support unmodified x402 v2 clients.
- Do not accept a custom private payment header as a substitute for the protocol.
- Ensure request/authorization replay behavior matches the official SDK's guarantees and add application-level idempotency if required.
- Never log authorization data or signatures.
- Do not report a payment as successful merely because the business handler ran.

## 9.2 Integration session with Member 1

Before enabling all three sellers, pair with Member 1 to verify:
1. The exact official SDK package/version and FastAPI integration pattern.
2. How the payment challenge is configured per service.
3. How payment verification and settlement are performed.
4. Whether the SDK settles before or after the business handler runs.
5. What happens if the handler times out, throws an exception, or returns invalid output.
6. How request/resource binding and replay prevention work.
7. What settlement reference/evidence is exposed to the application.
8. Which error/status fields are persisted for the ledger.

This is essential because the project requires failures not to be charged where the selected lifecycle can guarantee it. Do not assume settlement ordering.

## 9.3 Prices and network

- Use Base Sepolia only for the hackathon.
- Use the shared canonical network and token configuration after verification.
- Keep each per-call price at or below the project's stated cap of `0.10 USDC`.
- Express accounting values in integer atomic units.
- Do not hard-code a guessed token contract or SDK API from an old snippet; verify current official configuration.
- Use fresh testnet wallets and only testnet funds.

---

# 10. Shared Persistence, Events, and Metrics

Member 4 owns the authoritative ledger database. Member 2 should emit the agreed event/call metadata through a shared service or interface rather than create a separate ledger.

Suggested operational fields:
- `call_id`
- `service_id`
- `started_at`, `completed_at`, `latency_ms`
- `outcome_code`
- `input_validation_ok`
- `output_validation_ok`
- `error_code` where applicable
- a settlement reference only when supplied by the trusted payment integration

Do not let seller code independently set authoritative buyer payment status. The payment engine and ledger own settlement truth.

## 10.1 Reputation inputs

Provide trustworthy raw measurements so Member 4 can calculate:
- successful schema-valid responses
- completed attempts
- median execution latency
- schema rejection count
- service's current listed price

Do not calculate reputation from self-reported values or hard-coded ratings.

---

# 11. Testing Strategy

## 11.1 Unit tests

For each seller:
- request validation
- business logic
- output model/schema
- boundary values
- no-result case
- timeout/error mapping

## 11.2 Protocol integration tests

- Missing payment receives a protocol-compliant x402 v2 challenge.
- Valid unmodified x402 v2 client can call the service.
- Invalid/expired/mismatched authorization is rejected by the official integration.
- Replayed authorization cannot unlock multiple successful responses.
- Settlement and error behavior matches the selected SDK lifecycle.
- One test is run against each of the three seller endpoints.

## 11.3 Security tests

- Scraper SSRF and redirect tests.
- Payload and response-size limits.
- Timeout and resource exhaustion cases.
- No secrets in logs.
- No payment authorization in application error responses.
- Inference prompt-injection-like input does not alter tool/payment policy.
- Untrusted scraped text is not executed or treated as system instructions.

## 11.4 End-to-end demo test

One buyer task should:
1. Discover the Data Seller.
2. Discover and call the Scraping Seller for a permitted public page.
3. Send the relevant content to the Inference Seller.
4. Validate each output against its schema.
5. Return the combined result with source provenance.
6. Show one ledger attempt per call and verified settlement evidence where each payment settled.
7. Show accurate total spend and remaining budget.

The number of calls and actual spend must come from execution/ledger data, not from a scripted claim.

---

# 12. Work Plan for a 24-Hour Hackathon

## Phase 1 — Contract freeze (Hour 0–1)
- [ ] Confirm service IDs, paths, schemas, prices, and registry fields with Member 3.
- [ ] Confirm payment lifecycle and SDK integration with Member 1.
- [ ] Confirm event/persistence interface with Member 4.
- [ ] Create seller module skeletons and one test per seller.

## Phase 2 — Business handlers (Hour 1–3)
- [ ] Implement Data Seller with deterministic data.
- [ ] Implement Scraping Seller for one allowlisted host.
- [ ] Implement Inference Seller with one narrow summarization behavior.
- [ ] Validate request and response models.
- [ ] Add timeouts and payload limits.

## Phase 3 — One paid seller (Hour 3–5)
- [ ] Integrate official x402 v2 server support into one seller.
- [ ] Test it with Member 1's buyer/payment path.
- [ ] Verify real testnet settlement behavior and ledger event mapping.
- [ ] Fix protocol issues before copying the pattern.

## Phase 4 — All three paid sellers (Hour 5–8)
- [ ] Add x402 support to remaining endpoints.
- [ ] Seed all three registry records through the agreed mechanism.
- [ ] Test with the unmodified x402 v2 client.
- [ ] Confirm each response schema is published and matches actual output.

## Phase 5 — Hardening (Hour 8–12)
- [ ] Add replay/idempotency tests.
- [ ] Add scraper SSRF/redirect protections.
- [ ] Test provider errors, timeouts, oversized requests, and malformed responses.
- [ ] Confirm latency/outcome metadata reaches Member 4.
- [ ] Check logs for secrets.

## Phase 6 — Full integration (Hour 12–16)
- [ ] Run the three-category buyer task with Member 3.
- [ ] Confirm buyer output validation and fallback.
- [ ] Confirm Member 4's ledger shows each attempt and correct status.
- [ ] Confirm seller price and registry terms match.

## Phase 7 — Deployment and rehearsal (Hour 16–24)
- [ ] Deploy public HTTPS seller endpoints.
- [ ] Configure secrets in hosting settings only.
- [ ] Run health and end-to-end smoke tests.
- [ ] Freeze service IDs, paths, schemas, and prices.
- [ ] Rehearse seller behavior, payment challenge, failure handling, and security explanations.

---

# 13. Git and Collaboration Workflow

## Branch and commits

Work only on `feature/sellers` for this ownership area, then open a pull request.

Suggested commits:

```text
feat(sellers): add shared seller request and response models
feat(sellers): implement structured data lookup
feat(sellers): add bounded public-page scraper
feat(sellers): add summarization inference endpoint
feat(sellers): integrate official x402 v2 server
test(sellers): add schema and protocol tests
test(sellers): add SSRF and replay regression cases
docs(sellers): document service contracts and demo behavior
```

## Pull request checklist

- [ ] No unrelated edits to payment engine, buyer planner, or ledger schema.
- [ ] Service IDs and paths match shared contracts.
- [ ] Advertised JSON Schemas match actual responses.
- [ ] Prices and payment terms come from the agreed canonical source.
- [ ] Tests pass.
- [ ] No secrets or generated local files are committed.
- [ ] Failure behavior has been checked with Member 1.
- [ ] Registry and persistence changes are coordinated with Members 3 and 4.

---

# 14. Common Risks and Mitigations

| Risk | Mitigation |
|---|---|
| x402 SDK API differs from an example | Verify official docs and pin the tested package version |
| Payment settles before a seller failure | Confirm lifecycle early; design truthful status/reconciliation with Member 1 |
| Registry price differs from seller challenge | One canonical configuration source and cross-component tests |
| Seller output fails buyer schema validation | Share schemas; validate on seller and buyer sides |
| Scraper can access internal network | Host allowlist, DNS/IP checks, redirect validation, egress restrictions |
| Public website blocks or changes | Use a permitted stable demo site; have a transparent deterministic fixture fallback if necessary |
| LLM provider is unavailable | Use a documented deterministic fallback or explicit unavailable error |
| Replay yields duplicate work or results | Official SDK protection plus durable application-level idempotency where needed |
| Deployment secrets leak | Server-only secret settings; never put secrets in frontend environment variables or Git |
| Integration starts too late | Make one seller work end-to-end before completing all three |

---

# 15. Final Acceptance Checklist

## Functional
- [ ] Data Seller works.
- [ ] Scraping Seller works against an approved host.
- [ ] Inference Seller works.
- [ ] Three distinct service IDs, paths, prices, and schemas exist.
- [ ] Registry records are available through Member 3's API.

## Payment/protocol
- [ ] Official x402 v2 server integration is used.
- [ ] Unmodified x402 v2 client can pay each seller.
- [ ] Invalid/replayed authorization is rejected.
- [ ] Settlement evidence is available to the payment/ledger path.
- [ ] Failure behavior is consistent with the selected SDK lifecycle.

## Safety/quality
- [ ] Input and output schemas are enforced.
- [ ] Timeouts and payload bounds are in place.
- [ ] Scraper SSRF and redirect tests pass.
- [ ] Inference input is treated as untrusted content.
- [ ] No secrets or authorization data are logged.
- [ ] Latency and outcomes feed the shared metrics/ledger.
- [ ] All seller tests pass.

## Demo/deployment
- [ ] Public HTTPS URLs work.
- [ ] One task uses Data + Scraping + Inference.
- [ ] The demo shows real execution and truthful payment evidence.
- [ ] Service descriptions accurately state any seeded data or fallback behavior.

---

# 16. Member 2's Immediate To-Do List

Do these in order:

1. Open `API_CONTRACTS.md` and `DATABASE_SCHEMA.md`; confirm the fields/statuses with the team.
2. Create the three seller module skeletons and Pydantic schemas.
3. Make each plain business handler work without payment.
4. Pair with Member 1 to implement and test x402 v2 on one seller.
5. Extend the same tested pattern to the other two sellers.
6. Publish/seed the three service records through Member 3's registry path.
7. Connect latency/outcome metadata to Member 4's ledger path.
8. Run schema, SSRF, timeout, replay, and interoperability tests.
9. Deploy public HTTPS endpoints.
10. Rehearse the complete three-category paid task.

**Success criterion:** a real buyer can discover and pay each of the three seller agents through unmodified x402 v2 integration, receive schema-valid results, and see truthful outcomes in the shared ledger.
