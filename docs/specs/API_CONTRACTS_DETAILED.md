# DI-06: Pay-per-Call Agent Economy
## API Contract / Interface Specification

**Document ID:** DI06-API-001  
**Filename:** `API_CONTRACTS.md`  
**Project:** DI-06 — Pay-per-Call Agent Economy  
**Backend:** FastAPI + Pydantic (proposed baseline)  
**Frontend:** React + TypeScript (proposed baseline)  
**Payment protocol:** x402 v2  
**Settlement network:** Base Sepolia (`eip155:84532`)  
**Status:** Proposed shared contract — team must freeze schemas and status enums before parallel implementation

---

## 1. Purpose

This document defines the HTTP APIs and shared request/response contracts used by the DI-06 marketplace, buyer agent, service registry, seller agents, payment engine, ledger, and reputation dashboard.

It is the shared integration agreement for all four team members. The goal is to make independently developed modules interoperable without repeatedly changing request fields, response shapes, or status meanings.

The API contracts cover:

- Service registry discovery and filtering.
- Service metadata and declared input/output schemas.
- Natural-language task submission with a spending budget.
- Task execution status and aggregated results.
- Three paid seller categories: Data, Scraping, and Inference.
- x402 v2 payment challenges and the selected SDK's standard payment flow.
- Ledger entries and settlement evidence.
- Seller reputation.
- Health and readiness endpoints.
- Standard errors and idempotency.
- Security, validation, and acceptance tests.

**Important:** The application endpoints below are proposed project APIs. They are not official x402 protocol routes. The three seller endpoints must use the official x402 v2 integration and its required HTTP 402 challenge/payment behavior. Do not invent or modify protocol headers to fit these application contracts.

---

## 2. Contract Rules

### 2.1 Shared conventions

| Item | Convention |
|---|---|
| API base path | `/api/v1` for application APIs |
| Content type | `application/json` unless otherwise specified |
| Character encoding | UTF-8 |
| Internal IDs | UUID strings |
| Public service identifier | Stable slug such as `data-001` |
| Timestamps | ISO 8601 with timezone, preferably UTC (`Z`) |
| Network identifier | CAIP-2 string, e.g. `eip155:84532` |
| Money arithmetic | Integer token base units internally |
| Money in public JSON | Decimal USDC string, e.g. `"0.002000"` |
| Pagination | `limit` + `offset` initially |
| Error format | Shared JSON error object for application APIs |
| Authentication | Define per deployment; never put signing keys in browser |
| API versioning | Breaking changes require a coordinated contract change |

Public JSON uses decimal USDC strings for readability. The backend must parse and convert amounts to integer base units before comparisons or arithmetic. The number of decimal places must match the verified token configuration.

### 2.2 Stable identifiers

- `service_id`: stable public slug, for example `data-001`, in registry-facing APIs.
- `service_uuid`: optional internal UUID, if exposed at all.
- `task_id`: UUID string.
- `call_id`: UUID string.
- `payment_attempt_id`: UUID string.
- `settlement_id`: UUID string.

Do not switch between slugs and UUIDs without documenting which field each endpoint accepts.

### 2.3 Timeouts and retries

- Set explicit timeouts for seller calls and external services.
- Do not retry a paid call blindly after a timeout.
- Before retrying a request with uncertain settlement, reconcile the payment attempt.
- Use idempotency keys for task submission and call execution where appropriate.
- Retrying a request must not create duplicate payments or unlock another protected response.

### 2.4 Application API versus x402 protocol

Application endpoints such as `/api/v1/services` and `/api/v1/tasks` are project-defined. Seller endpoints use the selected official x402 v2 server/client integration. The exact x402 headers, payloads, and lifecycle must come from the chosen SDK and official specification, not from the illustrative JSON in this document.

---

## 3. API Inventory

