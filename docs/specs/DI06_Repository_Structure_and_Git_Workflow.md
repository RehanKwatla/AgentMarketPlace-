# DI-06: Pay-per-Call Agent Economy
## Repository Structure & Git Workflow

**Document ID:** DI06-REPO-GIT-001  
**Project:** DI-06 — Pay-per-Call Agent Economy  
**Team size:** 4 members  
**Repository model:** Single Git repository / modular monolith  
**Protocol:** x402 v2  
**Status:** Team implementation baseline

---

## 1. Purpose

This document defines how the four-person team will organize the repository, divide ownership, collaborate through Git, manage shared interfaces, review changes, integrate modules, and keep the project runnable during the 24-hour hackathon.

The objective is to let all four members develop in parallel while preventing common integration problems such as:

- Two members creating incompatible versions of the same API.
- Multiple branches changing the same shared files.
- Payment and seller modules using different assumptions about prices or payment status.
- Broken dependency files caused by independent package changes.
- Secrets accidentally committed to Git.
- Large, late merges that cannot be tested before the demo.
- A `main` branch that no longer starts.

**Core rule:** parallelize implementation, not contracts. Agree on shared schemas, folder ownership, configuration names, and test expectations before members begin independent work.

---

## 2. Repository Strategy

### 2.1 Recommended approach: one repository

Use a single repository for the frontend, backend, database migrations, scripts, tests, and documentation.

Why this is appropriate for the hackathon:

1. Everyone can work from the same source of truth.
2. Shared API and data contracts are easy to review.
3. One pull request can include a complete feature and its tests.
4. A single README can explain how to start the complete application.
5. Cross-module integration can be tested before merging.
6. It avoids the extra coordination required by separate repositories.

Start with a **modular monolith**. Keep clear module boundaries, but do not create separate microservice repositories or deployment infrastructure unless the implementation proves it is necessary. The three seller agents must still be independently addressable and individually registered, even if their code lives in one repository.

### 2.2 Repository name

Recommended:

```text
di06-agent-economy
```

Alternative names are acceptable, but select one canonical repository name and use it consistently in local paths, README instructions, deployment settings, and team communication.

### 2.3 Source of truth

The GitHub repository is the authoritative source for:

- Application code.
- Dependency and lock files.
- API contracts.
- Database migrations.
- Tests.
- Configuration templates.
- Setup and deployment instructions.
- Demo scripts and architecture documentation.

Do not rely on code that exists only on one member's laptop, temporary chat messages, or uncommitted IDE changes.

---

## 3. Recommended Repository Structure

Use the following structure as the initial target. Keep the structure practical: create a file or folder when it has a defined purpose, and avoid empty scaffolding that nobody owns.

```text
di06-agent-economy/
├── README.md
├── .gitignore
├── .env.example
├── docker-compose.yml
│
├── docs/
│   ├── 01_PROJECT_REQUIREMENTS.md
│   ├── 02_SYSTEM_ARCHITECTURE.md
│   ├── 03_SYSTEM_ARCHITECTURE_DIAGRAM.png
│   ├── 04_TECH_STACK_AND_SETUP.md
│   ├── 05_REPOSITORY_AND_GIT_WORKFLOW.md
│   ├── 06_API_CONTRACTS.md
│   ├── 07_DATABASE_SCHEMA.md
│   ├── 08_PAYMENT_SECURITY.md
│   ├── 09_TEST_PLAN.md
│   └── 10_EXECUTION_PLAN.md
│
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/
│   │   ├── registry/
│   │   ├── buyer/
│   │   ├── payments/
│   │   ├── sellers/
│   │   │   ├── data/
│   │   │   ├── scraping/
│   │   │   └── inference/
│   │   ├── ledger/
│   │   ├── reputation/
│   │   ├── database/
│   │   └── schemas/
│   └── tests/
│       ├── unit/
│       ├── integration/
│       ├── payment_safety/
│       └── interoperability/
│
├── frontend/
│   ├── package.json
│   ├── package-lock.json
│   ├── .env.example
│   ├── index.html
│   └── src/
│
├── database/
│   ├── migrations/
│   └── seed/
│
├── scripts/
│   ├── seed_registry.py
│   ├── check_environment.py
│   └── run_demo.py
│
└── .github/
    └── workflows/
        └── checks.yml
```

