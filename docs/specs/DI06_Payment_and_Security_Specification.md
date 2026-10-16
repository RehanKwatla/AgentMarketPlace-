# DI-06 — Payment & Security Specification

**Project:** Pay-per-Call Agent Economy  
**Document type:** Implementation specification  
**Status:** Proposed implementation contract for the hackathon  
**Payment environment:** Base Sepolia testnet only  
**Protocol requirement:** x402 v2 interoperability  
**Primary objective:** Ensure every paid service call is authorized, bounded by budget, protected against replay, independently verifiable, and auditable.

---

## 1. Purpose

This document defines the payment lifecycle and security controls for the DI-06 solution. It is the implementation reference for the payment/security owner and the integration contract for the buyer agent, seller agents, registry, database, and ledger dashboard.

The system must not treat an HTTP response, a database row, or an LLM statement as proof of payment. A payment is considered settled only when the configured x402 v2 flow and the relevant on-chain evidence support that conclusion.

### 1.1 In scope

- x402 v2 payment challenges and client/server interoperability
- Testnet token, network, recipient, price, and scheme validation
- Buyer budget enforcement, including parallel calls
- Replay prevention and idempotency
- Settlement and payment-attempt recording
- Safe behavior for seller errors, timeouts, invalid output, and uncertain outcomes
- Secrets, wallet, API, endpoint, and log security
- Reconciliation, auditability, and security tests

### 1.2 Out of scope for the initial implementation

- Production funds or mainnet payments
- Custodial wallet service
- Cross-chain bridges
- Escrow, automatic refunds, or dispute arbitration
- A custom payment protocol replacing x402
- Treating an LLM-generated plan as payment authorization

Escrow/refunds and a second network are stretch goals only. Do not implement them before the mandatory safety controls pass.

---

## 2. Security Principles

1. **Testnet only:** use fresh, low-value test wallets on Base Sepolia. Never use a mainnet wallet or real funds.
2. **Fail closed:** if required payment metadata, registry data, signature verification, budget state, or settlement status cannot be validated, do not proceed as though payment succeeded.
3. **Backend authority:** only the trusted backend payment policy may authorize a payment. The frontend and LLM planner are untrusted inputs.
4. **Registry is the price authority:** the buyer must compare the seller's current x402 challenge with the registered service terms before authorizing payment.
5. **Atomic spending control:** concurrent calls must reserve budget atomically before any payment authorization is created or signed.
6. **One authorization, one response:** a valid payment authorization must not unlock multiple successful responses through serial or parallel replay.
7. **Evidence before status:** record a settlement as verified only after checking authoritative x402/facilitator and chain evidence appropriate to the SDK lifecycle.
8. **No charge for seller failure:** seller errors, timeouts, or invalid output that is detected before settlement must not cause settlement. If payment has already settled and output is subsequently rejected, record `paid_output_rejected`; do not falsely mark it as uncharged.
9. **Minimize secrets:** private keys and API keys must never be sent to the browser, committed to source control, or written to ordinary logs.
10. **Auditable decisions:** record why each payment was approved, refused, rejected, or left pending reconciliation.

---

## 3. Threat Model

| Threat | Example | Required mitigation |
|---|---|---|
| Price manipulation | Seller returns a 0.08 USDC challenge for a service listed at 0.02 USDC | Refuse before signing |
| Recipient substitution | Challenge uses a different `payTo` address | Refuse before signing |
| Wrong network/token | Challenge points to a different chain or token | Refuse before signing |
| Unsupported scheme | Challenge uses a scheme not approved by this buyer | Refuse before signing |
| Budget race | Several concurrent calls each see the same remaining balance | Atomic reservation/locking |
| Replay | Same authorization or paid request is submitted repeatedly | Durable idempotency, authorization uniqueness, seller-side replay protection |
| Duplicate payment | Client retries after a timeout with uncertain settlement | Reconcile before retry; do not blindly resubmit |
| Seller outage | Seller times out or returns 5xx | No settlement; mark failed and not charged once confirmed |
| Invalid seller output | Output fails the registered JSON Schema | Reject output, flag seller; ensure settlement ordering follows the rule in §8 |
| Forged ledger row | Application records `paid` without a real transfer | Chain/facilitator reconciliation; separate attempts from verified settlements |
| Secret leakage | Wallet key appears in frontend bundle, Git, exception, or log | Environment secrets, secret scanning, redaction |
| Prompt injection | Seller output tells the buyer to ignore budget policy | Treat output as untrusted data; deterministic payment gate |
| Registry poisoning | Service metadata is altered to direct payments to an attacker | Validate registry integrity, restrict writes, audit changes |
| Request confusion | Payment for one request is reused for a different body or service | Bind authorization/idempotency to a canonical request identity |
| Denial of service | Repeated invalid 402s or expensive seller calls | Rate limits, bounded payloads, concurrency and timeout limits |