| Method | Endpoint | Purpose | Owner |
|---|---|---|---|
| `GET` | `/health` | Basic process health | Integration owner |
| `GET` | `/ready` | Dependency/readiness check | Integration owner |
| `GET` | `/api/v1/services` | Search/filter registry | Member 3 |
| `GET` | `/api/v1/services/{service_id}` | Retrieve service metadata | Member 3 |
| `GET` | `/api/v1/services/{service_id}/reputation` | Retrieve reputation | Member 3 / Member 4 |
| `POST` | `/api/v1/tasks` | Submit a natural-language task | Member 3 |
| `GET` | `/api/v1/tasks/{task_id}` | Retrieve task state/results | Member 3 / Member 4 |
| `POST` | `/api/v1/tasks/{task_id}/cancel` | Request task cancellation | Optional; implement only if safe |
| `GET` | `/api/v1/tasks/{task_id}/calls` | List calls for a task | Member 3 / Member 4 |
| `GET` | `/api/v1/ledger` | Query ledger entries | Member 4 |
| `GET` | `/api/v1/ledger/{call_id}` | Retrieve call/ledger details | Member 4 |
| `GET` | `/api/v1/reputation` | List seller reputation | Member 3 / Member 4 |
| `POST` | Seller-specific endpoint | Paid seller operation using x402 v2 | Member 2 |
| `GET` | `/openapi.json` | FastAPI-generated OpenAPI document | Backend |

The endpoint inventory is the initial contract. If a route is removed or renamed, update this document and the frontend together.

---

## 4. Shared Data Types

### 4.1 Service category

Allowed values:

```text
data
scraping
inference
```

Every active service must belong to exactly one category for the initial implementation.

### 4.2 Task status

Recommended values:

```text
queued
planning
running
completed
completed_with_warnings
failed
cancelled
```

Task status describes the overall task. It must not be used as a substitute for payment status.

### 4.3 Service-call status

Recommended values:

```text
created
awaiting_payment
executing
validating_output
succeeded
paid_output_rejected
refused
failed_and_not_charged
pending_reconciliation
```

### 4.4 Payment-attempt status

Recommended values:

```text
created
challenge_received
policy_rejected
authorization_created
verification_pending
settlement_pending
settled
failed_before_settlement
pending_reconciliation
```

### 4.5 Settlement status

Recommended values:

```text
observed
confirmed
reverted
verification_failed
```

### 4.6 Ledger status mapping

The dashboard must preserve the distinction between payment and output validity.

| Internal condition | Display status | Meaning |
|---|---|---|
| Verified settlement and accepted output | `paid` | Paid call with valid accepted result |
| Verified settlement but rejected output | `paid_output_rejected` | Payment occurred, but buyer rejected output |
| Deterministic policy refusal before authorization/settlement | `refused` | Call refused by policy |
| Confirmed failure with no charge | `failed_and_not_charged` | Failure occurred and no payment was made |
| Settlement uncertain | `pending_reconciliation` | Do not claim paid or unpaid until reconciled |

The required visible statuses are `paid`, `paid output rejected`, `refused`, and `failed and not charged`. The API may use snake_case values internally, but the frontend should render readable labels.

---

## 5. Standard Error Contract

All project-defined application APIs should return a consistent error structure. x402 protocol responses from seller endpoints must follow the official x402 v2 implementation and must not be replaced by this generic error envelope when a protocol-specific response is required.

### 5.1 Error JSON

```json
{
  "error": {
    "code": "BUDGET_EXCEEDED",
    "message": "The requested service cannot be purchased within the remaining budget.",
    "request_id": "8f4d5b9e-1d4d-4c1a-a4cc-5d10a8e6c101",
    "details": {
      "remaining_budget_usdc": "0.001000",
      "required_usdc": "0.002000"
    }
  }
}
```

`details` must contain safe, non-secret diagnostic information only.

### 5.2 Error codes

| Code | Typical HTTP status | Meaning |
|---|---:|---|
| `VALIDATION_ERROR` | 400 or 422 | Request is malformed or fails validation |
| `NOT_FOUND` | 404 | Resource does not exist |
| `SERVICE_INACTIVE` | 409 | Service exists but cannot be selected |
| `BUDGET_EXCEEDED` | 409 | Request would exceed the remaining budget |
| `PRICE_MISMATCH` | 409 | Requested price exceeds approved registry price |
| `PAYMENT_POLICY_REJECTED` | 403 or 409 | Payment configuration violates policy |
| `IDEMPOTENCY_CONFLICT` | 409 | Idempotency key reused with a different request |
| `TASK_NOT_CANCELLABLE` | 409 | Task has reached a state that cannot safely be cancelled |
| `DEPENDENCY_UNAVAILABLE` | 503 | Required dependency is unavailable |
| `SELLER_TIMEOUT` | 504 | Seller did not respond before timeout |
| `SELLER_INVALID_OUTPUT` | 502 | Seller output failed schema validation |
| `PAYMENT_PENDING_RECONCILIATION` | 202 or 409 | Payment outcome is uncertain and must be reconciled |
| `INTERNAL_ERROR` | 500 | Unexpected server error |