### 3.1 Folder ownership and purpose

| Path | Purpose | Primary owner |
|---|---|---|
| `README.md` | Project overview, setup, commands, demo instructions | Member 4, reviewed by all |
| `.gitignore` | Exclude secrets, local environments, build output | Member 4 / integration owner |
| `.env.example` | Names and safe placeholders for required configuration | Integration owner; changes coordinated |
| `docs/` | Requirements, architecture, API, database, security, tests | All members by topic |
| `backend/app/main.py` | Application entry point and router registration | Integration owner |
| `backend/app/config.py` | Validated application settings | Member 1 with integration owner |
| `backend/app/registry/` | Service registration and discovery | Member 3 |
| `backend/app/buyer/` | Task planning, service selection, aggregation and fallback | Member 3 |
| `backend/app/payments/` | x402 integration and deterministic payment policy | Member 1 |
| `backend/app/sellers/` | Three seller implementations | Member 2 |
| `backend/app/ledger/` | Durable call/payment records and reconciliation | Member 4 with Member 1 |
| `backend/app/reputation/` | Seller success, latency and price statistics | Member 3 with Member 4 |
| `backend/app/database/` | Database connection/session and shared persistence helpers | Member 4 |
| `backend/app/schemas/` | Shared request, response and event schemas | Shared; changes require coordination |
| `backend/tests/unit/` | Fast tests for individual functions and modules | All owners |
| `backend/tests/integration/` | Multi-module and database integration tests | All owners |
| `backend/tests/payment_safety/` | Budget, price, replay, and settlement-safety tests | Member 1 |
| `backend/tests/interoperability/` | Tests against compatible external x402 v2 clients/sellers | Member 1 with Members 2 and 3 |
| `frontend/` | Marketplace, task form, result view, ledger and reputation UI | Member 4 |
| `database/migrations/` | Version-controlled schema changes | Member 4 |
| `database/seed/` | Repeatable initial registry/demo data | Member 3 with Member 4 |
| `scripts/` | Environment checks, seeding and demo helpers | Relevant owner |
| `.github/workflows/` | Automated checks on pushes and pull requests | Integration owner |

**Ownership does not mean isolation.** Other members may contribute to any module, but the owner coordinates interface changes and reviews changes to that module.

### 3.2 Shared files requiring coordination

The following files affect several components and must not be changed independently without informing the team:

- `README.md`
- `.env.example`
- Dependency and lock files.
- `backend/app/main.py`
- `backend/app/config.py`
- `backend/app/schemas/`
- Database migrations.
- Service registry schema.
- Payment status enums.
- API contract document.
- Docker Compose and deployment configuration.
- Shared test fixtures.

If a change affects a shared file, announce it in the team channel and include it in the relevant pull request.

---

## 4. Four-Member Work Allocation

The team should assign one primary owner to each workstream.

### Member 1 — Payment Engine and Security

**Primary branch:** `feature/payments`

Owns:

- Official x402 v2 SDK integration.
- Buyer-side payment handling.
- Seller-side payment integration coordination.
- Registry price, token, network, and `payTo` checks.
- Budget reservation and release rules.
- Replay protection and idempotency.
- Settlement verification/reconciliation interfaces.
- Payment safety tests.
- Testnet transaction verification.

**Expected deliverables:**

- A minimal paid endpoint working on Base Sepolia.
- Deterministic payment-policy functions.
- Documented payment lifecycle.
- Tests for budget, price, recipient, network, token, replay, and failures.
- Safe handling of uncertain transaction outcomes.

**Must coordinate with:**

- Member 2 for seller middleware and protected output behavior.
- Member 3 for buyer call interfaces and spending requests.
- Member 4 for ledger fields and persisted payment status.

### Member 2 — Seller Agents

**Primary branch:** `feature/sellers`

Owns:

- Data Seller.
- Scraping Seller.
- Inference Seller.
- Seller input/output schemas.
- Per-service metadata.
- Seller errors, timeouts, and response-size limits.
- x402 v2 seller compatibility.
- Invalid-output test fixtures.

**Expected deliverables:**

- Three independently callable seller endpoints.
- One registry-compatible service record per seller.
- Declared and enforced output schemas.
- An unpaid request that returns the expected x402 v2 challenge.
- Successful paid requests through the agreed payment integration.
- Tests for normal output, failure, timeout, and invalid output.