### 3.1 Trust boundaries

- **Browser:** untrusted; may request tasks and view results but must not sign or hold payment secrets.
- **Buyer planner/LLM:** untrusted for payment policy; may propose services but cannot approve spending.
- **Buyer payment service:** trusted policy enforcement component; validates, reserves budget, and coordinates the official x402 client.
- **Seller service:** untrusted until its response is validated; must enforce one-time payment semantics.
- **Registry:** trusted source of declared service terms only if protected and audited; it is not proof that a seller's challenge is valid.
- **Facilitator and public chain:** external dependencies; their responses and transaction evidence must be checked, and uncertain outcomes must remain uncertain until reconciled.
- **Database:** durable audit/state store, not by itself proof of on-chain settlement.

---

## 4. Payment Environment and Configuration

### 4.1 Required network

- Network: **Base Sepolia**
- CAIP-2 network identifier: `eip155:84532`
- RPC reference: `https://sepolia.base.org`
- Explorer: BaseScan Sepolia
- Facilitator reference: `https://x402.org/facilitator`

Use the official x402 v2 SDK and its supported facilitator workflow. Verify package names, API signatures, payment scheme support, and network/token configuration against the current official SDK documentation before implementation. Do not invent x402 headers or manually reimplement cryptographic verification when the SDK provides it.

### 4.2 Token configuration

Use the approved Base Sepolia test USDC configuration from the current official x402/Circle documentation. The project brief references token address:

`0x036CbD53842c5426634e7929541eC2318f3dCF7`

Treat this address as a value to verify against the official source before use, not as an unchecked hard-coded assumption.

USDC uses 6 decimal places. Store and calculate amounts as integer base units:
- `1 USDC = 1,000,000` base units
- `0.10 USDC = 100,000` base units
- `0.02 USDC = 20,000` base units
- `0.001 USDC = 1,000` base units

Do not use floating-point arithmetic for payment decisions. A decimal string may be used at the API boundary, but parse it exactly into an integer base-unit amount.

### 4.3 Environment variables

Example names only; use the exact variable names expected by the chosen SDK:

```dotenv
APP_ENV=development
PAYMENT_NETWORK=eip155:84532
PAYMENT_TOKEN_ADDRESS=<verified_base_sepolia_usdc_address>
X402_FACILITATOR_URL=https://x402.org/facilitator
BUYER_WALLET_PRIVATE_KEY=<server-side-secret>
BUYER_WALLET_ADDRESS=<public-address>
PAYMENT_MAX_PER_CALL_USDC=0.10
PAYMENT_DEFAULT_TASK_BUDGET_USDC=0.05
PAYMENT_REQUEST_TIMEOUT_SECONDS=15
PAYMENT_RECONCILIATION_ENABLED=true
```

Rules:
- `.env` must be ignored by Git and must never be committed.
- Commit only `.env.example` with placeholders.
- Never put private keys, seed phrases, facilitator credentials, or database passwords in Vite variables such as `VITE_*`; frontend variables are public.
- Do not print full environment dumps in logs or debugging output.
- If a secret is exposed, stop using that key, rotate/revoke it where possible, inspect recent activity, and replace the secret.

---

## 5. Authoritative Payment Terms

Before payment, the backend must have a trusted snapshot of the service terms selected from the registry.

For each service, the snapshot must include at least:

- `service_id`
- `seller_id`
- `category`
- `endpoint_url`
- `listed_price_base_units`
- `network_id`
- `token_address`
- `pay_to_address`
- `scheme`
- `input_schema_version`
- `output_schema_version`
- `registry_version` or immutable terms hash
- `active` status

### 5.1 Challenge comparison

When the seller returns an x402 v2 payment challenge, compare the relevant normalized payment requirements against the service snapshot:

| Field | Required check |
|---|---|
| Amount | Must be parseable exactly and must not exceed the registered per-call price |
| Network | Must equal the approved network, `eip155:84532` |
| Asset/token | Must match the verified approved test USDC address for that network |
| Recipient (`payTo`) | Must match the registry recipient exactly after safe address normalization |
| Scheme | Must be explicitly supported by the configured x402 v2 client and project policy |
| Resource/service | Must correspond to the requested registered service and canonical request |
| Expiry/validity | Must be valid under the official protocol/SDK rules |
| Extra requirements | Reject unknown or unsupported requirements rather than silently ignoring payment-relevant fields |

**Mandatory rule:** if the challenge amount exceeds the registry price, or if network, token, recipient, or scheme differs from the approved service terms, refuse to pay. Record the reason in the ledger/audit trail.

A registry listing is not permission to ignore a challenge mismatch. A mismatch indicates a potential attack or configuration error.

### 5.2 Price semantics

- The registered per-call price is the maximum seller charge accepted for that service call.
- The buyer must never silently accept a higher price because an LLM recommends the service.
- A seller may quote a lower amount only if the current x402 scheme and SDK flow support that behavior and the implementation records both the listed and actual amount.
- If the project uses a task budget, it must cover all planned calls and any concurrently reserved calls.
- Network fees or facilitator behavior must be understood from the chosen implementation. Do not claim that the listed service price includes every possible external fee unless the payment flow guarantees that.

---

## 6. Buyer Payment Authorization State Machine

Use a durable state machine. Exact names may map to the database/API schema, but transitions must remain explicit.

```text
PLANNED
  -> BUDGET_RESERVED
  -> REQUEST_SENT
  -> CHALLENGE_RECEIVED
  -> CHALLENGE_VALIDATED
  -> PAYMENT_AUTHORIZED
  -> PAYMENT_SUBMITTED / VERIFICATION_PENDING
  -> SETTLEMENT_VERIFIED
  -> RESPONSE_RECEIVED
  -> OUTPUT_VALIDATED
  -> COMPLETED
```

Failure and alternate states:

```text
PLANNED -> REFUSED
BUDGET_RESERVED -> REFUSED
REQUEST_SENT -> FAILED_AND_NOT_CHARGED
CHALLENGE_RECEIVED -> REFUSED
CHALLENGE_VALIDATED -> REFUSED
PAYMENT_SUBMITTED -> RECONCILIATION_PENDING
SETTLEMENT_VERIFIED -> PAID_OUTPUT_REJECTED
OUTPUT_VALIDATED -> COMPLETED
```

State transitions must be persisted. Do not use a single boolean such as `paid=true` to represent the entire lifecycle.

### 6.1 Authorization gate

Only the payment service may authorize a payment. It must verify all of the following before signing or submitting payment:

1. The user/task is authenticated or otherwise authorized for the requested operation.
2. The task is active and has a unique task/call identity.
3. The service is active and its registry terms snapshot is available.
4. The call has a valid, unique idempotency key.
5. The payment challenge matches the registry and configured network/token.
6. The exact amount is not above the registered price.
7. The budget reservation is valid and covers this call.
8. The request has not already consumed a payment authorization.
9. The challenge is within its validity window.
10. The official SDK accepts the requirements and selected scheme.

If any mandatory check fails, do not sign. Record a deterministic refusal reason.

### 6.2 LLM boundary

The LLM may propose:
- which service to use,
- the sequence of calls,
- the expected usefulness of a result,
- a user-facing explanation.

The LLM must not:
- change the task budget,
- change the registry price or recipient,
- override a mismatch,
- sign or submit payment,
- mark a call as paid,
- fabricate a transaction hash,
- retry an uncertain payment without reconciliation.

A deterministic backend policy must enforce every payment constraint regardless of the model output.

---

## 7. Budget Enforcement and Concurrency

### 7.1 Integer accounting

Store all monetary values in integer USDC base units. Keep these separate:

- `task_budget_base_units`
- `budget_reserved_base_units`
- `amount_authorized_base_units`
- `amount_submitted_base_units`
- `amount_settled_base_units`
- `amount_released_base_units`

The UI may format integer units as USDC for display. Do not use a floating-point total as the enforcement source.

### 7.2 Atomic reservation

The reservation must be atomic across concurrent requests and workers. Use a database transaction with row locking or an equivalent atomic conditional update. A read-then-write sequence without a lock is not safe.

Conceptual invariant:

```text
settled_spend + active_reservations <= task_budget
```

If a call's maximum charge is `P`, reserve `P` before payment authorization. If the reservation would exceed the remaining budget, refuse the call. On confirmed non-payment, release the reservation. On confirmed settlement, convert the reservation to actual settled spend and release any unused portion. On uncertain payment status, retain the reservation until reconciliation resolves the outcome.