Use one agreed status/code mapping. Do not expose stack traces, private keys, authorization headers, or raw database errors to clients.

---

## 6. Service Registry API

### 6.1 `GET /api/v1/services`

**Purpose:** Search the marketplace by category, price, and active status.

#### Query parameters

| Parameter | Type | Required | Description |
|---|---|---:|---|
| `category` | string | No | `data`, `scraping`, or `inference` |
| `max_price_usdc` | decimal string | No | Maximum per-call price |
| `min_price_usdc` | decimal string | No | Minimum per-call price |
| `active` | boolean | No | Filter active/inactive services; default `true` |
| `q` | string | No | Search service name/description |
| `limit` | integer | No | Default 20; enforce a reasonable maximum |
| `offset` | integer | No | Default 0 |

#### Example request

```http
GET /api/v1/services?category=data&max_price_usdc=0.010000&active=true&limit=20&offset=0
```

#### Example response

```json
{
  "items": [
    {
      "service_id": "data-001",
      "name": "Structured Data Seller",
      "category": "data",
      "description": "Returns structured data for buyer tasks.",
      "endpoint_url": "https://example.com/services/data-001",
      "price_usdc": "0.002000",
      "network": "eip155:84532",
      "asset_address": "0xVERIFIED_TOKEN_ADDRESS",
      "pay_to": "0xSELLER_RECEIVING_ADDRESS",
      "input_schema": {
        "type": "object",
        "properties": {
          "query": {"type": "string"}
        },
        "required": ["query"]
      },
      "output_schema": {
        "type": "object",
        "properties": {
          "items": {"type": "array"}
        },
        "required": ["items"]
      },
      "is_active": true,
      "reputation": {
        "success_rate": 0.96,
        "median_latency_ms": 420,
        "total_calls": 25
      }
    }
  ],
  "limit": 20,
  "offset": 0,
  "total": 1
}
```

Addresses and URLs above are illustrative placeholders. The returned payment fields must match the actual seller configuration and verified token/network.

#### Rules

- Return only services matching all supplied filters.
- Do not select inactive services for new tasks.
- The registry's listed price is the trusted comparison price for buyer policy.
- Prices must be represented consistently and converted to integer token units before arithmetic.
- Validate and restrict registry URLs to approved schemes/hosts. Deployed seller URLs should be HTTPS.
- Do not allow a seller's request to silently overwrite its registry price or payment recipient.

### 6.2 `GET /api/v1/services/{service_id}`

**Purpose:** Retrieve one service's full registry metadata.

#### Path parameter

- `service_id`: stable public slug, e.g. `data-001`.

#### Success response

Returns one service object using the same field names as the registry list item.

#### Errors

- `404 NOT_FOUND` if the service does not exist.
- `409 SERVICE_INACTIVE` only if the chosen API design elects to signal inactive service separately; otherwise return the record with `is_active: false`.

Choose one behavior and keep it consistent.

### 6.3 `GET /api/v1/services/{service_id}/reputation`

Returns the current reputation summary for the service.

```json
{
  "service_id": "data-001",
  "success_rate": 0.96,
  "median_latency_ms": 420,
  "total_calls": 25,
  "successful_calls": 24,
  "paid_output_rejected_calls": 1,
  "last_call_at": "2026-10-16T12:15:30Z"
}
```

If the service has no call history, return a clearly defined empty-history representation. Do not imply a perfect success rate without observations.

---

## 7. Task Submission API

### 7.1 `POST /api/v1/tasks`

**Purpose:** Accept a natural-language request and spending budget, then create a buyer task.

#### Headers

```http
Content-Type: application/json
Idempotency-Key: <unique-client-generated-key>
```