**Must coordinate with:**

- Member 1 on payment middleware, verification and settlement ordering.
- Member 3 on request/response schemas and service capabilities.
- Member 4 on public URLs, health checks and dashboard metadata.

### Member 3 — Buyer Agent and Registry

**Primary branch:** `feature/buyer-registry`

Owns:

- Registry search/filter endpoints.
- Service metadata and service selection.
- Natural-language task planning.
- Budget-aware plan construction.
- Seller reputation-aware ranking.
- Buyer execution orchestration.
- Output-schema validation.
- Result aggregation and fallback logic.

**Expected deliverables:**

- Searchable registry.
- Task submission and status retrieval.
- Buyer that can use Data, Scraping, and Inference services in one task.
- Clear explanation of service choices and total cost.
- Schema validation and fallback based on remaining budget.

**Must coordinate with:**

- Member 1 for the payment client and budget reservation interface.
- Member 2 for service schemas and behavior.
- Member 4 for task/result persistence and frontend data requirements.

### Member 4 — Database, Ledger, Dashboard and Deployment

**Primary branch:** `feature/dashboard-ledger`

Owns:

- Database setup and migrations.
- Ledger data model and read APIs.
- Task history and result persistence coordination.
- Frontend marketplace and task interface.
- Transaction ledger display.
- Reputation dashboard.
- Deployment configuration.
- README, setup instructions and demo runbook.
- Final secret scan coordination.

**Expected deliverables:**

- Reproducible database setup.
- Ledger that reflects actual call and settlement outcomes.
- UI for discovery, task execution, results, ledger and reputation.
- Public URLs for the demo.
- Clean-checkout setup instructions.
- Final demo script and checklist.

**Must coordinate with:**

- Member 1 for transaction and payment status fields.
- Member 2 for seller endpoints and metadata.
- Member 3 for task/result schemas and registry APIs.

### 4.1 Integration owner

Choose one person—preferably the member most comfortable with Git and cross-module debugging—to coordinate:

- Protecting `main`.
- Reviewing shared contract changes.
- Resolving merge conflicts.
- Keeping dependency files consistent.
- Running the integration test suite.
- Tracking blockers and milestone completion.
- Ensuring the deployed build corresponds to a known commit.

The integration owner does not need to write every module. Their responsibility is to maintain a coherent, runnable system.

---

## 5. Branching Strategy

Use a simple feature-branch workflow. Avoid elaborate Git Flow with multiple long-lived release branches during a 24-hour hackathon.

### 5.1 Branch names

```text
main
feature/payments
feature/sellers
feature/buyer-registry
feature/dashboard-ledger
fix/<short-description>
docs/<short-description>
```

Create feature branches from the latest `main`. If a branch is long-lived, regularly bring in changes from `main` so it does not drift too far from the integrated code.

### 5.2 Branch rules

1. `main` must remain runnable.
2. Do not commit directly to `main` except for an agreed emergency fix.
3. Each feature branch should have a clear owner.
4. Keep commits focused and descriptive.
5. Push branches regularly; do not keep hours of work only on a local machine.
6. Merge through a pull request when practical.
7. Review at least the shared interfaces and security-sensitive changes.
8. Run relevant tests before merging.
9. Merge early enough to leave time for end-to-end testing.
10. Never commit secrets, wallet exports, `.env` files, or local database dumps.

### 5.3 Example: create a feature branch

```bash
git switch main
git pull origin main
git switch -c feature/payments
```

Push the branch:

```bash
git push -u origin feature/payments
```

### 5.4 Example: synchronize with main

Before integrating:

```bash
git fetch origin
git switch feature/payments
git merge origin/main
```

Resolve conflicts carefully, run tests, then push:

```bash
git add <resolved-files>
git commit -m "Merge main into payment feature"
git push
```

Use either merge or rebase consistently according to the team's agreed workflow. For a time-constrained team, merging `main` into a shared feature branch is often easier to coordinate than rewriting shared branch history.

### 5.5 Avoid force-pushing shared branches

Do not force-push a branch another member is using. If history rewriting is necessary, coordinate explicitly first.

---

## 6. Commit Message Convention

Use short, descriptive commit messages. A lightweight convention is enough:

```text
feat(payments): add x402 buyer integration
feat(sellers): add data seller endpoint
feat(registry): add category and price filters
feat(buyer): validate seller output schemas
feat(ledger): persist payment outcomes
fix(payments): reject recipient mismatch
fix(buyer): reserve budget before parallel calls
test(payments): add replay protection cases
docs(setup): document Base Sepolia configuration
chore(deps): pin backend dependencies
```

Suggested prefixes:

| Prefix | Use |
|---|---|
| `feat` | New functionality |
| `fix` | Bug fix |
| `test` | Tests |
| `docs` | Documentation |
| `refactor` | Code restructuring without intended behavior change |
| `chore` | Tooling, dependencies, or maintenance |

Commit only related changes together. Avoid messages such as `update`, `final`, `changes`, or `all code`.

---

## 7. Pull Request and Merge Checklist

Before merging a feature branch, verify the relevant items.

### 7.1 General checklist

- [ ] The change has a clear purpose.
- [ ] It follows the agreed API and data contracts.
- [ ] No secrets or private keys are included.
- [ ] No unrelated generated files or local data are included.
- [ ] Relevant tests pass.
- [ ] Error handling is included.
- [ ] Documentation is updated if setup, endpoints, configuration or behavior changed.
- [ ] The change does not break the existing local startup workflow.
- [ ] The owner has reviewed the final diff.

### 7.2 Payment/security changes

For changes to payment-related code, also verify:

- [ ] Registry price is checked before authorization.
- [ ] Network, token and `payTo` are checked against trusted configuration.
- [ ] Budget reservation is atomic and concurrency-safe.
- [ ] Replay protection is durable and correctly scoped.
- [ ] Uncertain settlement is reconciled before retrying.
- [ ] Seller failure behavior matches the payment lifecycle.
- [ ] No payment is marked `paid` without appropriate settlement evidence.
- [ ] Tests cover the changed safety property.

### 7.3 Database changes

- [ ] A migration is included.
- [ ] The migration works on a clean database.
- [ ] The change preserves required ledger fields.
- [ ] Concurrent budget reservations remain safe.
- [ ] Seed data does not contain fake settlement evidence.
- [ ] Existing data is not destroyed without an explicit reason.

---

## 8. Shared API and Schema Contract Workflow

API/schema drift is one of the largest risks when four members work in parallel.

### 8.1 Freeze the first contract

Before independent implementation begins, agree on:

- Registry service fields.
- Task request and response fields.
- Seller input/output schema format.
- Payment attempt and ledger fields.
- Status names.
- Error response shape.
- IDs and timestamp conventions.
- USDC amount representation.
- Service endpoint URL format.
- Health endpoint behavior.

Keep the agreed definitions in `docs/06_API_CONTRACTS.md` and shared schema code.

### 8.2 Use one source for shared types

Where practical, define Pydantic models in a shared backend module and use FastAPI's OpenAPI output to support frontend integration. Avoid duplicating slightly different versions of the same contract in several files.

The frontend can define TypeScript types based on the agreed API contract. If automatic type generation is used, document the command and keep generated files consistent.

### 8.3 Contract-change procedure

If a member needs to change a shared field:

1. Explain the problem and proposed change.
2. Identify affected modules and tests.
3. Update the API contract document.
4. Coordinate with all affected owners.
5. Make the schema change in a dedicated commit or pull request.
6. Update callers and tests.
7. Run integration tests before merging.

Do not silently rename a field in one module and expect all other modules to adapt automatically.

### 8.4 Example service contract

```json
{
  "service_id": "data-001",
  "name": "Example Data Service",
  "category": "data",
  "endpoint_url": "https://example.com/services/data-001",
  "price_usdc": "0.002000",
  "network": "eip155:84532",
  "pay_to": "0x...",
  "input_schema": {},
  "output_schema": {},
  "description": "Returns structured data."
}
```

This is an example shape only. The final contract must be the one agreed by the team and must match the actual seller's payment configuration. The `pay_to` value above is a placeholder.

### 8.5 Amount and status consistency

- Use integer base units internally for payment arithmetic.
- Use one documented external representation for USDC values, preferably a decimal string.
- Use the exact same status values across backend, database and frontend.
- Do not label a request `failed_and_not_charged` when settlement is uncertain.
- If settlement succeeds but output validation fails, represent that outcome as a paid-but-rejected result (for example, `paid_output_rejected`).

