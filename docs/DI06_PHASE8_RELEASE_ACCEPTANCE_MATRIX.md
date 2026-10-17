# DI-06 — Global Phase 8 Release Acceptance Matrix & Gate Evaluation

**Project:** AgentMarketplace — DI-06: Pay-Per-Call Agent Economy
**Target Branch:** `M1`
**Current Baseline HEAD:** `045e7fe9d9c75645f10534b4cd3bc84b2bb3155e`
**Document Status:** Pre-Release Acceptance Baseline (Post-Audit Correction)
**Audit Timestamp:** 2026-10-17T06:49:00+05:30

---

## 1. Executive Summary & Production Readiness Caveat

> [!CAUTION]
> **CRITICAL PRODUCTION READINESS CAVEAT:**
> Passing 308/308 local automated tests and executing a clean frontend production build **does NOT prove deployed production readiness, cloud PostgreSQL runtime stability, live facilitator compatibility, or on-chain settlement finality**.
>
> Under the repository binding Code of Conduct ([`AGENTS.md`](file:///c:/Users/ASUS/Desktop/AgentMarketPlace/AGENTS.md)) and Zero-Fabrication rules:
> - Unit tests and TestClient fixtures only prove local software correctness under isolated or mocked conditions.
> - No external release gate (Gate D, Sub-Gates D.2 through D.7) may be claimed as passed until empirical evidence is gathered directly from live deployed infrastructure and external blockchain networks.
> - Global Phase 8 remains strictly **PENDING EXTERNAL ACCEPTANCE** until live deployment verification is completed.

This matrix derives verbatim from the two canonical release gate specifications:
1. **Master Plan Team Acceptance Checklist:** [`docs/specs/DI06_TEAM_OF_4_IMPLEMENTATION_MASTER_PLAN.md`](file:///c:/Users/ASUS/Desktop/AgentMarketPlace/docs/specs/DI06_TEAM_OF_4_IMPLEMENTATION_MASTER_PLAN.md), Section 7 (CHK-01 through CHK-13).
2. **Payment Security Release Gate Criteria:** [`docs/specs/DI06_Payment_and_Security_Specification.md`](file:///c:/Users/ASUS/Desktop/AgentMarketPlace/docs/specs/DI06_Payment_and_Security_Specification.md), Section 16.1 (PAY-02..06, PAY-09..13, PAY-14..20, PAY-22, PAY-28..30).

Every criterion is evaluated across five mandatory evidentiary dimensions:
1. **Local Implementation Status:** Whether code exists in the repository.
2. **Local Automated-Test Evidence:** Empirical test proof in the local 308-test suite.
3. **Deployed Verification Status:** Current state on live deployed Vercel/Render infrastructure.
4. **Final Acceptance Status:** Canonical release gate status.
5. **Outstanding Action and Responsible Party:** Exact steps and owners required for final closure.

---

## 2. Master Plan Team Acceptance Checklist Matrix (Section 7)

| # | Exact Requirement Text | Source Section | Local Implementation Status | Local Automated-Test Evidence | Deployed Verification Status | Final Acceptance Status | Outstanding Action & Responsible Party |
| :---: | :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| **CHK-01** | **Three distinct seller categories are searchable through HTTP and UI.** | Master Plan §7.1 | Implemented in `backend/registry/routes.py` and `frontend/src/components/ServiceCard.tsx`. | Passing: `test_registry.py` and `test_api.py`. | Outstanding (Pending live deployment). | **PROVISIONALLY VERIFIED** | Verify `GET /api/v1/services?category=...` on live Render URL and UI catalog cards on Vercel (Operator / DevOps). |
| **CHK-02** | **Buyer accepts natural-language task and budget.** | Master Plan §7.2 | Implemented in `backend/buyer/service.py` (`POST /api/v1/buyer/tasks`). | Passing: `test_buyer_service.py` and `test_api.py`. | Outstanding (Pending live deployment). | **PROVISIONALLY VERIFIED** | Verify live task submission and budget allocation on deployed Render instance (Operator / DevOps). |
| **CHK-03** | **Demo workflow uses Data + Scraping + Inference.** | Master Plan §7.3 | Implemented in `backend/payments/service.py` multi-hop coordinator and `scripts/run_demo.py`. | Passing: `test_phase4_orchestration_ledger.py`. | Outstanding (Pending live deployment). | **PROVISIONALLY VERIFIED** | Execute multi-hop workflow across all 3 services via deployed Vercel dashboard console (Operator / Lead Integrator). |
| **CHK-04** | **At least three paid calls can settle with individual verified transaction evidence.** | Master Plan §7.4 | Implemented in `backend/payments/settlement.py` (`ERC20TransferLogVerifier`). | Passing in mock mode: `test_payment_engine.py`. | **Gated / Unverified** (Zero live blockchain transactions broadcast). | **GATED (PENDING TESTNET BROADCAST)** | Requires operator-supplied funded Base Sepolia wallet, authorization, and 3 distinct on-chain tx receipts with matching USDC Transfer logs (Operator / Blockchain Lead). |
| **CHK-05** | **Ledger records every attempt, price, amount, status, latency and transaction link.** | Master Plan §7.5 | Implemented in `backend/ledger/models.py` and `backend/database/models.py`. | Passing: `test_m4_persistence_sync_concurrency.py`. | Outstanding (Pending live deployment). | **PROVISIONALLY VERIFIED** | Verify live paginated `GET /api/v1/ledger` response on Render PostgreSQL containing all 14 audit fields (Operator / DevOps). |
| **CHK-06** | **Budget never exceeds limit under concurrency.** | Master Plan §7.6 | Implemented in `backend/payments/budget.py` and `DurablePaymentRepository.atomic_reserve`. | Passing locally: `test_concurrent_budget_reservations_atomic` (10 parallel threads, 0 overdraw). | **Outstanding** (Not verified against live multi-connection Render PostgreSQL). | **PROVISIONALLY VERIFIED (PENDING LIVE POSTGRES)** | Execute concurrency load test against live Render PostgreSQL instance under multi-connection traffic (Lead Integrator). |
| **CHK-07** | **Manipulated price/mismatched terms are refused.** | Master Plan §7.7 | Implemented in `backend/payments/service.py` terms validation logic. | Passing: `test_settlement_verification.py` (PAY-02..06). | Outstanding (Pending live deployment). | **PROVISIONALLY VERIFIED** | Issue external curl request with tampered price to deployed endpoint and verify HTTP 402/400 refusal (Lead Integrator). |
| **CHK-08** | **Replay does not produce extra paid responses/transfers.** | Master Plan §7.8 | Implemented in `backend/payments/idempotency.py` and `AuthorizationNonceGuard`. | Passing locally: `test_concurrent_nonce_reservations_isolation` (8 parallel threads, exactly 1 succeeds). | **Outstanding** (Not verified against live Render PostgreSQL). | **PROVISIONALLY VERIFIED (PENDING LIVE POSTGRES)** | Execute parallel replay attack test against live deployed `/api/v1/payments/multi-hop` backed by PostgreSQL (Lead Integrator). |
| **CHK-09** | **Seller failure and invalid output are represented truthfully.** | Master Plan §7.9 | Implemented in `backend/sellers/common.py` and `backend/payments/service.py`. | Passing: `test_sellers_foundation.py` and `test_phase3_payment_hardening.py`. | Outstanding (Pending live deployment). | **PROVISIONALLY VERIFIED** | Trigger intentional downstream schema violation on live deployment; confirm `paid output rejected` status in ledger (Lead Integrator). |
| **CHK-10** | **Reputation updates from actual outcomes.** | Master Plan §7.10 | Implemented in `backend/ledger/routes.py` dynamic calculation. | Passing: `test_runtime_endpoints_and_isolation.py`. | Outstanding (Pending live deployment). | **PROVISIONALLY VERIFIED** | Query `GET /api/v1/reputation` on deployed backend; verify scores reflect settled attempts (Lead Integrator). |
| **CHK-11** | **Both directions of unmodified x402 v2 interoperability pass.** | Master Plan §7.11 | Implemented in `backend/payments/x402_adapter.py` and `backend/payments/middleware.py`. | Passing: `test_x402_sdk_compatibility.py` (8/8 wire tests pass). | Outstanding (Pending external live reference interoperability). | **PROVISIONALLY VERIFIED (PENDING EXTERNAL INTEROP)** | Exercise live bidirectional HTTP challenge/response exchange against official x402 reference client and seller (Lead Integrator). |
| **CHK-12** | **Public HTTPS URLs are available.** | Master Plan §7.12 | Configuration specified in `render.yaml` and `frontend/vercel.json`. | Statically validated in migration tests. | **Pending** (No public HTTPS endpoints provisioned yet). | **PENDING DEPLOYMENT** | Operator provisions Render web service and Vercel project, recording active HTTPS URLs (Operator / DevOps). |
| **CHK-13** | **Secret scan passes; README has setup and one-command startup.** | Master Plan §7.13 | Implemented: `.gitignore` blocks secrets/DBs, `.env.example` clean, `README.md` and `scripts/start_dev.py` document startup. | Passing: `test_frontend_built_bundle_no_secrets_leakage`, secret scan, and documentation audit. | Outstanding (Pending public GitHub repository scan). | **PROVISIONALLY VERIFIED (PENDING REPO SCAN)** | Push reviewed files to GitHub and confirm repository secret scan passes and fresh clone starts with one command (Operator / DevOps). |

---

## 3. Payment Security Release Gate Criteria Matrix (Section 16.1)

| Requirement ID | Specification Description | Source Section | Local Implementation Status | Local Automated-Test Evidence | Deployed Verification Status | Final Acceptance Status | Outstanding Action & Responsible Party |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| **PAY-02** | Challenge amount exceeds registry price -> Refused before signing/submission. | Payment Spec §16 | Implemented in `backend/payments/service.py`. | Passing: `test_payment_policy.py`, `test_phase3_payment_hardening.py`. | Outstanding (Pending live deployment). | **PASSED (LOCAL)** | Verify HTTP 400 refusal on live Render endpoint (Lead Integrator). |
| **PAY-03** | Wrong `payTo` address -> Refused; no settlement. | Payment Spec §16 | Implemented in `backend/payments/service.py`. | Passing: `test_full_settlement_rejection_on_wrong_recipient`. | Outstanding (Pending live deployment). | **PASSED (LOCAL)** | Verify recipient mismatch rejection on live deployment (Lead Integrator). |
| **PAY-04** | Wrong blockchain network -> Refused; no settlement. | Payment Spec §16 | Implemented in `backend/payments/service.py`. | Passing: `test_full_settlement_rejection_on_wrong_network`. | Outstanding (Pending live deployment). | **PASSED (LOCAL)** | Verify network ID enforcement on live deployment (Lead Integrator). |
| **PAY-05** | Wrong token contract -> Refused; no settlement. | Payment Spec §16 | Implemented in `backend/payments/service.py`. | Passing: `test_full_settlement_rejection_on_wrong_token_contract`. | Outstanding (Pending live deployment). | **PASSED (LOCAL)** | Verify contract address verification on live deployment (Lead Integrator). |
| **PAY-06** | Unsupported payment scheme -> Refused; no settlement. | Payment Spec §16 | Implemented in `backend/payments/settlement.py`. | Passing: `test_payment_engine.py`. | Outstanding (Pending live deployment). | **PASSED (LOCAL)** | Verify scheme refusal on live deployment (Lead Integrator). |
| **PAY-09** | 3+ concurrent calls -> Atomic reservations; budget never exceeded. | Payment Spec §16 | Implemented in `backend/payments/budget.py`. | Passing: `test_concurrent_budget_reservations_atomic` (10 threads). | Outstanding (Pending live PostgreSQL test). | **PASSED (LOCAL / PENDING POSTGRES)** | Verify advisory locks under load on live Render PostgreSQL (Lead Integrator). |
| **PAY-10** | Budget 0.012 USDC, proposed calls 0.020 USDC -> Refusal/re-plan. | Payment Spec §16 | Implemented in `backend/buyer/service.py` & payments coordinator. | Passing: `test_budget_cap_enforcement_multi_hop`. | Outstanding (Pending live deployment). | **PASSED (LOCAL)** | Verify budget cap refusal on live deployment (Lead Integrator). |
| **PAY-11** | Same idempotency key & same request sent serially -> At most 1 payment. | Payment Spec §16 | Implemented in `backend/payments/idempotency.py`. | Passing: `test_idempotency_serial_replay`. | Outstanding (Pending live deployment). | **PASSED (LOCAL)** | Verify serial replay cache return on live deployment (Lead Integrator). |
| **PAY-12** | Same authorization sent in 5 parallel requests -> Exactly 1 redemption. | Payment Spec §16 | Implemented in `AuthorizationNonceGuard`. | Passing: `test_concurrent_nonce_reservations_isolation` (8 threads). | Outstanding (Pending live PostgreSQL test). | **PASSED (LOCAL / PENDING POSTGRES)** | Verify parallel authorization replay protection on Render PostgreSQL (Lead Integrator). |
| **PAY-13** | Same idempotency key with different body/service -> Conflict refusal. | Payment Spec §16 | Implemented in `backend/payments/idempotency.py`. | Passing: `test_idempotency_payload_mismatch_conflict`. | Outstanding (Pending live deployment). | **PASSED (LOCAL)** | Verify conflict refusal on live deployment (Lead Integrator). |
| **PAY-14** | Seller returns 5xx before settlement -> `failed_and_not_charged`. | Payment Spec §16 | Implemented in seller lifecycle & payments coordinator. | Passing: `test_seller_route_internal_exception_sanitization`. | Outstanding (Pending live deployment). | **PASSED (LOCAL)** | Verify 5xx seller failure maps to `failed and not charged` (Lead Integrator). |
| **PAY-15** | Seller operation times out before settlement -> No settlement. | Payment Spec §16 | Implemented in async timeout handler. | Passing: `test_async_timeout_cancellation_behavior`. | Outstanding (Pending live deployment). | **PASSED (LOCAL)** | Verify timeout releases budget reservation without settlement (Lead Integrator). |
| **PAY-16** | Seller output fails seller-side schema validation -> No settlement. | Payment Spec §16 | Implemented in `backend/sellers/common.py`. | Passing: `test_concrete_sellers_reject_invalid_output`. | Outstanding (Pending live deployment). | **PASSED (LOCAL)** | Verify seller output validation aborts prior to settlement (Lead Integrator). |
| **PAY-17** | Buyer detects invalid output after settlement -> `paid_output_rejected`. | Payment Spec §16 | Implemented in buyer output validator & ledger recorder. | Passing: `test_confirmed_payment_followed_by_invalid_seller_output`. | Outstanding (Pending live deployment). | **PASSED (LOCAL)** | Verify buyer output rejection transitions to `paid output rejected` (Lead Integrator). |
| **PAY-18** | Payment submission times out with unknown outcome -> `reconciliation_pending`. | Payment Spec §16 | Implemented in suspense transition handler. | Passing: `test_payment_service_live_mode_unverified_proof_transitions_to_suspense`. | Outstanding (Pending live deployment). | **PASSED (LOCAL)** | Verify unconfirmed proof transitions attempt to suspense queue (Lead Integrator). |
| **PAY-19** | Reconciliation confirms settlement -> Ledger records verified evidence. | Payment Spec §16 | Implemented in `backend/ledger/reconciliation.py`. | Passing locally: `test_reconcile_pending_attempt`. | **Outstanding** (Requires live facilitator response). | **PROVISIONALLY VERIFIED (PENDING LIVE FACILITATOR)** | Resolve suspense attempt against live facilitator API on deployed backend (Lead Integrator). |
| **PAY-20** | Reconciliation confirms no settlement -> `failed_and_not_charged`. | Payment Spec §16 | Implemented in `backend/ledger/reconciliation.py`. | Passing: `test_reconciliation_safely_releases_reservation`. | Outstanding (Pending live deployment). | **PASSED (LOCAL)** | Verify failed reconciliation safely releases reserved budget (Lead Integrator). |
| **PAY-22** | Zero private keys or credentials exposed in repo/build/logs. | Payment Spec §16 | Implemented: gitignore, sanitized logging, bundle audit. | Passing: bundle secret scan, git diff audit. | Outstanding (Pending hosting env audit). | **PASSED (LOCAL)** | Audit Vercel & Render hosting environment variable configurations (Operator / DevOps). |
| **PAY-28** | Unmodified x402 v2 buyer calls our seller -> Interop passes. | Payment Spec §16 | Implemented in `backend/payments/middleware.py`. | Passing locally: `test_official_payment_requirement_schema_and_wire_roundtrip`. | **Outstanding** (Pending external reference client test). | **PROVISIONALLY VERIFIED (PENDING EXTERNAL INTEROP)** | Execute wire call from unmodified official x402 client against deployed seller (Lead Integrator). |
| **PAY-29** | Our buyer pays unmodified reference x402 v2 seller -> Interop passes. | Payment Spec §16 | Implemented in `backend/payments/x402_adapter.py`. | Passing locally: `test_adapter_handles_official_and_custom_challenge_headers`. | **Outstanding** (Pending external reference seller test). | **PROVISIONALLY VERIFIED (PENDING EXTERNAL INTEROP)** | Execute wire purchase from our buyer agent against external reference seller (Lead Integrator). |
| **PAY-30** | Full ledger reconciled against testnet transfers -> Verified evidence. | Payment Spec §16 | Implemented in `backend/ledger/reconciliation.py` sync logic. | Passing locally: `test_settlement_reconciler_sync_historical_settlements`. | **Outstanding** (Requires live Base Sepolia RPC queries). | **PROVISIONALLY VERIFIED (PENDING LIVE RECONCILIATION)** | Execute live historical reconciliation against Base Sepolia RPC on Render (Lead Integrator / Blockchain Lead). |

---

## 4. Gate D Evidence Tracking Plan

Every Gate D sub-gate is tracked independently with explicit evidentiary requirements:

| Sub-Gate | Target Capability | Evidentiary Standard (Zero Fabrication) | Current Verification Status | Outstanding Blocker / Action |
| :--- | :--- | :--- | :---: | :--- |
| **D.1** | **Local Test, Build & Patch-Format Readiness** | Full pytest regression suite passes (308/308); clean frontend production build (0 errors); clean patch format via `git diff --check` (0 errors). | **PASSED** (Empirically verified locally) | None for D.1. Note: Does not imply clean git status, as working tree intentionally holds 48 reviewed files awaiting operator staging. |
| **D.2** | **Reviewed Remote Publication** | Working tree staged, committed, and pushed to `origin/M1` using [`docs/DI06_PUBLICATION_MANIFEST.md`](file:///c:/Users/ASUS/Desktop/AgentMarketPlace/docs/DI06_PUBLICATION_MANIFEST.md). | **AWAITING OPERATOR** | Operator authorization required to commit and push to remote. |
| **D.3** | **Render PostgreSQL Runtime** | Application connects to managed PostgreSQL; `init_db()` executes non-destructive DDL migrations. | **PENDING PROVISIONING** | Awaiting operator to provision `agent-marketplace-postgres` on Render. |
| **D.4** | **Deployed Backend HTTP** | External curl requests to `https://<api>/health` return 200 OK with `database: "connected"`. | **PENDING DEPLOYMENT** | Awaiting operator to provision `agent-marketplace-api` on Render. |
| **D.5** | **Vercel Frontend & CORS** | Browser loads Vercel dashboard; CORS allows API communication without browser console errors. | **PENDING DEPLOYMENT** | Awaiting operator to deploy `frontend/` on Vercel and configure `VITE_API_BASE_URL`. |
| **D.6** | **Official x402 Facilitator Gateway** | Direct HTTP interaction with `https://facilitator.x402.org` returns valid wire response for real challenge. | **EXTERNAL DEPENDENCY** | Awaiting live gateway response during deployed staging smoke test. |
| **D.7** | **Live Base Sepolia Settlement** | On-chain USDC transfer receipt on Base Sepolia (`84532`) verified with decoded Transfer log matching amount & payTo. | **GATED (ZERO SPEND PROTOCOL)** | Requires operator-supplied testnet private key and explicit broadcast authorization. |

---

## 5. Phase 8 Closure Protocol & Next Actions

1. **Step 1: Operator Authorizes Publication (D.2):** Operator executes the file-by-file staging runbook from [`docs/DI06_PUBLICATION_MANIFEST.md`](file:///c:/Users/ASUS/Desktop/AgentMarketPlace/docs/DI06_PUBLICATION_MANIFEST.md).
2. **Step 2: Cloud Infrastructure Provisioning (D.3, D.4, D.5):** Operator provisions Render PostgreSQL and Vercel frontend following [`docs/VERCEL_RENDER_DEPLOYMENT.md`](file:///c:/Users/ASUS/Desktop/AgentMarketPlace/docs/VERCEL_RENDER_DEPLOYMENT.md).
3. **Step 3: External Staging Verification:** Execute the 10-step verification runbook from outside the application process. Record real HTTPS URLs, database connection confirmation, and CORS responses.
4. **Step 4: Phase 8 Transition:** Upon recording deployed evidence for CHK-01..13 and PAY-02..30, transition Global Phase 8 from **PRE-RELEASE BASELINE** to **FINAL RELEASE COMPLETE**.