The `Idempotency-Key` header is recommended for task creation. If the team does not implement it for the initial version, document that choice. If implemented, the same key with the same request must return the existing task; the same key with a different request must be rejected.

#### Request JSON

```json
{
  "task": "Find three recent articles about renewable energy, extract the title and source, and summarize the findings.",
  "budget_usdc": "0.050000",
  "max_concurrency": 3,
  "preferred_categories": ["scraping", "data", "inference"],
  "require_all_categories": true
}
```

#### Field definitions

| Field | Type | Required | Rules |
|---|---|---:|---|
| `task` | string | Yes | Non-empty natural-language task; enforce a maximum length |
| `budget_usdc` | decimal string | Yes | Non-negative amount; parse to integer base units |
| `max_concurrency` | integer | No | Default 3; enforce configured upper bound and support at least 3 |
| `preferred_categories` | array of strings | No | Must contain valid categories |
| `require_all_categories` | boolean | No | If true, plan must use all three categories when feasible |

The application must refuse a plan that cannot fit within the available budget. It must not rely on the LLM to enforce spending limits.

#### Success response

Return `202 Accepted` if the task runs asynchronously, or `201 Created` if the task record is created and execution is synchronous/fully accepted. Choose one approach and use it consistently.

```json
{
  "task_id": "2c07b9d1-5b35-4ed4-8a7b-2adcc5b2a010",
  "status": "queued",
  "budget_usdc": "0.050000",
  "reserved_usdc": "0.000000",
  "spent_usdc": "0.000000",
  "max_concurrency": 3,
  "created_at": "2026-10-16T12:00:00Z",
  "status_url": "/api/v1/tasks/2c07b9d1-5b35-4ed4-8a7b-2adcc5b2a010"
}
```

### 7.2 Budget rules

- Budget values are converted to integer token base units before use.
- The buyer must reserve funds atomically before authorizing concurrent paid calls.
- The sum of confirmed spend and active reservations must not exceed the task budget.
- If the task needs a service that is unaffordable, the buyer must refuse it or choose an eligible fallback.
- The API must never accept an LLM-generated plan as permission to bypass budget checks.
- An uncertain payment outcome remains reserved or pending reconciliation until resolved.

---

## 8. Task Status and Results

### 8.1 `GET /api/v1/tasks/{task_id}`

Returns task status, budget totals, service-call summaries, and the final result when available.

#### Example response

```json
{
  "task_id": "2c07b9d1-5b35-4ed4-8a7b-2adcc5b2a010",
  "status": "completed_with_warnings",
  "task": "Find three recent articles about renewable energy and summarize them.",
  "budget_usdc": "0.050000",
  "reserved_usdc": "0.000000",
  "spent_usdc": "0.006000",
  "remaining_usdc": "0.044000",
  "max_concurrency": 3,
  "calls": [
    {
      "call_id": "5d8f3e2c-6db3-42c0-a0f4-5f20a0f3bb10",
      "service_id": "scraping-001",
      "category": "scraping",
      "status": "succeeded",
      "listed_price_usdc": "0.002000",
      "amount_paid_usdc": "0.002000",
      "latency_ms": 860,
      "transaction_hash": "0xEXAMPLE_HASH"
    }
  ],
  "result": {
    "summary": "Example summary text.",
    "sources": []
  },
  "created_at": "2026-10-16T12:00:00Z",
  "completed_at": "2026-10-16T12:00:04Z"
}
```

The transaction hash and result are illustrative. In real responses, only include transaction hashes that actually exist and label them with the correct network. A call can have no transaction hash if it was refused or failed before settlement.

#### Rules

- `spent_usdc` reflects confirmed paid amounts, not merely planned costs.
- `remaining_usdc` must be computed from the budget and confirmed/reserved amounts according to the agreed definition; document whether it means unspent-and-unreserved budget or budget minus confirmed spend only.
- Do not expose internal stack traces or sensitive payment details.
- If settlement is uncertain, expose `pending_reconciliation` at call level and avoid claiming the task has definitively spent or not spent the amount.

### 8.2 `GET /api/v1/tasks/{task_id}/calls`

Returns the service-call records for one task.