### 7.3 Parallel calls

The implementation must support `max_concurrency >= 3`, and tests must exercise at least three concurrent calls. A task with a budget smaller than the sum of its proposed calls must not start all calls and hope some fail later.

Example:
- Task budget: `0.012 USDC` = `12,000` base units
- Three calls each priced at `0.005 USDC` = `5,000` base units
- Total planned maximum: `0.015 USDC` = `15,000` base units
- Required result: reject or re-plan before authorization; never exceed `12,000` base units.

Budget checks must cover parallel workers, retries, fallbacks, and any seller call created during result recovery.

### 7.4 Budget increase

A model or seller cannot increase the budget. Any budget change must be an explicit user-authorized operation, validated and persisted by the backend before new reservations are accepted.

---

## 8. Replay Protection, Idempotency, and Duplicate Payment

The required behavior is: **one valid payment authorization unlocks at most one paid response, and repeated serial or parallel requests must not create additional paid responses or duplicate transfers.**

### 8.1 Idempotency key

Each logical service call must have a stable, high-entropy idempotency key created by the buyer backend. Store a unique database constraint over the appropriate scope, such as `(buyer_id, idempotency_key)`.

Bind the idempotency record to:
- buyer/task identity,
- service ID,
- canonical request-body hash,
- registry terms version,
- payment authorization/resource identity,
- final state.

If the same key is reused with a different service or request body, reject it as an idempotency conflict. Do not treat it as a new paid call.

### 8.2 Request identity

Canonicalize the relevant request fields using a deterministic encoding, then hash them. The request identity must be stable across retries and must distinguish different service calls. Do not rely on timestamps alone.

### 8.3 Seller-side one-time redemption

The seller must durably record the payment authorization/resource as consumed before releasing the paid result. A unique constraint or atomic compare-and-set must ensure that two parallel requests cannot both redeem the same authorization.

Expected behavior:
- First valid redemption: may proceed once.
- Serial replay: return a safe duplicate/replay response; do not release a second paid result.
- Parallel replay: exactly one request may win the atomic claim.
- Repeated request with a different body/resource: reject.
- Seller restart: replay state remains durable.

An in-memory set is not sufficient for production-style replay tests because it is lost on restart and may race across workers.

### 8.4 Protocol compatibility

Use the official x402 v2 SDK and its documented lifecycle for payment verification and settlement. The idempotency layer complements the protocol; it must not replace or modify x402 v2 semantics. Do not invent headers, payload fields, signing formats, or verification rules. Confirm exactly which authorization/resource fields the chosen SDK exposes and bind replay storage to those supported fields.

---

## 9. Settlement and Delivery Ordering

This section is a critical design decision.

The system requirement is that a seller failure, timeout, or output that violates the seller's own output schema must not settle. Therefore, implement the official SDK's supported payment lifecycle so the seller can validate the request, execute the service, and validate its output before final settlement whenever the selected scheme and SDK permit that ordering.

### 9.1 Required seller flow

1. Receive the request and process x402 v2 payment requirements through the official SDK.
2. Validate request shape, authorization/resource identity, price, and replay state.
3. Execute the seller's operation with bounded timeout and resource limits.
4. Validate the seller's output against the registered output schema.
5. If execution fails, times out, or output fails seller-side schema validation before settlement: do not settle; return an appropriate error through the supported protocol flow and record the failed attempt.
6. If output is valid, complete the official x402 verification/settlement flow as documented by the SDK.
7. Persist the settlement evidence and one-time redemption state safely.
8. Return the paid response only once.
9. The buyer validates the returned output independently against the registry schema.

Do not assume that every x402 SDK supports exactly this order. Confirm the SDK's actual middleware/handler lifecycle before implementing. If the selected flow settles before the seller can validate the output, this requirement is not met and must be addressed explicitly rather than hidden.

### 9.2 Buyer output rejection

The buyer independently validates output against the registered JSON Schema and, where appropriate, checks semantic constraints. If the payment has settled but the buyer rejects the response, record:

- status: `paid_output_rejected`
- settlement transaction hash and verified amount
- seller/service ID
- validation error code and a safe, concise reason
- reputation penalty event
- fallback decision and budget check result

Do not claim the call was “not charged” if a transfer has settled. A fallback call is a new call with its own idempotency key, budget reservation, payment validation, and transaction evidence.

### 9.3 Timeouts and uncertain outcomes

