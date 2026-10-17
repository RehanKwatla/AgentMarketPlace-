# AGENTICA — PHASE 4 TEST & DEMO RUNBOOK
**Document:** `docs/PHASE4_TEST_AND_DEMO_RUNBOOK.md`  
**Date:** 17 October 2026  
**Auditor:** Setup Lead & Member 4 (DevOps Engineer)  
**Status:** COMPLETE (Stage 8 Master Plan)  
**Classification:** VERIFIED OPERATIONAL PROCEDURE  

---

## 1. Operating Modes Overview

AGENTICA supports four distinct operating configurations:

| Mode | Environment Flag | Blockchain Settlement | External Providers | Primary Purpose |
|---|---|---|---|---|
| **Automated Test Mode** | Default / `SELLER_PROVIDER_MODE=fake` | Mock / Test double | Deterministic fake | Fast, deterministic CI regression suite (`pytest`) |
| **Deterministic Demo Mode** | `SELLER_PROVIDER_MODE=fake` | Facilitator receipt double | Deterministic fake | Repeatable offline judge presentation without external latency |
| **Live Provider Mode** | `SELLER_PROVIDER_MODE=live` | Facilitator receipt double | Live Gemini 3.8 / Groq LLMs | Real external AI & web scraping demonstration |
| **Live Blockchain Mode** | `SELLER_PROVIDER_MODE=live` | Base Sepolia (`eip155:84532`) | Live providers | Full testnet USDC settlement (requires funded wallet) |

---

## 2. Environment Setup

### 2.1 Backend Prerequisites
- Python 3.11+ (Python 3.14 compatible)
- Virtual environment with dependencies from `requirements.txt`:
  ```powershell
  pip install -r requirements.txt
  ```

### 2.2 Frontend Prerequisites
- Node.js v18+ and npm
- Dependencies installed via clean lockfile:
  ```powershell
  cd frontend
  npm ci
  ```

---

## 3. Starting the Platform

### 3.1 Start the FastAPI Backend
In root directory `c:\AgentMarket`:
```powershell
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
Verify backend health:
```powershell
curl http://localhost:8000/health
```
Expected output:
```json
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

### 3.2 Start the React Frontend Dashboard
In directory `c:\AgentMarket\frontend`:
```powershell
npm run dev
```
Open browser to `http://localhost:5173`.

---

## 4. Running Verifications & Test Suites

### 4.1 Backend Regression Suite
Runs all 284 unit and integration tests:
```powershell
python -m pytest backend/tests/ -v
```
Expected result: **284 passed in ~11s**.

### 4.2 Frontend Type-Check & Production Build
```powershell
cd frontend
npm run build
```
Expected result: **Built in ~2.5s with 0 errors**.

---

## 5. Running the Autonomous Buyer Demo

### 5.1 Deterministic Offline Demo (Recommended for Presentations)
Runs the full 3-hop pipeline (Data -> Scraping -> Inference) through the payment client and audit ledger:
```powershell
$env:SELLER_PROVIDER_MODE="fake"
python scripts/demo_m3_orchestration.py
```
**Expected Trace Output:**
- Step 1 [SCRAPING]: `SUCCEEDED` (0.003 USDC paid)
- Step 2 [DATA]: `SUCCEEDED` (0.002 USDC paid)
- Step 3 [INFERENCE]: `SUCCEEDED` (0.004 USDC paid)
- Final Status: `COMPLETED`
- Total Spent: `0.009000 USDC` (9,000 atomic units)
- Audit Records: 3 new records logged in `LedgerRepository`

### 5.2 Live Provider Demo (Gemini & Groq)
Requires active internet connection and configured API keys in `.env`:
```powershell
$env:SELLER_PROVIDER_MODE="live"
python -c "
import asyncio
from backend.sellers.inference_seller import InferenceSellerService
from backend.sellers.schemas import InferenceSellerInput
from backend.sellers.common import SellerExecutionContext

async def test():
    svc = InferenceSellerService()
    ctx = SellerExecutionContext(request_id='demo_live', service_id='inference_001')
    res, metrics = await svc.execute_lifecycle(InferenceSellerInput(prompt='Summarize Base Sepolia advantages in 20 words'), ctx)
    print('Live AI Response:', res.response)

asyncio.run(test())
"
```

---

## 6. Troubleshooting & Diagnostics

| Symptom | Cause | Resolution |
|---|---|---|
| `503 PAYMENT_VERIFIER_UNAVAILABLE` | No `SellerPaymentVerifier` configured | Ensure `get_seller_payment_verifier` dependency is injected or override provided. |
| `402 Payment Required` on initial request | Normal x402 challenge | Client must parse `X-402-Requirement` header and re-request with `X-402-Payment-Payload`. |
| `HTTP 500: LIVE mode requires DATA_PROVIDER_URL` | `SELLER_PROVIDER_MODE=live` without data API | Set `SELLER_PROVIDER_MODE=fake` for demo, or provide `DATA_PROVIDER_URL`. |
| `[Errno 11001] getaddrinfo failed` | Trailing punctuation or invalid URL in prompt | Remove commas/punctuation from target URLs (e.g. `https://ethereum.org`). |
| Database locked / concurrency conflict | Multi-process SQLite lock | Ensure transactions use scoped sessions; PostgreSQL container handles high concurrency. |
