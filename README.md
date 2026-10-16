# Pay-Per-Call Agent Economy (DI-06)

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Base Sepolia](https://img.shields.io/badge/Network-Base%20Sepolia-0052FF.svg)](https://sepolia.basescan.org)
[![x402 Protocol](https://img.shields.io/badge/Payments-x402%20v2-orange.svg)](https://x402.org)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?logo=python&logoColor=white)](https://python.org)

An autonomous pay-per-call microservice agent economy built for the **DI-06 Hackathon**. Autonomous buyer agents discover services, evaluate reputation, reserve atomic budgets, and purchase services from specialized seller agents via the **x402 v2 payment lifecycle** with USDC on **Base Sepolia (`eip155:84532`)**.

---

## 🚀 Key System Features

1. **Service Registry & Marketplace:** Dynamic catalog with filtering by category, max price, and capability schemas.
2. **Three Specialized Seller Agents:**
   - **Data Seller:** Structured market and financial statistics.
   - **Scraping Seller:** Real-time web extraction and markdown conversion.
   - **Inference Seller:** LLM synthesis, summarization, and sentiment reasoning.
3. **Autonomous Buyer Agent:** Goal decomposition, reputation-aware provider selection, atomic budget reservation, and multi-service aggregation.
4. **Official x402 v2 Payment Flow:** Real HTTP 402 challenge/response with EIP-712 payment authorizations and verifiable facilitator settlement proofs.
5. **Security & Financial Guardrails:** Integer USDC base unit arithmetic (6 decimals), replay protection, nonce validation, idempotency cache, and atomic budget reservation locks.
6. **Immutable Ledger & Reputation:** Four-state audit trail (`paid`, `paid output rejected`, `refused`, `failed and not charged`) and real-time reliability scoring.
7. **Web Dashboard:** Interactive React/Vite/Tailwind UI for real-time monitoring and inspection.

---

## 📁 Repository Layout & Member Ownership

```
pay-per-call-agent-economy/
├── AGENTS.md                  # Strict rules for all AI agents & developers
├── README.md                  # Project overview and quickstart
├── .env.example               # Configuration template (NO SECRETS)
├── docker-compose.yml         # Containerized orchestration
├── requirements.txt           # Python backend dependencies
├── pyproject.toml             # Packaging & pytest configuration
├── backend/
│   ├── main.py                # App shell & router mounting (Setup Lead)
│   ├── shared/                # Shared schemas, config & errors (Setup Lead)
│   ├── payments/              # x402 v2 integration & security (Member 1)
│   ├── sellers/               # Data, Scraping, Inference agents (Member 2)
│   ├── buyer/                 # Planner, selector, buyer agent (Member 3)
│   ├── registry/              # Service catalog & discovery (Member 3)
│   ├── ledger/                # Audit log, reputation, reconciliation (Member 4)
│   ├── database/              # SQLAlchemy sessions & models (Member 4)
│   └── tests/                 # Automated test suite (All Members)
├── frontend/                  # React + Vite + Tailwind dashboard (Member 4)
├── docs/                      # Architectural & API contracts
└── scripts/                   # Dev runners & test scripts
```

---

## ⚡ Quickstart

### 1. Prerequisites
- Python 3.11+ (Python 3.14 verified)
- Node.js 18+ & npm
- Git

### 2. Setup & Run
```bash
# 1. Clone repository
git clone <REPO_URL>
cd AgentMarketPlace

# 2. Configure Environment
cp .env.example .env

# 3. Start Backend
python scripts/start_dev.py --backend-only

# 4. Run Automated Tests
python scripts/run_tests.py
```

API Documentation: `http://localhost:8000/docs`  
Interactive Dashboard: `http://localhost:5173`

---

## 📖 Key Documentation
- [AGENTS.md](AGENTS.md) — Mandatory developer & agent rules.
- [docs/API_CONTRACTS.md](docs/API_CONTRACTS.md) — Shared API specifications.
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — System architecture & sequence diagrams.
- [docs/SECURITY.md](docs/SECURITY.md) — Cryptographic & payment security boundaries.
- [docs/TEAM_WORKFLOW.md](docs/TEAM_WORKFLOW.md) — Branch rules & team guide.
- [docs/DEMO.md](docs/DEMO.md) — Judges demonstration runbook.