---

## 9. Dependency Management

### 9.1 Python dependencies

Select one primary dependency-management method, such as `pyproject.toml` with a lockfile or a pinned requirements file. Do not maintain multiple independent dependency lists.

Rules:

1. Install dependencies in a virtual environment.
2. Pin versions after verifying the working x402 v2 integration.
3. Coordinate changes to FastAPI, Pydantic, the database layer, and x402 packages.
4. Update the lockfile whenever dependencies change.
5. Run tests after dependency changes.
6. Record any required Python runtime version.

### 9.2 Node dependencies

- Keep `frontend/package.json` and `frontend/package-lock.json` in Git.
- Use `npm ci` for repeatable installs after the lockfile is established.
- Do not commit `node_modules/`.
- Coordinate changes to React, Vite, Tailwind, and any Node-based x402 SDK integration.

### 9.3 Avoid dependency collisions

If an x402 integration requires a runtime or SDK that differs from the main backend runtime, isolate it behind a documented adapter instead of forcing incompatible libraries into the same environment.

Do not add a second framework or runtime just because it is familiar. Add it only when a specific protocol or implementation requirement justifies it and the team agrees on the interface.

---

## 10. Secrets and Repository Hygiene

### 10.1 Files that must not be committed

At minimum, ignore:

```gitignore
# Environment and secrets
.env
.env.*
!.env.example
!.env.local.example
*.pem
*.key
wallet.json
secrets/
credentials/

# Python
.venv/
venv/
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/

# Node
node_modules/
dist/
.vite/

# Local databases and logs
*.sqlite
*.db
*.log
logs/
tmp/

# Editor and OS
.vscode/
.idea/
.DS_Store
Thumbs.db
```

Review these patterns to ensure they do not exclude required source files. Adjust the environment-file patterns if the project uses additional non-secret example files.

### 10.2 If a secret is committed accidentally

1. Stop using the exposed key immediately.
2. Rotate or replace the affected testnet credential.
3. Remove it from the current code and configuration.
4. Check the repository history and deployment logs for exposure.
5. Notify the integration owner.
6. Run a secret scan before continuing.

Deleting the file in a later commit does not remove the secret from Git history or existing clones.

### 10.3 Secret scanning

Before the final submission:

- Run the repository's available secret-scanning tool.
- Search tracked files for likely private-key patterns and `.env` files.
- Review Git status and the complete diff.
- Confirm the frontend bundle contains no private keys.
- Confirm logs and screenshots do not reveal credentials.

Do not paste real secrets into automated scanners, external websites, issue trackers, or chat messages unless the tool is explicitly approved for that purpose.

---

## 11. Local Development and Integration Workflow

### 11.1 Initial setup for every member

Each member should be able to:

1. Clone the repository.
2. Read `README.md` and this document.
3. Create their local environment.
4. Install locked backend/frontend dependencies as applicable.
5. Create local environment files from the examples.
6. Start PostgreSQL or the agreed database service.
7. Apply migrations and seed the registry.
8. Start the backend and frontend.
9. Call the health endpoint.
10. Run the relevant tests.

### 11.2 Daily/continuous workflow during the hackathon

At the beginning of a work session:

```bash
git switch main
git pull origin main
git switch <your-feature-branch>
git merge origin/main
```

Before committing:

```bash
git status
git diff
```

After committing:

```bash
git push
```

Before opening a pull request:

- Run tests for the module.
- Check the diff for secrets and unrelated files.
- Update docs/contracts if needed.
- Tell affected members about interface changes.

At regular intervals, the integration owner should merge working branches, run the combined application, and report blockers.

### 11.3 Integration cadence

Do not wait until all four members say they are finished.

Suggested checkpoints:

- **Checkpoint A:** Repository, startup commands, shared schemas and database are in place.
- **Checkpoint B:** One real paid x402 v2 call works.
- **Checkpoint C:** Three seller endpoints are integrated.
- **Checkpoint D:** Buyer executes a task using all three categories.
- **Checkpoint E:** Budget, price and replay safety tests pass.
- **Checkpoint F:** Ledger, reputation and frontend work end to end.
- **Checkpoint G:** Public deployment and final demonstration are verified.

