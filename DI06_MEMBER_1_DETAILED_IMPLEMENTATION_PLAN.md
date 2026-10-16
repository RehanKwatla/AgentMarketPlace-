# DI-06 — Member 1 Implementation Plan
## Payment Engine & Security

**Project:** DI-06 Pay-per-Call Agent Economy  
**Owner:** Member 1  
**Branch:** `feature/payments`  
**Target network:** Base Sepolia only for the hackathon demo  
**Primary goal:** Execute paid seller-agent calls safely, enforce payment policy and budget limits, prevent duplicate payment attempts, verify settlement, and persist auditable payment records.

---

## 1. Mission and Definition of Success

Member 1 owns the payment execution layer. It should be the only application layer that initiates paid calls.

The core demonstration should prove this end-to-end flow:

1. The buyer orchestrator requests a paid seller operation.
2. The payment engine loads trusted service terms.
3. The engine checks policy, budget, and idempotency.
4. The official x402 v2 SDK executes the supported payment flow.
5. Settlement is verified using evidence supported by the selected scheme.
6. Payment attempt and settlement records are persisted.
7. The result is returned to the buyer and is visible in the ledger.

**Success means one real, low-value Base Sepolia payment has verified evidence and a persisted ledger record.** Do not claim success based only on HTTP 200, a seller's assertion, or a transaction hash.

Build this thin vertical slice early, then add hardening.

## 2. Responsibilities

- Validate service price, recipient, token, network, payment scheme, expiry, and relevant request binding.
- Enforce task budgets with integer token atomic units.
- Reserve budget atomically to prevent concurrent overspending.
- Persist idempotency keys and prevent duplicate payment attempts.
- Wrap the official x402 v2 SDK in a small adapter.
- Track payment attempts and verify settlement.
- Reconcile uncertain payment outcomes without blindly retrying.
- Persist safe, useful payment records and error codes.
- Integrate with Member 3's buyer orchestrator and Member 4's database/ledger.
- Add unit, concurrency, failure-path, and integration tests.

## 3. Shared Contracts — Agree Before Coding

Before implementation, agree on the request/result schema with Members 3 and 4. Do not independently invent competing field names or status definitions.

### Suggested request interface

```python
async def execute_paid_call(
    task_id: str,
    call_id: str,
    service_id: str,
    input_payload: dict,
    idempotency_key: str,
):
    ...
```

The exact types should follow the existing repository and shared API contract.

### Suggested result fields

- `task_id`, `call_id`, `service_id`
- payment status
- agreed amount and token/currency
- network
- seller output or output reference, if available
- transaction/settlement reference and verification details, when available
- safe error code and explanatory message, if applicable

### Standard statuses

| Status | Meaning |
|---|---|
| `paid` | Settlement is verified and the required seller output passed validation. |
| `paid_output_rejected` | Settlement is verified, but seller output failed validation. |
| `refused` | A policy, authorization, or budget check rejected the request before payment. |
| `failed_and_not_charged` | Failure is established and evidence supports that no charge occurred. |
| `pending_reconciliation` | Payment outcome is uncertain and must be checked before another attempt. |

Do not treat `paid_output_rejected` as an unpaid request. Do not label an uncertain outcome as `failed_and_not_charged`.

---

## 4. Recommended Repository Structure

Reuse existing modules where possible.

```text
backend/
└── app/
    └── payments/
        ├── __init__.py
        ├── service.py
        ├── policy.py
        ├── budget.py
        ├── idempotency.py
        ├── x402_adapter.py
        ├── settlement.py
        ├── schemas.py
        └── errors.py

backend/tests/payments/
├── test_policy.py
├── test_budget.py
├── test_idempotency.py
├── test_x402_adapter.py
├── test_settlement.py
└── test_payment_service.py
```

### Module responsibilities

| Module | Responsibility | Priority |
|---|---|---|
| `schemas.py` | Typed request, result, status, and error models | P0 |
| `policy.py` | Validate trusted service terms and payment constraints | P0 |
| `x402_adapter.py` | Thin wrapper around the official x402 v2 SDK | P0 |
| `service.py` | Orchestrate the full paid-call lifecycle | P0 |
| `budget.py` | Atomic budget reservations, settlement, and release | P0 |
| `idempotency.py` | Durable duplicate/replay protection | P0 |
| `errors.py` | Consistent safe error types and codes | P0 |
| `settlement.py` | Verify outcomes and reconcile uncertain attempts | P1 |

---

## 5. Implementation Phases

### Phase 1 — Inspect the repository and freeze contracts
**Target: first 20–30 minutes**