A network timeout does not prove that payment failed. If payment submission or settlement may have happened:
- set the call to `reconciliation_pending`;
- retain the budget reservation;
- query the official facilitator/SDK and chain using available transaction/payment identifiers;
- do not blindly create a new authorization or resend payment;
- only mark `failed_and_not_charged` after confirming no settlement occurred and the protocol lifecycle supports that conclusion.

Use bounded retries for safe read-only operations. Payment submission retries must be governed by the official SDK and idempotency/reconciliation policy, not generic HTTP retry middleware.

---

## 10. Ledger and Audit Requirements

Every attempted paid call must create a durable ledger/audit record, including refusals and failures.

### 10.1 Minimum ledger fields

- `call_id`
- `task_id`
- `buyer_id`
- `seller_id`
- `service_id`
- `attempted_at`
- `completed_at` or last state-change time
- `listed_price_base_units`
- `challenge_amount_base_units`, if received
- `authorized_amount_base_units`, if authorized
- `settled_amount_base_units`, if verified
- `network_id`
- `token_address`
- `pay_to_address`
- `status`
- `refusal_or_failure_code`
- `latency_ms`
- `idempotency_key_hash` (do not expose raw keys unnecessarily)
- `request_hash`
- `payment_attempt_id`
- `transaction_hash`, if available
- `explorer_url`, derived only from a configured trusted network mapping
- `settlement_verified_at`
- `reconciliation_status`

Never fabricate a transaction hash or explorer URL. If no transaction was submitted, leave transaction fields empty. If the outcome is uncertain, show `reconciliation_pending` instead of inventing a final state.

### 10.2 Required externally visible statuses

Use the exact required product statuses:
- `paid`
- `paid_output_rejected`
- `refused`
- `failed_and_not_charged`

Additional internal states may include:
- `planned`
- `budget_reserved`
- `challenge_received`
- `payment_submitted`
- `reconciliation_pending`
- `cancelled_before_payment`

Map internal states to the four required statuses only when the evidence supports that mapping. In particular, do not map a pending/uncertain payment to `failed_and_not_charged`.

### 10.3 Audit events

Record append-only events for:
- challenge received,
- challenge accepted/refused and why,
- budget reserved/released/converted,
- payment authorization created,
- payment submission attempted,
- settlement verified or reconciliation changed,
- seller output schema failure,
- buyer output schema rejection,
- replay/idempotency rejection,
- fallback selected/refused,
- reputation update,
- admin/registry term change.

Avoid storing private keys, full authorization signatures, seed phrases, or unnecessary personal data in audit events. If protocol troubleshooting requires sensitive material, use restricted, short-retention diagnostics with explicit redaction—not the normal ledger.

---

## 11. Reputation and Fallback Policy

Reputation must be computed from recorded calls, not seller-provided claims.

Track at minimum:
- eligible call count,
- successful valid-output count,
- invalid-output count,
- failure count,
- success rate,
- median latency,
- listed price,
- last updated time.

Recommended initial interpretation:
- A `paid` call with valid output contributes to successful calls.
- `paid_output_rejected` counts as a paid but invalid result and lowers output-quality reputation.
- `refused` due to a buyer-side policy mismatch should not automatically count as seller execution failure; record a separate security/mismatch metric.
- `failed_and_not_charged` counts as an execution failure when attributable to the seller.
- Exclude unresolved `reconciliation_pending` calls from final settlement and success metrics until resolved.

### 11.1 Fallback

When a seller's output is rejected:
1. Record the rejection and update the seller-quality metrics.
2. Identify a compatible alternative from the registry.
3. Re-check price, network, token, recipient, scheme, schema compatibility, and reputation.
4. Atomically reserve the fallback call's maximum cost.
5. Verify remaining budget and concurrency.
6. Execute the fallback as a separate call with separate idempotency and settlement evidence.
7. Explain the fallback and added cost to the user.

Do not repeatedly call the same failing seller without a policy-based reason. Limit fallback attempts per task.

---

## 12. Wallet and Secret Management

### 12.1 Wallet separation

- Use a dedicated buyer testnet wallet with only a small test balance.
- Each seller may publish its public receiving address (`payTo`) in registry metadata.
- Public addresses and transaction hashes may be displayed; private keys and seed phrases may not.
- Never reuse a personal wallet for the hackathon prototype.

### 12.2 Secret storage

For local development:
- store secrets in an ignored `.env` file;
- use placeholders in `.env.example`;
- restrict file access where possible.