At each checkpoint, identify the next blocking dependency and assign one person to resolve it.

---

## 12. Testing and Continuous Integration

Automated checks are valuable even in a short hackathon because they catch breakage immediately after integration.

### 12.1 Minimum checks on pull requests

Run the checks the repository actually supports:

- Python syntax/import checks.
- Backend unit tests.
- API/schema tests.
- Frontend production build.
- Database migration checks, where feasible.
- Secret scan.
- Payment-safety tests on a controlled test setup.

Do not put real private keys or funded wallet secrets into public CI. Unit tests should use mocks or controlled fixtures; a separate, explicitly configured integration run should exercise the real testnet payment path.

### 12.2 Example CI workflow outline

The exact commands must match the final dependency setup.

```yaml
name: Checks

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: python -m pip install --upgrade pip
      - run: |
          cd backend
          # Replace with the repository's chosen, locked install command.
          python -m pip install -e ".[dev]"
          pytest

  frontend-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: cd frontend && npm ci
      - run: cd frontend && npm run build
```

This is a starting template, not a guaranteed drop-in workflow. Before enabling it, confirm the Python project metadata, runtime versions, lockfiles, test commands, and action versions. Do not expose secrets to untrusted pull requests.

---

## 13. Merge Conflict Handling

Conflicts are normal when members edit shared files.

### 13.1 Prevention

- Keep ownership boundaries clear.
- Agree on shared contracts early.
- Avoid editing the same shared file from multiple branches when possible.
- Commit small changes.
- Communicate before changing configuration or schema files.
- Integrate branches frequently.

### 13.2 Resolution procedure

1. Fetch the latest remote changes.
2. Merge the relevant branch into your feature branch.
3. Inspect each conflicted file.
4. Preserve the intended behavior from both changes where appropriate.
5. Ask the file owner if the correct resolution is unclear.
6. Run unit and integration tests.
7. Commit the resolution and push the branch.
8. Re-run the combined application after the merge.

Never resolve a payment or database conflict by simply accepting one side without understanding the behavior being removed.

---

## 14. Definition of Done

A feature is not complete just because the code has been written.

### 14.1 General definition of done

A feature is complete when:

- [ ] It implements an agreed requirement.
- [ ] It follows the shared contract.
- [ ] It handles expected failure cases.
- [ ] It has relevant tests.
- [ ] It does not introduce secrets.
- [ ] It is documented where necessary.
- [ ] It is committed and pushed.
- [ ] It has been integrated with dependent modules.
- [ ] The integrated application still starts.

### 14.2 Payment feature definition of done

- [ ] Correct x402 v2 lifecycle is implemented through the selected official integration.
- [ ] A valid testnet payment has been exercised.
- [ ] The service price is checked against the trusted registry.
- [ ] Network, token, and recipient are checked.
- [ ] Budget reservation is safe under concurrency.
- [ ] Replay attempts cannot unlock multiple paid responses.
- [ ] Failure/timeout outcomes are handled without falsely claiming a payment did or did not occur.
- [ ] Transaction evidence is recorded and reconciled.
- [ ] Interoperability tests are documented.

### 14.3 Seller feature definition of done

- [ ] Service is independently addressable.
- [ ] Registry record matches its actual endpoint and payment configuration.
- [ ] Input and output schemas are documented and enforced.
- [ ] Unpaid requests follow the x402 v2 challenge flow.
- [ ] Valid paid requests work.
- [ ] Error and timeout cases are tested.
- [ ] The output can be validated by the buyer.

### 14.4 Frontend/ledger feature definition of done

- [ ] UI uses the agreed API contract.
- [ ] Loading, empty, success and error states are handled.
- [ ] Payment status and transaction hash are displayed accurately.
- [ ] Explorer links point to the correct network.
- [ ] No secrets are present in browser code.
- [ ] Production build succeeds.

---

## 15. Demo and Release Branching

Keep release handling simple.

1. Stabilize `main` as the demo candidate.
2. Tag or record the commit used for the final deployment.
3. Avoid merging untested features after the final full acceptance run.
4. If a critical bug appears, create a small fix branch, test it, merge it, and redeploy.
5. Record the deployed frontend/backend URLs and the commit hash.
6. Preserve real testnet transaction hashes for the demonstration.
7. Make sure the demo still works if optional LLM features or nonessential external sources fail.

