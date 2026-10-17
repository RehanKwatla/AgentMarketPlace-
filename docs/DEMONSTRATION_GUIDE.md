# AGENTMARKETPLACE DI-06: END-TO-END DEMONSTRATION GUIDE
## Reproducible Walkthrough for Autonomous Paid Microservice Economy

**Project:** AgentMarketplace DI-06 — Pay-Per-Call Agent Economy
**Protocol:** x402 v2 Payment Protocol
**Settlement Network:** Base Sepolia Testnet (`eip155:84532`)
**Settlement Asset:** Base Sepolia USDC (`0x036CbD53842c5426634e7929541eC2318f3dCF7e`)
**Status:** Validated Offline / Testnet Simulation (Gate D Active)

---

## 1. Prerequisites & Environment Setup

### System Requirements
- **Python:** 3.11+ (Python 3.12/3.14 verified)
- **Node.js:** v18+ or v20+ with npm
- **Docker & Docker Compose** (Optional for containerized run)
- **Git**

### Installation Commands
```bash
# Clone and enter workspace
cd AgentMarketPlace

# 1. Backend environment setup
pip install -r requirements.txt

# 2. Frontend environment setup
cd frontend
npm install
cd ..
```

### Environment Configuration
Copy the template configuration:
```bash
cp .env.example .env
```
Ensure `.env` contains the default mock/testnet settings:
```ini
ENVIRONMENT=development
BLOCKCHAIN_NETWORK=eip155:84532
BASE_SEPOLIA_RPC_URL=https://sepolia.base.org
USDC_CONTRACT_ADDRESS=0x036CbD53842c5426634e7929541eC2318f3dCF7e
HOST=0.0.0.0
PORT=8000
VITE_API_BASE_URL=http://localhost:8000
```

---

## 2. Startup Procedures

### Option A: Local Development (Recommended for Testing & Demos)
Open two terminal windows:

**Terminal 1 — Backend API Server:**
```powershell
python scripts/start_dev.py --backend-only
# Server starts at http://localhost:8000
# OpenAPI Docs available at http://localhost:8000/docs
```

**Terminal 2 — Frontend Dashboard:**
```powershell
cd frontend
npm run dev
# Vite dev server runs at http://localhost:5173
```

### Option B: Containerized Docker Compose
```bash
docker compose up --build
# Backend: http://localhost:8000
# Frontend: http://localhost:5173
# PostgreSQL: localhost:5432
```

---

## 3. End-to-End Three-Category Demonstration

The marketplace hosts three canonical seller microservices participating in the x402 economy:
1. **Data:** `data_001` (Financial asset market data, priced at `0.002` USDC)
2. **Scraping:** `scraping_001` (Clean web extraction & word count, priced at `0.003` USDC)
3. **Inference:** `inference_001` (Analytical summarization & reasoning, priced at `0.004` USDC)

### Category 1: Real-Time Market Data Service (`data_001`)

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/payments/multi-hop \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "demo_data_001",
    "steps": [
      {
        "step_id": 1,
        "service_id": "data_001",
        "input_payload": {"symbol": "ETH"},
        "depends_on": []
      }
    ],
    "max_budget_usdc": 0.05
  }'
```

**Observed Real Response:**
```json
{
  "task_id": "demo_data_001",
  "status": "completed",
  "total_hops": 1,
  "executed_hops": 1,
  "successful_hops": 1,
  "total_cost_usdc": "0.002000",
  "total_cost_base_units": 2000,
  "steps": [
    {
      "task_id": "demo_data_001",
      "call_id": "call_demo_data_001_s1",
      "service_id": "data_001",
      "status": "paid",
      "amount_usdc": "0.002000",
      "settlement_proof": "rec_auth_e58f0c08a9ef555f",
      "seller_output": {
        "symbol": "ETH",
        "price": 2650.5,
        "volume_24h": 1420500.0,
        "timestamp": "2026-10-16T23:25:50.495722+00:00"
      }
    }
  ],
  "final_output": {
    "symbol": "ETH",
    "price": 2650.5,
    "volume_24h": 1420500.0,
    "timestamp": "2026-10-16T23:25:50.495722+00:00"
  }
}
```

---

### Category 2: Web Scraping Service (`scraping_001`)

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/payments/multi-hop \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "demo_scraping_001",
    "steps": [
      {
        "step_id": 1,
        "service_id": "scraping_001",
        "input_payload": {"url": "https://news.ycombinator.com"},
        "depends_on": []
      }
    ],
    "max_budget_usdc": 0.05
  }'
```