```json
{
  "task_id": "2c07b9d1-5b35-4ed4-8a7b-2adcc5b2a010",
  "items": [
    {
      "call_id": "5d8f3e2c-6db3-42c0-a0f4-5f20a0f3bb10",
      "service_id": "scraping-001",
      "status": "succeeded",
      "listed_price_usdc": "0.002000",
      "amount_paid_usdc": "0.002000",
      "latency_ms": 860,
      "transaction_hash": "0xEXAMPLE_HASH",
      "created_at": "2026-10-16T12:00:01Z"
    }
  ]
}
```

### 8.3 Optional cancellation endpoint

`POST /api/v1/tasks/{task_id}/cancel` is optional. Only implement cancellation if the team can safely handle in-flight calls and payment states. A cancellation request must not imply that an already-settled payment has been reversed.

---

## 9. Seller Service Contracts

### 9.1 Seller endpoint design

Each seller must have an independently addressable endpoint and a registry record:

| Seller | Example service ID | Example endpoint |
|---|---|---|
| Data | `data-001` | `/services/data-001` |
| Scraping | `scraping-001` | `/services/scraping-001` |
| Inference | `inference-001` | `/services/inference-001` |

In deployment, the registry must advertise public HTTPS URLs. The example paths are illustrative; agree on exact routes before implementation.

### 9.2 Payment behavior

Every seller endpoint must use the selected official x402 v2 server integration.

- An unpaid request that requires payment must return the SDK's valid x402 v2 `402 Payment Required` challenge.
- The client follows the standard x402 v2 flow.
- The seller must not trust a client-supplied claim of payment.
- Verification and settlement must follow the chosen SDK's lifecycle.
- Do not hand-roll protocol headers or change standard field names.
- Do not return protected output to a request that has not passed the required payment flow.
- Failure and output-validation behavior must be tested against the actual SDK lifecycle.

This document intentionally does not specify raw x402 headers because those must be taken from the official v2 SDK/specification selected by the team.

### 9.3 Data Seller

**Example input**

```json
{
  "query": "renewable energy",
  "limit": 5
}
```

**Example output**

```json
{
  "items": [
    {
      "id": "energy-001",
      "title": "Example energy report",
      "value": "example value",
      "source": "example-source"
    }
  ],
  "count": 1
}
```

### 9.4 Scraping Seller

Scraping must be limited to permitted public sources and respect applicable access rules, robots.txt, rate limits, and website terms.

**Example input**

```json
{
  "url": "https://example.org/article",
  "extract": ["title", "author", "published_at", "text"]
}
```

**Example output**

```json
{
  "url": "https://example.org/article",
  "title": "Example article",
  "author": null,
  "published_at": null,
  "text": "Short normalized article content.",
  "fetched_at": "2026-10-16T12:00:00Z"
}
```

Validate URL schemes and apply an allowlist or other appropriate SSRF protection. Do not allow arbitrary access to localhost, cloud metadata endpoints, private IP ranges, or internal services.

### 9.5 Inference Seller

**Example input**

```json
{
  "operation": "summarize",
  "text": "Text to summarize.",
  "max_words": 100
}
```

**Example output**

```json
{
  "operation": "summarize",
  "summary": "A concise summary of the supplied text.",
  "word_count": 9
}
```

The team may choose another inference operation, but its input/output JSON Schema must be registered and enforced.

### 9.6 Seller schema rules

For each seller:

- Publish `input_schema` and `output_schema` in the registry.
- Validate request inputs before performing the service operation.
- Validate outputs against the seller's declared schema.
- Return safe, structured application errors for ordinary failures, except where the x402 protocol requires its own response.
- Apply timeouts and response-size limits.
- Never include secrets in outputs.
- Keep seller output data separate from claims about payment settlement.

---

## 10. Buyer Agent Internal Interface

The buyer orchestrates registry discovery, planning, paid calls, validation, fallback, and aggregation. Internal Python functions are not necessarily public HTTP endpoints, but their interfaces should be explicit.

### 10.1 Suggested interface

```python
async def execute_task(
    task_id: str,
    user_task: str,
    budget_usdc_units: int,
    max_concurrency: int,
) -> dict:
    """Plan, execute, validate, and aggregate a task within its budget."""
```