1. Pull the latest main branch and create `feature/payments`.
2. Inspect the backend framework, existing payment code, database layer, seller endpoints, environment configuration, and tests.
3. Read the shared API contract and database schema.
4. Agree on the `execute_paid_call()` request/result contract with Member 3.
5. Agree on persistence/repository methods with Member 4.
6. Confirm the exact supported x402 v2 SDK APIs, payment scheme, token, recipient format, and Base Sepolia configuration from the installed SDK and authoritative documentation.

**Deliverable:** A shared typed contract and a minimal working branch.

Do not guess SDK method names or copy examples from an incompatible SDK version.

### Phase 2 — Implement the policy layer
**Target: next 30–45 minutes**

Implement `policy.py`. Validate before payment initiation:

- Service exists and is enabled.
- Price matches the trusted registry/configuration.
- Token and network match approved configuration.
- Recipient matches the registered seller recipient.
- Payment scheme is supported.
- Amount is positive and within configured limits.
- Payment requirements are valid and not expired.
- Request is authorized for the task.
- Relevant service/call binding is checked where supported.
- Idempotency key is not being reused for different request contents.

The client/planner must not be allowed to redefine price, token, recipient, or network.

Example pseudocode:

```python
def validate_payment_request(request, service, policy):
    if not service.enabled:
        raise PaymentRefused("SERVICE_DISABLED")

    if request.amount_atomic != service.price_atomic:
        raise PaymentRefused("PRICE_MISMATCH")

    if service.network != policy.allowed_network:
        raise PaymentRefused("NETWORK_NOT_ALLOWED")

    if service.token_address != policy.allowed_token_address:
        raise PaymentRefused("TOKEN_NOT_ALLOWED")

    if service.recipient != policy.expected_recipient:
        raise PaymentRefused("RECIPIENT_MISMATCH")
```

Adapt this example to actual schemas. Validate addresses and protocol fields correctly; do not rely on casual string checks alone.

### Phase 3 — Implement integer accounting and budget reservations
**Target: next 30–45 minutes**

Implement `budget.py`.

- Use integer token atomic units; never use floating-point amounts.
- Confirm token decimals from the configured token.
- Track task budget, settled/spent amount, active reservations, and available amount.
- Make reservation atomic in the database using a row lock or an equivalent conditional update.
- Insert a unique reservation record in the same transaction as the budget update.
- Release a reservation only when the outcome establishes that the payment was not initiated/charged.
- Convert the reservation into spent/settled accounting after verified settlement.
- Keep uncertain exposures accounted for until reconciliation determines the outcome.

Conceptual formula:

```text
available = budget - spent - reserved
```

A read-then-write sequence without locking/atomic conditions is unsafe: concurrent requests can both spend the same available balance.

### Phase 4 — Implement durable idempotency and replay protection
**Target: next 30–45 minutes**

Implement `idempotency.py`.

Persist at least:

- idempotency key
- task ID, call ID, and service ID
- canonical request hash
- payment attempt ID
- current status
- timestamps
- transaction/settlement reference when known

Expected behavior:

| Situation | Behavior |
|---|---|
| New key | Create one operation and start processing. |
| Same key, same request, completed | Return the existing result; do not charge again. |
| Same key, same request, processing | Return/wait on the existing operation; do not create another payment. |
| Same key, different request | Reject with an idempotency conflict. |
| Timeout with unknown outcome | Reconcile the existing attempt before any new attempt. |

Use a database uniqueness constraint for the appropriate idempotency scope. An application-only lookup has a race condition.

Idempotency keys are not a substitute for protocol-level replay protection. Respect the selected x402 scheme's nonce, expiry, signature, and request-binding rules where applicable.

### Phase 5 — Integrate the official x402 v2 SDK
**Start as early as possible; do not defer the first payment**

Implement `x402_adapter.py` as a thin wrapper around the official SDK.

Expected responsibilities:

1. Use the configured server-side signer/client.
2. Make the paid request to the seller endpoint.
3. Handle the payment-required response using the SDK's supported flow.
4. Validate payment requirements against trusted service terms.
5. Let the SDK perform supported authorization/signing/submission steps.
6. Capture the seller response and payment/settlement metadata.
7. Return a typed result to `service.py`.

Illustrative interface only:

```python
class X402Adapter:
    async def execute_paid_request(
        self,
        service_config,
        payload,
        call_id,
    ):
        ...
```

Use the actual APIs of the installed SDK version. Do not hand-roll protocol signatures or payment headers unnecessarily.

#### Secret and environment rules

- Keep signer/private-key configuration server-side.
- Never expose private keys through frontend variables.
- Never commit keys or seed phrases.
- Never log authorization headers or raw signed payment payloads.
- Use a dedicated test wallet with a small balance.
- Use Base Sepolia only for the hackathon demo; do not use mainnet.

**Milestone:** Complete one low-value Base Sepolia payment and persist its real settlement evidence before building advanced abstractions.