For deployment:
- use the deployment platform's secret/environment manager;
- do not bake secrets into Docker image layers or frontend bundles;
- separate development and deployed credentials;
- rotate credentials if logs, source control, or a deployment artifact may have exposed them.

### 12.3 Logging and error handling

- Redact authorization signatures, private keys, API keys, seed phrases, database URLs, and credentials.
- Do not log full request/response bodies by default; they may contain sensitive data or prompt injection.
- Log structured error codes and correlation IDs.
- Return safe, concise public errors; retain restricted diagnostics server-side.
- Do not include secrets in exception traces surfaced to the browser.

### 12.4 Repository hygiene

- Commit `.gitignore` and `.env.example`.
- Run a secret scanner before every demo/release.
- Inspect Git history if a secret was committed; deleting the latest file is not sufficient.
- If a key is exposed, rotate it and assume it may have been copied.
- Never ask team members to paste private keys into shared chat or source files.

---

## 13. Network and Application Security

Minimum controls:
- HTTPS for public registry, buyer, seller, and dashboard endpoints.
- Strict CORS allowlist; never use wildcard CORS with credentials.
- Input validation with Pydantic or equivalent.
- Output validation using the schema version associated with the registry service.
- Request body size limits, timeouts, rate limits, and concurrency caps.
- Restrict seller outbound requests to permitted targets; prevent SSRF and arbitrary internal-network access.
- For scraping sellers, use allowlisted sites, honor site policies/robots.txt where applicable, and reject arbitrary user-supplied internal URLs.
- Parameterized SQL; least-privilege database credentials.
- Authentication/authorization for task creation, budget changes, and administrative registry writes.
- Public read-only marketplace metadata can be exposed separately from administrative mutation routes.
- Keep dependencies pinned and review security advisories relevant to the chosen SDK/runtime.
- Do not expose debug mode or stack traces in public deployments.

---

## 14. Registry Integrity and Service Metadata

The registry must be the source of declared terms, not an unrestricted write surface.

For each change to a service's price, endpoint, token, network, scheme, payTo, or schemas:
- authenticate and authorize the writer;
- validate field formats and supported combinations;
- store the previous and new terms;
- increment a version or compute an immutable terms hash;
- record who/what changed it and when;
- ensure in-flight calls remain bound to the terms snapshot used when they began.

Buyer-side checks must still compare every live payment challenge with the snapshot. Registry integrity alone does not remove the need for challenge validation.

---

## 15. Database Invariants

Implement these as database constraints, transactions, and tests—not merely comments.

1. Monetary columns use integer base units and non-negative constraints.
2. A task has one immutable or explicitly versioned budget authorization context.
3. Active budget reservations are unique per logical call.
4. One idempotency key in its defined scope maps to one canonical request.
5. One payment authorization/resource can be redeemed at most once.
6. A verified settlement references a real payment attempt and contains a transaction/payment identifier supported by the SDK.
7. A `paid` record requires verified settlement evidence and a valid response.
8. A `paid_output_rejected` record requires verified settlement evidence and an output rejection event.
9. A `failed_and_not_charged` record requires evidence that settlement did not occur.
10. An unresolved payment must remain pending reconciliation.
11. Budget settlement and reservation release must be transactional and idempotent.
12. A replay rejection must not create another settlement or paid response.
13. Transaction hashes should be unique within the appropriate network scope when they represent distinct transfers.
14. Ledger status changes and budget movements must be auditable.
15. A seller cannot update buyer-owned task budgets or overwrite buyer ledger evidence.

---

## 16. Required Security Test Plan

Run against testnet and local deterministic test doubles. Never use mainnet funds for these tests.