Suggested responsibilities:

1. Parse the user request into a plan.
2. Discover eligible services.
3. Rank services by category, price, reputation, and latency.
4. Validate that the plan can fit the budget.
5. Reserve budget before concurrent paid calls.
6. Call sellers through the standard x402 v2 client.
7. Validate each response against the declared output schema.
8. Reconcile payment outcome.
9. Record the call, payment attempt, and settlement evidence.
10. Select a fallback if the result is invalid or the seller fails and budget permits.
11. Aggregate valid outputs.
12. Return a transparent execution explanation and cost breakdown.

### 10.2 Deterministic boundary

The planner/LLM may propose a plan, but a deterministic policy module must approve each purchase. The LLM must not choose arbitrary token addresses, networks, receiving addresses, or spending amounts without registry and policy validation.

---

## 11. Ledger API

### 11.1 `GET /api/v1/ledger`

Returns the list of attempted service calls and their payment outcomes. The ledger must include refused and failed attempts, not just paid calls.

#### Query parameters

| Parameter | Type | Description |
|---|---|---|
| `status` | string | Filter by call/ledger status |
| `service_id` | string | Filter by seller service |
| `task_id` | UUID | Filter by task |
| `from` | ISO timestamp | Start time |
| `to` | ISO timestamp | End time |
| `limit` | integer | Page size |
| `offset` | integer | Page offset |

#### Example response

```json
{
  "items": [
    {
      "call_id": "5d8f3e2c-6db3-42c0-a0f4-5f20a0f3bb10",
      "task_id": "2c07b9d1-5b35-4ed4-8a7b-2adcc5b2a010",
      "timestamp": "2026-10-16T12:00:01Z",
      "buyer_address": "0xBUYER_ADDRESS",
      "service_id": "scraping-001",
      "seller_address": "0xSELLER_ADDRESS",
      "listed_price_usdc": "0.002000",
      "amount_paid_usdc": "0.002000",
      "network": "eip155:84532",
      "token_address": "0xVERIFIED_TOKEN_ADDRESS",
      "transaction_hash": "0xEXAMPLE_HASH",
      "explorer_url": "https://sepolia.basescan.org/tx/0xEXAMPLE_HASH",
      "status": "paid",
      "latency_ms": 860,
      "error_code": null
    }
  ],
  "limit": 20,
  "offset": 0,
  "total": 1
}
```

All addresses and hashes are illustrative. Construct explorer URLs from a verified network configuration and transaction hash; do not trust an arbitrary URL supplied by a seller.

### 11.2 `GET /api/v1/ledger/{call_id}`

Returns detailed information for one service call, including:

- Task and service identity.
- Listed price snapshot.
- Payment attempt status.
- Settlement evidence if any.
- Transaction hash and explorer link if verified.
- Output validation result.
- Latency.
- Safe failure reason.
- Relevant timestamps.

Do not expose private authorization payloads or signing details.

### 11.3 Ledger invariants

- Every attempted call should have a durable record.
- A refused call has no successful settlement unless reconciliation proves otherwise.
- A failed call must not be described as unpaid if the payment outcome is uncertain.
- A paid call must link to verified settlement evidence.
- `paid_output_rejected` means settlement occurred but the output was rejected.
- One transaction must not be counted twice because of retries or duplicate event delivery.

---

## 12. Reputation API

### 12.1 `GET /api/v1/reputation`

Returns current reputation summaries for all registered services.

#### Example response

```json
{
  "items": [
    {
      "service_id": "data-001",
      "success_rate": 0.96,
      "median_latency_ms": 420,
      "listed_price_usdc": "0.002000",
      "total_calls": 25,
      "successful_calls": 24,
      "paid_output_rejected_calls": 1,
      "last_call_at": "2026-10-16T12:15:30Z"
    }
  ]
}
```

### 12.2 Reputation rules

- Define the success-rate denominator once.
- A paid-but-rejected output should lower accepted-result success metrics.
- A policy refusal should not automatically count as a seller failure.
- Use persisted call outcomes as the source of reputation.
- Do not show a 100% success rate when no calls have been observed; show “No history yet.”
- Reputation may influence service ranking but must not override payment safety checks.

---

## 13. Health and Readiness