### Phase 6 — Settlement verification and reconciliation

Implement `settlement.py`.

Keep these facts separate:

1. **Payment initiation:** an attempt was made.
2. **Settlement evidence:** the selected protocol/source reports a verifiable outcome.
3. **Business result:** seller output passed or failed schema/quality validation.

Verify the evidence supported by the selected x402 scheme, including where applicable:

- correct network
- expected token and recipient
- expected amount
- relevant transaction or settlement reference
- protocol-supported verification result
- consistency with the stored payment attempt

A transaction hash, HTTP 200, or seller assertion alone is not enough. Schemes can expose different evidence; implement against the actual scheme in use.

#### Failure handling

| Event | Required behavior |
|---|---|
| Policy rejection before payment | `refused`; do not initiate payment. |
| Failure before payment, no charge established | `failed_and_not_charged`. |
| Timeout after possible submission | `pending_reconciliation`. |
| Settlement verified, output invalid | `paid_output_rejected`. |
| Settlement verified, output valid | `paid`. |
| Evidence unavailable or contradictory | Remain pending and record the reason. |

Add a reconciliation function that rechecks pending attempts by their existing references. A manual/API-triggered reconciliation route is acceptable for the first demo; a background worker can be added if time allows.

**Never blindly retry an uncertain payment.** Reconcile the existing attempt first.

### Phase 7 — Orchestrate the lifecycle in `service.py`

Keep `service.py` as the coordinator; policy, budget, idempotency, SDK, and settlement details belong in their respective modules.

Recommended sequence:

1. Validate request shape and required IDs.
2. Load trusted service terms.
3. Check idempotency.
4. Validate policy and authorization.
5. Atomically reserve budget.
6. Persist the payment attempt before critical external operations.
7. Execute the x402 adapter with bounded timeouts.
8. Verify settlement or mark `pending_reconciliation`.
9. Validate seller output against its agreed schema.
10. Persist final status, evidence, and audit event.
11. Return the agreed result contract.

Keep network calls outside long-running database transactions. Persist state before and after critical external actions so a process crash does not erase whether a payment may have been submitted.

Do not promise refunds/reversals unless the selected mechanism supports them and the reversal itself is verified.

### Phase 8 — Integrate with Member 4's persistence and ledger

Member 4 owns the database/ledger implementation. Member 1 should agree on repository methods for:

- creating/retrieving an idempotent payment attempt
- reserving/releasing task budget
- updating attempt status
- recording settlement evidence
- finding pending attempts for reconciliation
- appending audit events

Payment records should correlate task, service call, payment attempt, and settlement. Follow the shared schema rather than creating a separate permanent database.

Never persist private keys, seed phrases, or raw payment authorization secrets. If the database layer is not ready, use a small repository interface and test implementation temporarily, then integrate the real repository promptly.

---

## 6. Testing Plan

Create tests under `backend/tests/payments/`. Use mocks for most tests so they are quick and do not spend funds; keep one controlled low-value Base Sepolia test for the real payment path.

### Policy tests

- Valid service terms are accepted.
- Incorrect price is rejected.
- Incorrect recipient, token, or network is rejected.
- Expired or unsupported payment requirements are rejected.
- Disabled service or unauthorized task is rejected before payment.

### Budget and idempotency tests

- Insufficient budget prevents payment initiation.
- Concurrent reservations cannot exceed the task budget.
- Same key and same request do not create a second payment.
- Same key with different payload is rejected.
- Idempotency state survives backend restart.
- Uncertain outcomes do not cause automatic duplicate payment.

### Payment lifecycle tests

- Verified payment plus valid output produces `paid`.
- Verified payment plus invalid output produces `paid_output_rejected`.
- Timeout after submission produces `pending_reconciliation`.
- Reconciliation updates the existing attempt without duplicating it.
- Confirmed pre-payment failure releases its reservation.
- Inconsistent or missing settlement evidence is not treated as success.

### Security and integration tests

- Secrets never appear in logs.
- Member 3 can invoke the agreed interface.
- Member 4 can query the resulting ledger record.
- A real low-value testnet payment produces verifiable evidence.

---

## 7. Suggested 24-Hour Schedule

| Time | Focus | Deliverable |
|---|---|---|
| Hour 0–1 | Inspect repo, agree contracts, configure SDK/test wallet | Branch and shared schema |
| Hour 1–3 | First paid vertical slice | One testnet payment and persisted settlement |
| Hour 3–6 | Policy and accounting | Trusted-term validation and atomic budget reservation |
| Hour 6–9 | Idempotency and recovery | Durable duplicate prevention and reconciliation |
| Hour 9–12 | Integrate buyer and ledger | Member 3 and Member 4 can use the payment engine |
| Hour 12–16 | Security/failure tests | Concurrency, mismatch, timeout, and invalid-output tests |
| Hour 16–20 | End-to-end demo | Buyer → seller → verified payment → ledger |
| Hour 20–24 | Stabilize and rehearse | Critical fixes and credible demo evidence |

