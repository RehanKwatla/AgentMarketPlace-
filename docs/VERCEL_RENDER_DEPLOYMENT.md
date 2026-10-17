# Vercel + Render Production Deployment Guide & Operator Runbook

**Project:** AgentMarketplace — DI-06: Pay-Per-Call Agent Economy
**Architecture:**
- **Frontend:** React + TypeScript (Vite SPA) deployed to **Vercel**
- **Backend:** FastAPI ASGI Application deployed to **Render Web Service**
- **Database:** Managed PostgreSQL deployed to **Render PostgreSQL**
- **Target Branch:** `M1`
- **Testnet Network:** Base Sepolia (`eip155:84532`) | USDC Contract: `0x036CbD53842c5426634e7929541eC2318f3dCF7e`

---

## 1. Overview & Architecture Matrix

```
                      +---------------------------------------+
                      |             Vercel Edge               |
                      |   React / TypeScript Dashboard SPA    |
                      |   Root: frontend/  | Out: dist/       |
                      +-------------------+-------------------+
                                          |
                                          | HTTPS API Requests
                                          | Origin: https://<your-app>.vercel.app
                                          v
                      +---------------------------------------+
                      |          Render Web Service           |
                      |      FastAPI ASGI Engine (Uvicorn)    |
                      |      CORS: Allowlist Vercel Origin    |
                      +-------------------+-------------------+
                                          |
                                          | PostgreSQL (psycopg2)
                                          | SSL Mode: require
                                          v
                      +---------------------------------------+
                      |       Render Managed PostgreSQL       |
                      |    Persistent Storage & Advisory Locks|
                      +---------------------------------------+
```

---

## 2. Operator Step-by-Step Deployment Runbook

### Step 1: Publish Only Reviewed Files After Operator Authorization
*CRITICAL: Do NOT execute git push without explicit operator authorization.*