### 13.1 `GET /health`

Returns process health without exposing secrets.

```json
{
  "status": "ok",
  "service": "di06-agent-economy",
  "timestamp": "2026-10-16T12:00:00Z"
}
```

### 13.2 `GET /ready`

Checks required dependencies, such as database connectivity and essential configuration.

```json
{
  "status": "ready",
  "checks": {
    "database": "ok",
    "payment_configuration": "ok",
    "registry": "ok"
  }
}
```

Do not return private keys, connection strings, or detailed secret values. If a dependency is unavailable, return an appropriate non-success HTTP status and a safe summary.

---

## 14. Idempotency and Replay Safety

### 14.1 Task creation

If `POST /api/v1/tasks` supports `Idempotency-Key`:

- Same key + same normalized request: return the original task or its current state.
- Same key + different request: return `409 IDEMPOTENCY_CONFLICT`.
- Store the key durably with a request fingerprint and result reference.
- Scope keys appropriately so unrelated buyers cannot collide.

### 14.2 Paid service calls

- Assign a unique `call_id` and idempotency key before attempting payment.
- Atomically claim the key before authorizing the protected operation.
- Ensure the same authorization cannot unlock multiple protected responses.
- Enforce uniqueness in durable storage, not only in process memory.
- Test sequential retries and simultaneous duplicate requests.
- If the settlement outcome is unknown, reconcile before creating another payment attempt.

### 14.3 Important distinction

Application idempotency prevents duplicate task/call execution in the application. It does not replace the x402 v2 protocol's payment authorization and replay controls. Both layers must be tested.

---

## 15. Security and Validation Rules

1. Never expose buyer or seller private keys through frontend variables, API responses, or logs.
2. Validate price, token, network, and recipient against trusted registry configuration before authorizing payment.
3. Convert money to integer base units before comparisons.
4. Enforce task budgets atomically under concurrency.
5. Apply request timeouts and response-size limits.
6. Validate seller output against the declared JSON Schema before accepting it.
7. Restrict scraping URLs to permitted public targets and prevent SSRF.
8. Validate all path/query/body inputs.
9. Use HTTPS for public deployed endpoints.
10. Apply CORS only to intended frontend origins; CORS is not authentication.
11. Do not reveal stack traces or database details to clients.
12. Construct explorer links from a trusted network map.
13. Record safe failure codes and reasons.
14. Treat external seller output as untrusted data.
15. Keep protocol-specific x402 behavior compatible with the official v2 implementation.

---

## 16. OpenAPI and Type Synchronization

FastAPI should generate an OpenAPI document from the actual route and Pydantic definitions.

Recommended workflow:

1. Define request and response models in a shared backend schemas module.
2. Use those models in endpoint signatures.
3. Generate `/openapi.json`.
4. Review it against this document.
5. Use the agreed contract to create/update frontend TypeScript types.
6. Add tests for important request/response shapes.
7. Update this document whenever a breaking API change is approved.

Do not maintain a documentation contract that differs silently from the running API.

### 16.1 Suggested shared model names

- `ServiceSummary`
- `ServiceDetail`
- `ServiceSearchResponse`
- `TaskCreateRequest`
- `TaskCreateResponse`
- `TaskStatusResponse`
- `TaskCallSummary`
- `LedgerEntry`
- `LedgerListResponse`
- `ReputationSummary`
- `ApiError`

The team may rename these, but should choose one set of names and use it consistently.

---

## 17. Example End-to-End Interaction

This is a conceptual application-level flow. The seller's actual HTTP 402 exchange must follow the selected official x402 v2 SDK.

1. Frontend sends a task and budget to `POST /api/v1/tasks`.
2. Buyer creates a task record and plans the required services.
3. Buyer queries `GET /api/v1/services` and selects eligible sellers.
4. Buyer reserves the required budget for a call in the database.
5. Buyer requests the seller endpoint through the x402 v2 client.
6. An unpaid request receives the seller's valid x402 v2 `402 Payment Required` challenge.
7. The deterministic payment policy verifies price, network, asset, recipient, budget, and replay state.
8. The buyer follows the official x402 v2 payment flow.
9. The seller performs the protected operation according to its SDK lifecycle.
10. The application verifies settlement evidence and records the payment attempt and settlement.
11. Buyer validates the output schema.
12. If output is valid, buyer stores the result and updates reputation.
13. If output is invalid after settlement, the call is recorded as `paid_output_rejected`; fallback is considered only if budget permits.
14. Frontend polls `GET /api/v1/tasks/{task_id}` or uses another explicitly implemented status mechanism.
15. Dashboard queries `GET /api/v1/ledger` and displays the status, cost, latency, and verified explorer link.