| ID | Test | Expected result |
|---|---|---|
| PAY-01 | Valid seller challenge matches registry | Payment proceeds through official x402 v2 flow |
| PAY-02 | Challenge amount exceeds registry price | Refused before signing/submission |
| PAY-03 | Wrong `payTo` | Refused; no settlement |
| PAY-04 | Wrong network | Refused; no settlement |
| PAY-05 | Wrong token | Refused; no settlement |
| PAY-06 | Unsupported scheme | Refused; no settlement |
| PAY-07 | Expired/invalid requirements | Refused by SDK/policy |
| PAY-08 | Task budget below call price | Refused before authorization |
| PAY-09 | Three or more concurrent calls | Atomic reservations; budget never exceeded |
| PAY-10 | Budget is 0.012 USDC, proposed calls total 0.020 USDC | Reject/re-plan; total authorized/settled spend never exceeds 0.012 USDC |
| PAY-11 | Same idempotency key and same request sent serially | At most one paid response/settlement |
| PAY-12 | Same authorization sent in five parallel requests | Exactly one redemption/paid response; no duplicate transfer |
| PAY-13 | Same idempotency key with different body/service | Conflict/refusal; no second payment |
| PAY-14 | Seller returns 5xx before settlement | `failed_and_not_charged` once non-settlement is confirmed |
| PAY-15 | Seller operation times out before settlement | No settlement; reservation released only after safe confirmation |
| PAY-16 | Seller output fails seller-side schema validation | No settlement |
| PAY-17 | Buyer detects invalid output after settlement | `paid_output_rejected`; settlement retained; reputation lowered |
| PAY-18 | Payment submission times out with unknown outcome | `reconciliation_pending`; no blind retry |
| PAY-19 | Reconciliation confirms settlement | Ledger records verified amount and transaction evidence |
| PAY-20 | Reconciliation confirms no settlement | Safe transition to `failed_and_not_charged`; reservation released |
| PAY-21 | Seller restarts after authorization redemption | Replay remains blocked by durable storage |
| PAY-22 | Private key is scanned in repo/build/log output | Release blocked |
| PAY-23 | LLM asks to exceed budget or ignore mismatch | Deterministic payment gate refuses |
| PAY-24 | Seller output contains prompt injection | Treated as untrusted content; no policy override |
| PAY-25 | Ledger row lacks verified transaction evidence | Must not be represented as settled |
| PAY-26 | Fallback seller is selected | Separate reservation, idempotency key, and settlement evidence |
| PAY-27 | Registry terms change during an in-flight call | Call remains bound to the recorded terms snapshot |
| PAY-28 | Unmodified x402 v2 buyer calls our seller | Interoperability test passes |
| PAY-29 | Our buyer pays an unmodified reference x402 v2 seller | Interoperability test passes |
| PAY-30 | Full ledger reconciled against testnet transfers | Every claimed settlement is supported by evidence |

### 16.1 Release gate

Do not present the system as payment-safe until at minimum:
- PAY-02 through PAY-06 pass;
- PAY-09 through PAY-13 pass;
- PAY-14 through PAY-20 pass;
- PAY-22 passes;
- both x402 v2 interoperability tests pass;
- ledger reconciliation passes;
- no testnet private key or API secret is exposed.

---

## 17. Operational Reconciliation

A background job or administrative action should reconcile calls in `payment_submitted` or `reconciliation_pending`.

For each uncertain call:
1. Retrieve the payment/transaction identifiers available from the SDK and stored attempt.
2. Query the official facilitator and/or public chain using supported interfaces.
3. Validate network, token, recipient, amount, and transaction outcome.
4. Match the observed transfer to the specific call without double-counting.
5. Update settlement and budget state in one database transaction.
6. Append an audit event with evidence references and reconciliation time.
7. If the evidence remains inconclusive, leave the call pending.

Do not mark a payment successful solely because:
- the seller returned HTTP 200;
- the seller claims it was paid;
- the buyer received a signature;
- a transaction hash string exists;
- the database contains a `paid` status.

A transaction hash is evidence to investigate, not by itself proof that the expected transfer succeeded. Verify the transaction status and transfer details using the configured network and token.

---

## 18. User-Facing Safety and Transparency

The dashboard should show:
- listed price and actual verified paid amount;
- service, seller, network, and token;
- status and clear reason for refusal/failure;
- verified transaction hash and explorer link when available;
- latency;
- whether the result passed schema validation;
- whether a fallback was used and the additional cost;
- total task spend and remaining budget.

The buyer's explanation should separate:
- **planned** calls,
- **attempted** calls,
- **authorized** amounts,
- **verified settled** amounts,
- **released** reservations,
- **pending reconciliation** amounts.

Do not present a planned or authorized amount as money already spent. Do not hide a paid-but-rejected response or imply that it was free.

---

## 19. Implementation Ownership and Integration Contract

Suggested owner: **Payment & Security** team member.

Own:
- `backend/payments/`
- x402 v2 SDK integration
- challenge/registry comparison
- deterministic payment authorization policy
- budget reservation and concurrency gate
- replay/idempotency service
- settlement/reconciliation logic
- security tests and secret scanning

