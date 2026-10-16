# HACKATHON DEMO RUNBOOK — DI-06 JUDGES GUIDE

## 1. Quickstart (Live Demo in 3 Minutes)

### Step 1: Start the Backend & Frontend
```bash
# Terminal 1: Backend
python scripts/start_dev.py --backend-only

# Terminal 2: Frontend
cd frontend && npm run dev
```

Open Dashboard at: `http://localhost:5173`
API Documentation at: `http://localhost:8000/docs`

---

## 2. End-to-End Demo Script for Judges

### Act I: Inspect Service Marketplace
1. Show the Registry UI on the Dashboard (`GET /api/v1/services`).
2. Highlight the three distinct seller agents:
   - **Data Seller:** Real-time crypto market data quotes (`0.002 USDC`).
   - **Scraping Seller:** Clean web markdown extractor (`0.003 USDC`).
   - **Inference Seller:** LLM analysis and summarization (`0.004 USDC`).
3. Note that each seller specifies its network (`eip155:84532`), token address, and registered `payTo` address.

### Act II: Trigger Autonomous Buyer Task
1. In the Dashboard (or via Swagger at `/docs`), send a task to `POST /api/v1/buyer/tasks`:
```json
{
  "task": "Extract recent market sentiment on ETH and summarize trading signals",
  "budget_usdc": "0.02"
}
```
2. Observe live execution logs:
   - Task planner identifies required subtasks.
   - Budget manager atomically locks estimated USDC base units.
   - Buyer sends pre-flight request to Scraping Seller -> receives HTTP 402 with `X-402-Requirement`.
   - Buyer signs payment authorization on Base Sepolia.
   - Seller submits to Facilitator -> settles payment -> executes scraping logic.
   - Buyer validates returned schema.
   - Buyer sends next request to Inference Seller -> settles payment -> generates final synthesis.

### Act III: Inspect Persistent Ledger & Reputation
1. Navigate to the Ledger View on the Dashboard (`GET /api/v1/ledger`).
2. Show the transaction records, exact timestamps, transaction hashes, latencies, and terminal status (`paid`).
3. Highlight Reputation scores updated in real time based on successful schema delivery.

### Act IV: Security & Fault Demonstration
1. Demonstrate budget overdraw rejection: Trigger a task with `0.001 USDC` budget when cheapest service is `0.002 USDC`. System safely halts with `refused`.
2. Demonstrate invalid schema detection: If a seller returns corrupted JSON, the ledger reflects `paid output rejected` and decrements reputation.