---

## 18. Acceptance Tests for API Contracts

| Test | Expected behavior |
|---|---|
| Registry category filter | Returns only matching category |
| Registry price filter | Returns only services within the requested price range |
| Inactive service | Buyer does not select it for a new call |
| Task creation | Returns a stable task ID and status |
| Invalid budget | Rejected with a validation error |
| Budget too low | Buyer refuses purchase or selects an affordable eligible fallback |
| Concurrency | Supports at least 3 concurrent calls without overspending |
| Price manipulation | A seller challenge above registry price is refused |
| Recipient mismatch | Payment is refused |
| Wrong token/network | Payment is refused |
| Sequential replay | One authorization does not unlock multiple responses |
| Parallel replay | Duplicate concurrent requests cannot produce duplicate successful paid results/settlement |
| Seller timeout | Call is persisted; uncertain payment is reconciled before retry |
| Invalid output | Output is rejected and seller reputation is lowered |
| Paid invalid output | Payment remains recorded and status is `paid_output_rejected` |
| Ledger completeness | Refused and failed attempts are visible |
| Ledger settlement | Paid record links to verified transaction evidence |
| Reputation empty history | UI shows no history instead of a misleading perfect score |
| Error safety | Error responses do not reveal secrets or stack traces |
| External client compatibility | Unmodified x402 v2 client can pay a project seller |
| External seller compatibility | Project buyer can pay an unmodified x402 v2 seller |

---

## 19. Team Ownership and Change Control

| Contract area | Primary owner | Required collaborators |
|---|---|---|
| Registry API | Member 3 | Member 2, Member 4 |
| Buyer/task API | Member 3 | Member 1, Member 4 |
| Seller endpoint schemas | Member 2 | Member 1, Member 3 |
| x402 payment lifecycle | Member 1 | Member 2, Member 3 |
| Ledger API | Member 4 | Member 1, Member 3 |
| Reputation API | Member 3 / Member 4 | Member 2 |
| Health/readiness | Integration owner | All |
| Shared errors/status enums | Integration owner | All |

### Contract change process

1. Propose the change in the team channel or pull request.
2. Identify affected consumers.
3. Update this document and shared schema definitions.
4. Update backend/frontend implementations and tests.
5. Run integration tests.
6. Merge only after the affected owners agree.

Do not silently change a shared field or status in one branch.

---

## 20. Final Contract Freeze Checklist

Before parallel implementation:

- [ ] Confirm `/api/v1` as the application API prefix.
- [ ] Freeze service identifiers and category values.
- [ ] Freeze the registry response fields.
- [ ] Freeze task request and response fields.
- [ ] Decide whether task submission is synchronous or asynchronous.
- [ ] Freeze task, call, payment, settlement, and ledger statuses.
- [ ] Agree on public USDC decimal strings and internal integer base units.
- [ ] Confirm the meaning of `remaining_usdc`.
- [ ] Confirm seller endpoint paths and their x402 v2 integration.
- [ ] Agree on standard application error shape.
- [ ] Define idempotency key scope and duplicate behavior.
- [ ] Agree on how uncertain settlement is represented.
- [ ] Agree on ledger fields and explorer-link generation.
- [ ] Agree on reputation calculation.
- [ ] Generate and inspect FastAPI OpenAPI output.
- [ ] Add contract tests before the main integration phase.

---

## 21. Final Rule

**Treat this file as the shared API agreement, not as a substitute for the official x402 v2 protocol specification.** Project-defined routes and JSON models are controlled by the team; x402 payment challenges, authorization, verification, and settlement behavior must remain compatible with the selected official v2 implementation.

Freeze the shared contracts early, validate all payment-sensitive fields deterministically, and keep the API documentation synchronized with the running code.