If time becomes tight, prioritize:

1. One verified testnet payment end to end.
2. Shared API and persisted ledger integration.
3. Budget enforcement and durable idempotency.
4. Uncertain-outcome reconciliation.
5. Extra monitoring and polish.

Do not remove duplicate-charge safeguards to speed up the happy path.

---

## 8. Definition of Done

- [ ] One real low-value Base Sepolia payment has been completed using the supported x402 v2 flow.
- [ ] Settlement was verified using evidence supported by the selected scheme.
- [ ] Payment attempt and settlement records are persisted.
- [ ] Trusted price, network, token, recipient, scheme, and expiry are validated.
- [ ] Budget reservations remain safe under concurrent requests.
- [ ] Duplicate calls cannot create duplicate payment attempts.
- [ ] Uncertain outcomes remain pending until reconciled.
- [ ] Member 3 can invoke the agreed interface without implementing payment logic.
- [ ] Member 4 can display the resulting ledger record.
- [ ] Secrets do not appear in frontend code, logs, or committed files.
- [ ] Automated tests cover successful and failed paths.
- [ ] Setup, test commands, demo steps, actual results, and remaining limitations are documented.

---

## 9. Antigravity Coding-Agent Prompt

Use the following prompt in Antigravity to direct implementation.

> **Objective:** Implement Member 1's Payment Engine & Security workstream for DI-06 Pay-per-Call Agent Economy.
>
> **Before coding:** Inspect the repository, framework, database layer, environment configuration, API contracts, and tests. Work on `feature/payments`. Reuse existing modules and agree on typed request/result and repository contracts with Members 3 and 4.
>
> **Required modules:** `schemas.py`, `policy.py`, `budget.py`, `idempotency.py`, `x402_adapter.py`, `settlement.py`, `service.py`, and `errors.py` under `backend/app/payments/`, plus tests under `backend/tests/payments/`. Extend existing equivalents if they already exist.
>
> **Required behavior:**
>
> 1. Validate trusted service price, recipient, network, token, scheme, expiry, authorization, and applicable request binding before payment.
> 2. Use integer token atomic units.
> 3. Implement atomic budget reservations safe under concurrency.
> 4. Persist idempotency keys and canonical request hashes; reject key reuse with different contents.
> 5. Integrate the official x402 v2 SDK using its actual installed APIs and authoritative documentation.
> 6. Persist attempts before critical external actions and persist outcomes afterward.
> 7. Verify settlement using evidence supported by the selected scheme. Never treat HTTP 200 or a transaction hash alone as proof.
> 8. Use statuses `paid`, `paid_output_rejected`, `refused`, `failed_and_not_charged`, and `pending_reconciliation` consistently.
> 9. Never blindly retry an uncertain payment; reconcile the existing attempt first.
> 10. Distinguish payment settlement from seller-output validation.
> 11. Keep signing secrets on the backend; never log or expose them.
> 12. Use Base Sepolia only for the hackathon demo.
> 13. Integrate with Member 3 through the agreed payment interface and Member 4 through the agreed persistence contract.
>
> **Implementation order:** First deliver one thin vertical slice: one seller endpoint, one x402 payment, verified settlement evidence, and one persisted ledger record. Then add policy validation, atomic budget reservation, durable idempotency, reconciliation, and security tests.
>
> **Tests:** Cover valid payment, wrong price/token/network/recipient, expired requirements, insufficient budget, concurrent reservations, duplicate requests, idempotency conflicts, timeout after submission, settlement verification, invalid output after payment, secret redaction, and persistence. Use mocks for routine tests and one controlled low-value Base Sepolia test for the real payment path.
>
> **Constraints:** Do not fabricate transaction hashes or settlement evidence. Do not mark uncertain outcomes as paid or not charged. Do not blindly retry uncertain payments. Do not trust client-supplied prices or recipients. Do not use floating-point accounting, commit private keys, expose secrets to the frontend, rebuild the whole app, or invent a separate permanent ledger.
>
> **Final handoff:** Report files changed, environment setup (without secret values), tests actually run and their real results, exact testnet demo steps, evidence actually observed, and all remaining limitations. Do not claim a test or payment succeeded unless it actually did.

---

## 10. Final Recommendation

**Build the first real paid call and persisted settlement record before adding advanced abstractions.** It gives the rest of the team a real integration target and proves the core payment path works. After that, prioritize budget safety, idempotency, and uncertain-settlement handling over optional features.
