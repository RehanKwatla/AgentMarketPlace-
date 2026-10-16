# TEAM WORKFLOW & PARALLEL INTEGRATION GUIDE (DI-06)

## 1. Team Roster & Ownership Matrix

| Member | Role | Branch | Directory Ownership | Core Responsibilities |
|---|---|---|---|---|
| **Member 1** | Payment & Security Engineer | `feature/payments` | `backend/payments/` | Official x402 v2 integration, buyer/seller payment interfaces, network/token/price/payTo verification, atomic budget reservation, replay protection, idempotency, settlement verification. |
| **Member 2** | Seller Agents Engineer | `feature/sellers` | `backend/sellers/` | Data seller, Scraping seller, Inference seller, input & output schema validation, business logic, endpoints, x402 v2 challenge response. |
| **Member 3** | Buyer & Marketplace Engineer | `feature/buyer-registry` | `backend/buyer/`<br>`backend/registry/` | Service catalog API, filtering, task planner decomposition, service selection, reputation-aware routing, budget enforcement, aggregation, cost explanations. |
| **Member 4** | Ledger, Dashboard & Deployment Engineer | `feature/dashboard-ledger` | `backend/ledger/`<br>`backend/database/`<br>`frontend/` | Persistent database models, ledger audit log, settlement reconciliation, reputation calculations, React/Vite dashboard, deployment configs. |
| **Setup Lead** | System Architect & Repository Admin | `main` | `backend/shared/`<br>`backend/main.py`<br>`docs/API_CONTRACTS.md`<br>Root configs | Shared schemas, configs, central router mounting, merge coordination, test suite maintenance. |

---

## 2. Git Branch Strategy & Workflows

### Branch Structure:
- `main` — Always stable and runnable. All automated tests must pass before merging.
- `feature/payments` — Owned by Member 1.
- `feature/sellers` — Owned by Member 2.
- `feature/buyer-registry` — Owned by Member 3.
- `feature/dashboard-ledger` — Owned by Member 4.

### Daily Developer Workflow:

```bash
# 1. Clone repository to your independent local machine/workspace
git clone <REMOTE_URL>
cd AgentMarketPlace

# 2. Check out your assigned feature branch
git checkout feature/payments   # (or feature/sellers, etc.)

# 3. Pull latest changes from main before starting any work
git fetch origin
git merge origin/main

# 4. Make atomic changes within your assigned directory
# (Remember: Never touch files outside your owned directory without approval)

# 5. Run tests locally
pytest backend/tests/

# 6. Commit and push your changes
git add backend/payments/
git commit -m "feat(payments): implement atomic budget reservation logic"
git push origin feature/payments

# 7. Create Pull Request into 'main'
```

---

## 3. Shared File Change Process

If your feature requires an addition to `backend/shared/schemas.py`, `backend/shared/config.py`, or `docs/API_CONTRACTS.md`:
1. **Do not edit shared files directly on your feature branch without coordination.**
2. Propose the schema addition in the team chat or open a PR specifically tagged `[SHARED-CHANGE]`.
3. The Setup Lead reviews and merges the schema change into `main`.
4. All team members pull `main` into their feature branches:
   ```bash
   git fetch origin
   git merge origin/main
   ```

---

## 4. Local Execution Commands

### Quickstart Backend:
```bash
# Set up virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Run backend development server
python scripts/start_dev.py --backend-only
# Or via uvicorn directly:
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Quickstart Frontend:
```bash
cd frontend
npm install
npm run dev
# Dashboard available at http://localhost:5173
```

### Run Tests:
```bash
# Run entire test suite
python scripts/run_tests.py
# Or directly via pytest:
pytest backend/tests/ -v
```

---

## 5. Reporting Blockers & Integration Protocol

- **Integration Milestones:**
  - **T+4 Hours:** Shared schemas & registry operational.
  - **T+8 Hours:** Sellers live with x402 402 challenge headers.
  - **T+14 Hours:** Buyer agent successfully executes end-to-end paid workflow on Base Sepolia.
  - **T+18 Hours:** Ledger & Dashboard visualizer wired up.
  - **T+22 Hours:** Freeze code, run full integration test report, record demo.
- **Reporting Blockers:** Post immediate blocker in team channel with:
  1. Offending endpoint or interface signature.
  2. Expected vs. Actual JSON response.
  3. Git commit SHA and branch name.