Required integration contracts:
- **Registry owner:** provides immutable/versioned service terms snapshots and schema versions.
- **Seller owner:** validates seller output before settlement where supported, implements durable one-time redemption, and returns protocol-compliant errors.
- **Buyer owner:** obtains a call plan but invokes payment only through the payment service; validates output independently.
- **Database/ledger owner:** stores attempts, reservations, settlements, audit events, and status transitions transactionally.
- **Frontend owner:** displays status and evidence but never controls payment authorization.

Do not let separate team members invent competing payment status enums, price units, network identifiers, or x402 headers. Freeze these contracts before parallel implementation.

---

## 20. Implementation Sequence

1. Confirm the current official x402 v2 SDK, supported scheme, facilitator configuration, and Base Sepolia USDC contract.
2. Create test wallets and fund them using an official testnet faucet.
3. Build a single minimal seller and make one real testnet payment.
4. Add challenge-vs-registry validation for price, network, token, recipient, and scheme.
5. Implement integer-unit budget reservations with database transactions.
6. Add durable idempotency and seller-side one-time redemption.
7. Implement settlement evidence persistence and reconciliation.
8. Add seller-side timeout/output validation before settlement wherever the SDK lifecycle supports it.
9. Add buyer output validation and `paid_output_rejected`.
10. Add failure handling, safe fallback, reputation updates, and ledger UI.
11. Pass serial and parallel replay tests.
12. Pass reference buyer/reference seller interoperability tests.
13. Run a secret scan, full regression tests, and testnet ledger reconciliation.
14. Capture a short demo showing successful payment, refused manipulated price, replay rejection, and a seller failure that does not settle.

**Do not begin with the dashboard or LLM sophistication.** First prove a single real, verifiable, safe x402 v2 payment and its failure behavior.

---

## 21. Demo Script for Payment Safety

Suggested 5-minute sequence:

1. **Registry:** show a registered service, price, network, token, recipient, and schema.
2. **Successful call:** submit a task and show one seller call with a verified testnet transaction.
3. **Ledger:** open the transaction hash in the configured explorer and show the matching transfer.
4. **Price manipulation:** make a test seller challenge exceed its registry price; show refusal before signing.
5. **Replay:** submit the same authorization concurrently; show only one redemption and no duplicate settlement.
6. **Failure:** simulate a seller timeout/schema failure before settlement; show no transfer and the correct final status after confirmation.
7. **Output rejection:** if demonstrated, show a separately configured seller whose response is rejected after settlement; label it `paid_output_rejected`, show the actual transaction, and show the reputation penalty.
8. **Budget:** run a task whose planned calls exceed its budget; show that it is rejected or re-planned before authorization.

Never demonstrate security by exposing secrets, using mainnet funds, or fabricating explorer evidence.

---

## 22. Definition of Done

The payment/security implementation is complete for the hackathon only when:

- [ ] Official x402 v2 SDK is used; protocol behavior is not reimplemented ad hoc.
- [ ] Base Sepolia network and test USDC contract are verified against official documentation.
- [ ] Price, token, network, recipient, scheme, expiry, and service identity are checked before payment.
- [ ] Task budgets are enforced with integer base units and atomic reservations.
- [ ] At least three concurrent calls are supported without overspending.
- [ ] Durable idempotency and replay protection survive serial, parallel, and restart tests.
- [ ] Seller failure/timeout/schema failure before settlement does not settle.
- [ ] Uncertain payment outcomes are reconciled before retry or final failure status.
- [ ] Buyer schema rejection after settlement is correctly recorded as `paid_output_rejected`.
- [ ] Ledger entries reconcile to actual testnet transfers.
- [ ] No private keys or API secrets are exposed in Git, frontend assets, logs, or demo materials.
- [ ] Unmodified x402 v2 buyer/seller interoperability tests pass.
- [ ] Security tests and secret scanning pass.

---

## 23. Official References to Verify During Implementation

Use current official documentation for exact SDK APIs and protocol details; this specification deliberately avoids prescribing undocumented header names or signing payloads.

- x402 project documentation and SDKs: https://www.x402.org/
- x402 facilitator reference: https://x402.org/facilitator
- Base Sepolia network documentation: https://docs.base.org/
- Base Sepolia explorer: https://sepolia.basescan.org/
- Circle USDC/testnet documentation and faucet: https://developers.circle.com/

**Verification note:** Package names, SDK method signatures, payment scheme behavior, facilitator capabilities, and the test USDC contract can change. Confirm them from the current official source at implementation time. The security invariants and judge-facing expected behaviors in this document remain the project requirements.
