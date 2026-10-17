# AGENTICA — PHASE 7 OPERATIONAL RELEASE RUNBOOK

**Project:** DI-06 — AGENTICA: Pay-per-Call Agent Economy  
**Tagline:** Discover. Pay. Execute. Trust.  
**Phase:** 7 Operational Runbook  
**Date:** 2026-10-17  
**Module Owners:** DevOps, Release Engineering, and QA Lead  

---

## 1. System Requirements & Prerequisites

### 1.1 Toolchain
- **Python:** 3.10+ (Tested on Python 3.14.3)
- **Node.js:** v18+ (Tested on Node v24.14.0, npm 11.9.0)
- **Database:** SQLite (default for local development) or PostgreSQL 14+
- **Network Access:** Outbound HTTPS to `https://sepolia.base.org` (port 443)

### 1.2 Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Key environment settings:
```ini
# Core Configuration
ENVIRONMENT=development
LOG_LEVEL=INFO
PORT=8000

# Blockchain (Base Sepolia Testnet)
BLOCKCHAIN_NETWORK=eip155:84532
BASE_SEPOLIA_RPC_URL=https://sepolia.base.org
CHAIN_ID=84532
USDC_CONTRACT_ADDRESS=0x036CbD53842c5426634e7929541eC2318f3dCF7e
USDC_DECIMALS=6

# Provider Operating Mode (fake or live)
SELLER_PROVIDER_MODE=fake

# Frontend Origins
CORS_ALLOWED_ORIGINS=http://localhost:5173
```

---

## 2. Standard Operating Procedures

### 2.1 Running the Backend
From the repository root:
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
Verify health:
```bash
curl http://localhost:8000/health
# Response: {"status":"healthy","network":"eip155:84532"}
```

### 2.2 Running the Frontend
From the `frontend/` directory:
```bash
npm install
npm run dev
```
Open `http://localhost:5173` in a modern browser.

### 2.3 Running the Full Verification Test Suite
```bash
# Backend pytest suite
python -m pytest backend/tests/ -v

# Frontend TypeScript check & production bundle build
cd frontend && npm run build
```

### 2.4 Executing the Offline Buyer Orchestration Demo
```bash
# In PowerShell:
$env:SELLER_PROVIDER_MODE="fake"; python scripts/demo_m3_orchestration.py

# In Bash:
SELLER_PROVIDER_MODE="fake" python scripts/demo_m3_orchestration.py
```

---

## 3. Pre-Live Settlement Checklist (Gate 15)

Before performing any controlled on-chain payment test:
1. [ ] Confirm network is Base Sepolia (`eip155:84532`).
2. [ ] Confirm token is official Base Sepolia USDC (`0x036CbD53842c5426634e7929541eC2318f3dCF7e`).
3. [ ] Verify buyer wallet contains testnet Sepolia ETH (for gas) and testnet USDC.
4. [ ] Ensure spend caps are configured (`BUYER_DEFAULT_PER_REQUEST_MAX_USDC=0.005000`).
5. [ ] Obtain separate explicit human operator authorization for the transaction.
6. [ ] Never enter, copy, or print private keys in chat or terminal logs.

---

## 4. Emergency Procedures & Suspense Resolution

If an on-chain transaction or RPC query times out:
1. The payment engine transitions the attempt to `PENDING_RECONCILIATION`.
2. Budget reservation remains locked in suspense; no funds are prematurely released or re-charged.
3. Automated fallback execution is blocked to avoid duplicate payment.
4. Run manual reconciliation:
   ```python
   from backend.payments.reconciliation import reconcile_pending_settlement
   await reconcile_pending_settlement(attempt_id)
   ```
5. Check transaction status directly on [BaseScan Sepolia](https://sepolia.basescan.org).