Do not create a release branch unless there is a clear operational reason. A known, tested commit is more important than elaborate branching.

---

## 16. Integration Risks and Mitigations

| Risk | Why it matters | Mitigation |
|---|---|---|
| API schema drift | Buyer, sellers and UI fail to integrate | Freeze and version shared contracts |
| Multiple edits to `main.py` | Router/startup conflicts | Assign one owner and use router modules |
| Dependency conflicts | Local environments differ | Pin versions and commit lockfiles |
| Payment assumptions differ | Incorrect status or unsafe settlement | Document lifecycle and share payment tests |
| Budget races | Parallel calls overspend | Atomic database-backed reservations |
| Replay race | One authorization may be reused | Durable idempotency and atomic claim/consume logic |
| Fake ledger success | Dashboard misrepresents payment | Reconcile against transaction evidence |
| Secrets committed | Wallet compromise and failed security checks | `.gitignore`, secret scanning and rotation procedure |
| Late integration | No time to debug | Integrate at each checkpoint |
| Unreachable seller URLs | Judges cannot call services | Publish HTTPS endpoints and test externally |
| One member becomes a bottleneck | Other modules wait | Freeze contracts and provide mocks/fixtures early |
| Overengineering | Core requirements remain incomplete | Finish mandatory requirements before stretch goals |

---

## 17. Final Repository Readiness Checklist

### Repository
- [ ] One canonical GitHub repository exists.
- [ ] `main` is protected by team convention and remains runnable.
- [ ] Folder ownership is clear.
- [ ] README has working setup instructions.
- [ ] `.gitignore` excludes secrets and local build artifacts.
- [ ] `.env.example` contains placeholders only.
- [ ] Backend and frontend lockfiles are committed.
- [ ] Database migrations and seed instructions are documented.

### Collaboration
- [ ] Each member has a named workstream and feature branch.
- [ ] Integration owner is identified.
- [ ] API contracts are agreed and committed.
- [ ] Shared-file changes are communicated.
- [ ] Commit message convention is understood.
- [ ] Pull-request/test expectations are agreed.

### Technical integration
- [ ] Backend and frontend run from a clean checkout.
- [ ] Database can be created from migrations.
- [ ] All three sellers are represented in the registry.
- [ ] Payment status vocabulary is consistent.
- [ ] Payment and ledger interfaces are agreed.
- [ ] Automated checks run on pull requests or are available as documented commands.

### Security and demo
- [ ] No private keys or real `.env` files are tracked.
- [ ] Secret scan passes.
- [ ] A real testnet paid call has been verified.
- [ ] Budget, price, recipient, token, network and replay tests are assigned.
- [ ] Public endpoints and deployment ownership are assigned.
- [ ] Final demo commit and transaction evidence will be recorded.

---

## 18. First 60-Minute Team Kickoff

Use this checklist to get the repository ready without spending too long on process.

### First 10 minutes — Create the repository
- Create `di06-agent-economy`.
- Add `.gitignore`, README, and `docs/`.
- Add the current architecture and environment setup documents.
- Invite all four members.

### Next 15 minutes — Freeze shared contracts
- Agree on service metadata.
- Agree on task and seller request/response formats.
- Agree on ledger statuses.
- Agree on internal USDC amount representation.
- Record these decisions in `docs/06_API_CONTRACTS.md`.

### Next 10 minutes — Assign ownership
- Member 1: payments/security.
- Member 2: sellers.
- Member 3: buyer/registry.
- Member 4: database/ledger/UI/deployment.
- Choose the integration owner.

### Next 15 minutes — Establish local startup
- Create backend and frontend skeletons.
- Add environment templates.
- Confirm backend health endpoint.
- Confirm frontend can call backend.
- Confirm database connection and migration approach.

### Final 10 minutes — Set the first milestone
Assign the payment owner to establish the first real testnet paid call, while the other members prepare their modules against the frozen contracts and agreed test fixtures.

---

## Final Rule

**Keep `main` runnable, keep contracts stable, keep secrets out of Git, and integrate continuously.** A simple repository with clear ownership and one verified x402 v2 payment path is more valuable than a sophisticated branching model or a large number of unfinished modules.