**Observed Real Response:**
```json
{
  "task_id": "demo_scraping_001",
  "status": "completed",
  "total_hops": 1,
  "executed_hops": 1,
  "successful_hops": 1,
  "total_cost_usdc": "0.003000",
  "total_cost_base_units": 3000,
  "steps": [
    {
      "task_id": "demo_scraping_001",
      "call_id": "call_demo_scraping_001_s1",
      "service_id": "scraping_001",
      "status": "paid",
      "amount_usdc": "0.003000",
      "settlement_proof": "rec_auth_db77d933b2ad779e",
      "seller_output": {
        "url": "https://news.ycombinator.com",
        "title": "Extracted Content from news.ycombinator.com",
        "content": "Simulated web scraping extraction...",
        "word_count": 48
      }
    }
  ]
}
```

---

### Category 3: Analytical Inference Service (`inference_001`)

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/payments/multi-hop \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "demo_inference_001",
    "steps": [
      {
        "step_id": 1,
        "service_id": "inference_001",
        "input_payload": {"prompt": "Summarize market trends based on latest news"},
        "depends_on": []
      }
    ],
    "max_budget_usdc": 0.05
  }'
```

**Observed Real Response:**
```json
{
  "task_id": "demo_inference_001",
  "status": "completed",
  "total_hops": 1,
  "executed_hops": 1,
  "successful_hops": 1,
  "total_cost_usdc": "0.004000",
  "total_cost_base_units": 4000,
  "steps": [
    {
      "task_id": "demo_inference_001",
      "call_id": "call_demo_inference_001_s1",
      "service_id": "inference_001",
      "status": "paid",
      "amount_usdc": "0.004000",
      "settlement_proof": "rec_auth_8af7af6d8ab41f05",
      "seller_output": {
        "response": "Analytical Synthesis: Based on prompt 'Summarize market trends based on latest news', the system identified high-signal convergence towards autonomous microservice settlements.",
        "model_used": "agent-economy-reasoner-v1",
        "tokens_generated": 21
      }
    }
  ]
}
```

---

### End-to-End Multi-Hop Pipeline (Data + Scraping -> Inference DAG)

**Natural Language Execution via Buyer Agent:**
```bash
curl -X POST http://localhost:8000/api/v1/buyer/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Scrape web news on ETH crypto data and summarize key takeaways",
    "budget_usdc": "0.05"
  }'
```

**Observed Execution Details:**
- **Selected Services:** `data_001`, `scraping_001`, `inference_001`
- **Total Cost:** `0.009000 USDC` (`9,000` base units)
- **Hop 1 (Data):** Symbol `ETH` fetched, price `2650.5` (Cost: `0.002` USDC)
- **Hop 2 (Scraping):** Web content fetched (Cost: `0.003` USDC)
- **Hop 3 (Inference):** Synthesizes outputs from Step 1 and Step 2 (Cost: `0.004` USDC)
- **Settlement Proofs:** All recorded with durable receipts (`rec_auth_*`) and stored in the ledger.

---

## 4. Dashboard Inspection Procedure

1. Open your browser at `http://localhost:5173`.
2. Inspect the **Top Overview Cards**:
   - **Marketplace Settlement Spend:** Reflects total authorized spend in USDC and call counts.
   - **Settlement Evidence Status:** Displays `Confirmed On-Chain: 0`, `Local Auth (rec_auth_*): N`, `Unverified Hash: 0`, and `Pending Reconciliation: N`.
   - **Protocol & Gate D Status:** Displays `Base Sepolia (84532)`, `USDC (6 decimals)`, `x402 Protocol v2.0`, and active `Gate D: Offline Verification Mode`.
3. Test **Autonomous Buyer Agent Task Execution**:
   - Enter `Scrape web news on ETH crypto data and summarize key takeaways` with Budget `0.05` USDC.
   - Click `EXECUTE PAY-PER-CALL TASK`.
   - Observe real-time progress spinner: *"Negotiating x402 challenge & settling Base Sepolia micropayments..."*
   - Verify the **Executed Hops Breakdown** shows all 3 hops with latencies and Local Auth tags.
4. Inspect the **Immutable Payment Ledger**:
   - Verify all transactions are timestamped and tagged with truthful `Local Auth (rec_auth_...)` or `Unverified Hash` badges.

---

## 5. Troubleshooting & Common Issues

| Symptom | Cause | Solution |
| :--- | :--- | :--- |
| `TypeError: Failed to fetch` in browser | Backend server is not running on port 8000 | Run `python scripts/start_dev.py --backend-only` |
| `Port 5173 already in use` | Another Vite process is open | Kill the process or set `PORT=5174` in `.env` |
| Status remains `pending reconciliation` | Network or seller timeout occurred | Run `POST /api/v1/payments/reconcile` to retry reconciliation |
| Test failures on Windows PowerShell | Python virtual environment or path issue | Run tests using `python scripts/run_tests.py` |
| Docker Compose DB connection error | Port 5432 conflict with local PostgreSQL | Change host port mapping in `docker-compose.yml` to `"5433:5432"` |
