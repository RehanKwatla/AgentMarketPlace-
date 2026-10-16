# DI-06 — Team of Four Implementation Master Plan

**Project:** Pay-per-Call Agent Economy  
**Timebox:** 24-hour hackathon  
**Stack:** FastAPI, official x402 v2 SDK, PostgreSQL, React/Vite/TypeScript/Tailwind, Base Sepolia  
**Objective:** Three paid seller categories, a budget-aware buyer, real testnet settlement, and a truthful ledger/dashboard.

## 1. Work split

| Member | Responsibility | Branch | First milestone |
|---|---|---|---|
| 1 | Payment engine, budget reservations, x402 client, replay and settlement safety | `feature/payments` | One real verified testnet payment |
| 2 | Data, Scraping, Inference sellers and x402 server integration | `feature/sellers` | One paid seller, then all three |
| 3 | Registry, buyer planning/orchestration, validation and explanation | `feature/buyer-registry` | One task calls one paid seller |
| 4 | Database, ledger, reputation, frontend and deployment | `feature/dashboard-ledger` | Ledger displays the first real payment |

## 2. Freeze these shared contracts in the first hour
- service IDs, category enum, paths, input/output schemas
- registry fields: endpoint, price in atomic units, network, pay-to address, schemas, description
- task request and response fields
- stable `call_id` and idempotency key
- canonical status enum
- payment engine function signature
- persistence/repository interfaces
- transaction hash and settlement verification fields
- environment-variable names and safe defaults

Treat `API_CONTRACTS.md` and `DATABASE_SCHEMA.md` as canonical. Avoid duplicate schemas and inconsistent status names.

## 3. Non-negotiable rules
1. Use Base Sepolia only, never mainnet funds.
2. Verify official x402 v2 SDK/API and testnet token configuration before coding.
3. Use integer USDC atomic units for accounting.
4. Reserve budget atomically before concurrent calls; support concurrency >= 3.
5. Payment engine independently validates trusted price, token, network, recipient, scheme, expiry, and request binding.
6. One authorization must not unlock multiple paid responses/transfers.
7. `paid` requires verified settlement evidence; a hash or HTTP 200 alone is insufficient.
8. Keep uncertain outcomes in `pending_reconciliation`.
9. If settlement happened but output is invalid, use `paid_output_rejected`.
10. Never put private keys/API secrets in Git, browser bundles, screenshots, or logs.
11. Public registry, sellers, and dashboard must have HTTPS URLs for judging.
12. Never fake transaction hashes or settlement evidence.

## 4. Suggested repository ownership
```text
backend/app/payments/       # Member 1
backend/app/sellers/        # Member 2
backend/app/buyer/          # Member 3
backend/app/registry/       # Member 3
backend/app/ledger/         # Member 4
backend/app/reputation/     # Member 4
backend/app/db/             # Member 4, with shared repository interfaces
frontend/                    # Member 4
contracts/                   # shared Pydantic/TypeScript types
migrations/
tests/
.env.example
README.md
docker-compose.yml
```
Adapt to the repository already started; do not rebuild the project structure unnecessarily.

## 5. 24-hour schedule

### Hour 0–1: Align
- Create branches and freeze contracts.
- Confirm official x402 SDK and Base Sepolia token details.
- Add `.env.example` with placeholders.
- Each member creates one minimal module and one test.

### Hour 1–4: Thin vertical slice
- Member 1: payment policy and SDK adapter skeleton.
- Member 2: one seller endpoint behind x402.
- Member 3: registry seed and task endpoint calling one seller.
- Member 4: migration and minimal ledger API/table.
- **Checkpoint:** one real low-value testnet payment is visible in the ledger. If not, stop UI polish and debug together.

### Hour 4–8: Complete components
- Member 1: atomic budget reservations, replay protection, settlement verification.
- Member 2: finish Data, Scraping, Inference.
- Member 3: filters, selection, three-category orchestration, output validation.
- Member 4: ledger filters, call details, budget summary, basic dashboard.

### Hour 8–12: Integrate
- Run a happy path using all three sellers.
- Test price mismatch, wrong recipient/network/token, over-budget plan, duplicate calls, seller failure and invalid output.
- Reconcile ledger values against verified Base Sepolia transfers.

### Hour 12–16: Judge readiness
- Test unmodified x402 v2 client -> our seller.
- Test our buyer -> unmodified/reference seller.
- Add fallback/reputation and deploy public HTTPS endpoints.
- Add health/readiness checks.

### Hour 16–20: Harden
- Test concurrency 1, 3, and 5.
- Test same authorization serially and in parallel.
- Test uncertain settlement/reconciliation.
- Run regression tests and secret scan.
- Fix financial/status mismatches before UI polish.

### Hour 20–24: Freeze and rehearse
- Stop large architecture changes.
- Test one-command local startup and deployed smoke tests.
- Rehearse happy path, a refusal case, a failed seller case, and viva answers.
- Prepare architecture diagram and real transaction evidence.

## 6. Integration rhythm
- Stand-up every 60–90 minutes: done, next, blocked.
- Merge small pull requests early; avoid long-lived branches.
- Every PR includes tests and calls out contract changes.
- Tell affected members before changing shared types.
- Keep one integration owner responsible for `main`, release, and demo.
- Do not wait until the final hours to connect components.

## 7. Team acceptance checklist
- [ ] Three distinct seller categories are searchable through HTTP and UI.
- [ ] Buyer accepts natural-language task and budget.
- [ ] Demo workflow uses Data + Scraping + Inference.
- [ ] At least three paid calls can settle with individual verified transaction evidence.
- [ ] Ledger records every attempt, price, amount, status, latency and transaction link.
- [ ] Budget never exceeds limit under concurrency.
- [ ] Manipulated price/mismatched terms are refused.
- [ ] Replay does not produce extra paid responses/transfers.
- [ ] Seller failure and invalid output are represented truthfully.
- [ ] Reputation updates from actual outcomes.
- [ ] Both directions of unmodified x402 v2 interoperability pass.
- [ ] Public HTTPS URLs are available.
- [ ] Secret scan passes; README has setup and one-command startup.

## Final rule
**Member 3 proposes and orchestrates calls. Member 1 authorizes and coordinates payment. Member 2 provides bounded paid services. Member 4 records and displays durable events and verified settlement evidence. No member's component should bypass another's safety boundary.**