Do NOT use broad staging commands (such as `git add backend/` or `git add docs/`). Review the itemized publication manifest in [`docs/DI06_PUBLICATION_MANIFEST.md`](file:///c:/Users/ASUS/Desktop/AgentMarketPlace/docs/DI06_PUBLICATION_MANIFEST.md) and execute the strict file-by-file staging commands provided therein.

Pre-publication checklist:
1. Verify no `.env`, credentials, local SQLite databases (`.db`), or `dist/` folders are staged.
2. Run `git diff --cached --check` to ensure zero whitespace/conflict errors.
3. Review staged filenames with `git diff --cached --name-status`.

---

### Step 2: Provision Render PostgreSQL and FastAPI Web Service

#### Operational Modes & Configuration Matrix

| Mode | Intended Use | Buyer Wallet / Private Key | Seller Pay-To Addresses | Facilitator Verification | On-Chain Settlement |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Mode 1: Read-Only Staging** | Health checks, DB schema migration, catalog discovery, UI telemetry. | Non-operational placeholder (`0x000...0`) / No private key (`None`). | Non-operational placeholders (`0x000...1`, `...2`, `...3`). | Disabled. | None. |
| **Mode 2: Mock-Mode Demonstration** | End-to-end multi-hop workflow simulation, ledger records, dynamic reputation. | Mock buyer address / No private key (`None`). | Service catalog addresses. | Internal mock verification. | Mock settlement proof. |
| **Mode 3: Payment-Enabled Testnet** | Real x402 v2 payment lifecycle on Base Sepolia (`eip155:84532`). | **Operator-supplied, funded Base Sepolia wallet address & private key** (via Render secret env vars). | **Operator-supplied, verified seller payout addresses**. | Live facilitator (`https://facilitator.x402.org`). | Real Base Sepolia USDC transfers (`0x036CbD...`). |

> [!WARNING]
> **Placeholder Address Warning:**
> The addresses `0x0000000000000000000000000000000000000000` through `...0003` configured in `render.yaml` are **strictly non-operational placeholders**. They CANNOT receive, sign, or settle real payments. Never attempt real testnet payment settlement with placeholder addresses. Payment-enabled operation requires operator-supplied, verified testnet wallets and separate explicit authorization.

#### Uvicorn Worker Count & Concurrency Architecture

- **Canonical Start Command:** `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- **Intended Worker Count:** Exactly **1 worker** (default).
- **Concurrency Analysis & Architectural Boundaries:**
  - **Single-Worker Operation (Verified):** On Render's 512 MB Free tier, a single Uvicorn process handles concurrent requests asynchronously via Python's `asyncio` event loop. In-memory async locks (`asyncio.Lock` in `BudgetManager`) and in-memory caches (`IdempotencyStore._idempotency_cache`) operate without inter-process cache drift or synchronization overhead.
  - **Multi-Worker Scaling (`--workers N`):** In a multi-worker environment, separate OS processes do NOT share in-memory heap structures. Concurrency safety relies strictly on PostgreSQL row-level and transaction locks (`pg_advisory_xact_lock(hashtext(:task_id))` in `BudgetReservationModel` and `pg_advisory_xact_lock(hashtext(:auth_key))` in `AuthorizationNonceReservationModel`). If multi-worker is run against SQLite or without durable task IDs, inter-process locking cannot be guaranteed. Therefore, 1 worker is the verified canonical deployment configuration.

#### Option A: Automated via Render Blueprint (Recommended)
1. Log in to the [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** -> **Blueprint**.
3. Connect your repository: `AgentMarketPlace`.
4. Select branch: `M1`.
5. Render will automatically discover [`render.yaml`](file:///c:/Users/ASUS/Desktop/AgentMarketPlace/render.yaml) and provision:
   - Database: `agent-marketplace-postgres` (PostgreSQL 16)
   - Web Service: `agent-marketplace-api` (Python runtime with 1 Uvicorn worker)
6. Click **Apply**.

#### Option B: Manual Provisioning
1. **Create PostgreSQL Database:**
   - Click **New +** -> **PostgreSQL**.
   - Name: `agent-marketplace-postgres`, Database: `agent_marketplace`, User: `agent_marketplace_user`.
   - Region: `Oregon (US West)` or `Frankfurt (EU Central)`.
   - Plan: Free or Starter. Click **Create Database**.
2. **Create Web Service:**
   - Click **New +** -> **Web Service**.
   - Connect repository and select branch: `M1`.
   - Environment: `Python`, Region: Same as database.
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
   - Health Check Path: `/health`
   - Configure Environment Variables:
     - `ENVIRONMENT`: `production`
     - `DATABASE_URL`: *Render Internal Database Connection String*
     - `CORS_ALLOWED_ORIGINS`: `https://<your-vercel-domain>.vercel.app` (do NOT use wildcard `*`; local dev `http://localhost:5173` is strictly optional for development)
     - `BLOCKCHAIN_NETWORK`: `eip155:84532`
     - `BASE_SEPOLIA_RPC_URL`: `https://sepolia.base.org`
     - `CHAIN_ID`: `84532`
     - `USDC_CONTRACT_ADDRESS`: `0x036CbD53842c5426634e7929541eC2318f3dCF7e`
     - `USDC_DECIMALS`: `6`
     - `X402_FACILITATOR_URL`: `https://facilitator.x402.org`
     - `BUYER_WALLET_ADDRESS`: `0x0000000000000000000000000000000000000000` *(Placeholder: read-only/mock mode only)*
     - `DATA_SELLER_PAY_TO`: `0x0000000000000000000000000000000000000001` *(Placeholder: read-only/mock mode only)*
     - `SCRAPING_SELLER_PAY_TO`: `0x0000000000000000000000000000000000000002` *(Placeholder: read-only/mock mode only)*
     - `INFERENCE_SELLER_PAY_TO`: `0x0000000000000000000000000000000000000003` *(Placeholder: read-only/mock mode only)*
   - Click **Create Web Service**. Note your Render URL (e.g., `https://agent-marketplace-api.onrender.com`).

---

### Step 3: Apply Safe, Repeatable Schema Migrations

The database initialization and schema migration logic in [`backend/database/session.py`](file:///c:/Users/ASUS/Desktop/AgentMarketPlace/backend/database/session.py) executes automatically upon startup inside FastAPI's `lifespan` handler. It is:
- **Idempotent:** Safe for repeated executions across instance restarts.
- **Non-Destructive:** Uses SQLAlchemy table inspection to detect missing columns and executes `ALTER TABLE ADD COLUMN` without dropping tables or wiping data.

If manual pre-migration execution is desired from the Render Shell:
```bash
python -m backend.database.session
```

---

### Step 4: Verify `/health` Reports Active Database Connectivity

From your terminal, test the deployed backend health check:
```bash
curl -i https://<your-render-api>.onrender.com/health
```

Expected output:
```text
HTTP/2 200
content-type: application/json

{
  "status": "healthy",
  "version": "0.1.0",
  "network": "eip155:84532",
  "services": {
    "database": "connected",
    "registry": "active",
    "payment_engine": "configured"
  }
}
```
*Note: If the database is disconnected, the endpoint returns `HTTP 503 Service Unavailable` with `"database": "disconnected"`.*

---

### Step 5: Deploy Frontend from `frontend/` on Vercel

1. Log in to [Vercel Dashboard](https://vercel.com/).
2. Click **Add New...** -> **Project**.
3. Import your GitHub repository: `AgentMarketPlace`.
4. Configure Project Settings:
   - **Framework Preset:** `Vite`
   - **Root Directory:** Click *Edit* and select `frontend` *(CRITICAL: do not deploy from repository root)*.
   - **Build Command:** `npm run build` (runs `tsc && vite build`)
   - **Output Directory:** `dist`
   - **Install Command:** `npm install`
5. Configure Environment Variables:
   - `VITE_API_BASE_URL`: `https://<your-render-api>.onrender.com`
6. Click **Deploy**.
7. Note your public Vercel production domain (e.g., `https://agent-marketplace-dashboard.vercel.app`).

---

### Step 6: Configure `VITE_API_BASE_URL` and Backend CORS Allowlist

1. **Verify Frontend URL:** Ensure `VITE_API_BASE_URL` in Vercel settings matches your exact Render public URL without a trailing slash.
2. **Update Backend CORS Allowlist:**
   - In Render Dashboard -> `agent-marketplace-api` -> **Environment**.
   - Set `CORS_ALLOWED_ORIGINS` to your exact Vercel production domain:
     ```text
     https://agent-marketplace-dashboard.vercel.app
     ```
   - If you have preview domains or custom domains, add them as comma-separated values:
     ```text
     https://agent-marketplace-dashboard.vercel.app,https://agent-marketplace.yourdomain.com
     ```
   - Save changes. Render will restart the service to apply the updated origin allowlist.

---

### Step 7: Test Real Deployed HTTPS Endpoints from Outside Process

Run external verification commands using `curl` against the live Render public URL:

```bash
# 1. Verify Service Registry
curl -s https://<your-render-api>.onrender.com/api/v1/services | jq .

# 2. Verify Audit Ledger
curl -s https://<your-render-api>.onrender.com/api/v1/ledger | jq .

# 3. Verify Seller Reputation
curl -s https://<your-render-api>.onrender.com/api/v1/reputation | jq .

# 4. Verify Payment Dashboard Metrics
curl -s https://<your-render-api>.onrender.com/api/v1/payments/dashboard | jq .

# 5. Verify Pending Suspense Items
curl -s https://<your-render-api>.onrender.com/api/v1/payments/reconciliations | jq .
```

All endpoints must return HTTP 200 with valid JSON contracts matching [`backend/shared/schemas.py`](file:///c:/Users/ASUS/Desktop/AgentMarketPlace/backend/shared/schemas.py).

---

### Step 8: Verify Ledger Persistence Across Backend Restart

To ensure durable PostgreSQL persistence survives web service restarts:

1. Submit a disposable test buyer task:
   ```bash
   curl -X POST https://<your-render-api>.onrender.com/api/v1/buyer/tasks \
     -H "Content-Type: application/json" \
     -d '{"task": "Analyze market trends for ETH", "budget_usdc": "0.05"}'
   ```
2. Retrieve the ledger records and record the newest `request_id`:
   ```bash
   curl -s https://<your-render-api>.onrender.com/api/v1/ledger | jq '.records[0]'
   ```
3. In Render Dashboard -> `agent-marketplace-api`, click **Manual Deploy** -> **Restart Service**.
4. Once the service completes restarting and returns to `Available`, re-query the ledger:
   ```bash
   curl -s https://<your-render-api>.onrender.com/api/v1/ledger | jq '.records[0]'
   ```
5. Confirm that the exact `request_id` and all 14 audit fields remain persisted and identical.

---

### Step 9: Exercise Multi-Hop Task & Check Cross-Component Consistency

1. **Trigger Multi-Hop Pipeline via API:**
   ```bash
   curl -X POST https://<your-render-api>.onrender.com/api/v1/payments/multi-hop \
     -H "Content-Type: application/json" \
     -d '{
       "steps": [
         {"service_id": "data_001", "input_data": {"ticker": "ETH"}, "max_cost_usdc": "0.005"},
         {"service_id": "scraping_001", "input_data": {"url": "https://example.com"}, "max_cost_usdc": "0.005"},
         {"service_id": "inference_001", "input_data": {"prompt": "Synthesize data"}, "max_cost_usdc": "0.005"}
       ],
       "max_total_budget_usdc": "0.020"
     }'
   ```
2. **Verify Dashboard Consistency:**
   - Open your deployed Vercel frontend URL in the browser.
   - Verify that the **Marketplace Settlement Spend** reflects the sum of successful steps.
   - Verify that the **Multi-Hop Execution Console & Telemetry** renders all three steps with individual step latency, costs, and settlement evidence labels.
   - Verify that **Provider Reputation Cards** reflect the newly executed calls without NaN or missing fields.

---

### Step 10: Troubleshooting & Diagnostic Runbook

| Problem Area | Symptom | Underlying Cause | Exact Remediation |
| :--- | :--- | :--- | :--- |
| **CORS Failure** | Browser console: `Cross-Origin Request Blocked: The Same Origin Policy disallows reading the remote resource...` | Deployed Vercel domain is not present in Render's `CORS_ALLOWED_ORIGINS`. | In Render dashboard -> `agent-marketplace-api` -> **Environment**, ensure `CORS_ALLOWED_ORIGINS` exactly matches your Vercel URL (e.g., `https://agent-marketplace-dashboard.vercel.app`) without trailing slashes. |
| **Database Disconnected** | `GET /health` returns `503 Service Unavailable` with `"database": "disconnected"`. | Render web service cannot connect to PostgreSQL instance or `DATABASE_URL` is incorrect. | 1. In Render, verify `agent-marketplace-postgres` status is `Available`.<br>2. Ensure `DATABASE_URL` uses the Internal Connection String if in the same region.<br>3. Verify connection format (Render injects `postgres://` which the backend normalizes to `postgresql://`). |
| **Silent Localhost Fallback Prevention** | Dashboard displays red banner: `Deployment Configuration Required: VITE_API_BASE_URL is not set...` | Operator deployed Vercel frontend without setting `VITE_API_BASE_URL`. | In Vercel Project Settings -> **Environment Variables**, set `VITE_API_BASE_URL=https://<your-render-api>.onrender.com` and trigger a redeployment. |
| **Vercel SPA 404 on Refresh** | Refreshing `/ledger` or any subroute returns `404 Not Found`. | Vercel attempts to resolve path as static asset instead of serving `index.html`. | Verify [`frontend/vercel.json`](file:///c:/Users/ASUS/Desktop/AgentMarketPlace/frontend/vercel.json) rewrite rule is present: `{"source": "/(.*)", "destination": "/index.html"}`. |
| **Cold Start Delays** | Initial request takes 30–50s after 15 minutes of inactivity. | Render free tier instances spin down after inactivity. | Expected behavior on free plan. Once awake, subsequent requests respond in <100ms. For persistent warmth, upgrade service to Starter plan. |

---

## 3. Security & Settlement Integrity Invariants

1. **Anti-Bypass Protection:** The backend requires verified proof records stored in PostgreSQL. Fabricated `onchain_confirmed_*` strings or arbitrary transaction hashes cannot produce `confirmed_on_chain` status.
2. **Evidence Preservation:** Retrying an attempt with weaker proof or local receipts will never overwrite an existing on-chain transaction hash or downgrade a terminal `paid` status.
3. **Integer Arithmetic:** All internal USDC calculations strictly use integer base units (`1 USDC = 1,000,000 base units`). Floating-point money math is forbidden.
4. **Secret Isolation:** `BUYER_PRIVATE_KEY` and database credentials must never be included in `VITE_*` environment variables on Vercel. Frontend variables are publicly visible in browser bundles.
5. **Database Locking & Worker Concurrency Guarantees:**
   - Single Uvicorn worker is the verified production configuration.
   - When using PostgreSQL in multi-worker environments, atomic budget reservation is serialized via PostgreSQL transaction advisory locks (`SELECT pg_advisory_xact_lock(hashtext(:task_id))`), and authorization nonce replay is protected via `SELECT pg_advisory_xact_lock(hashtext(:auth_key))`.
   - **Documented Unresolved Risk:** If an operator configures multiple workers against SQLite (where advisory locks are unavailable) or executes tasks without persistent task IDs, in-memory `asyncio.Lock` cannot synchronize across separate worker processes. Therefore, multi-worker scaling must only be deployed on Render with PostgreSQL and persistent task IDs.
