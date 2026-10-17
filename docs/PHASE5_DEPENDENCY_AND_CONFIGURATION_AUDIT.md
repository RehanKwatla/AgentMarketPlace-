# AGENTICA — PHASE 5 DEPENDENCY & CONFIGURATION AUDIT

**Phase:** 5.10 Dependency, Configuration, and Supply-Chain Review  
**Status:** ACCEPTED  
**Date:** 2026-10-17  
**Module Owner:** Setup Lead / Shared Architecture & DevOps  
**Evidence Classification:** VERIFIED BY CODE INSPECTION & SYSTEM ENVIRONMENT AUDIT  

---

## 1. Executive Summary

This audit assesses the runtime dependencies, supply chain boundaries, configuration management, and environment variable security for AGENTICA.

The backend operates on standard, well-maintained packages (`fastapi`, `pydantic`, `httpx`, `sqlalchemy`, `web3`, `eth-account`) requiring Python `>=3.11` (currently verified on Python `3.14.3`). The frontend operates on standard React 18 / Vite 5 / TypeScript. No deprecated or unmaintained packages are introduced.

---

## 2. Dependency Inventories

### 2.1 Backend Dependencies (`pyproject.toml`)
| Package | Version Spec | Purpose | Security Review |
|---------|--------------|---------|-----------------|
| `fastapi` | `>=0.115.0` | Core asynchronous web framework | Active, modern OpenAPI standard |
| `uvicorn[standard]` | `>=0.30.0` | ASGI web server | Production standard |
| `pydantic` | `>=2.8.0` | Data modeling & JSON schema validation | V2 performance & typing |
| `pydantic-settings` | `>=2.4.0` | 12-factor environment configuration | Strict type-checked settings |
| `httpx` | `>=0.27.0` | Asynchronous HTTP client for x402 calls | Supports custom socket transports |
| `SQLAlchemy` | `>=2.0.30` | ORM & database connection pooling | 2.0 type-safe unified querying |
| `python-dotenv` | `>=1.0.1` | Local development `.env` loading | Safe developer ergonomics |
| `web3` | `>=6.19.0` | Ethereum & Base Sepolia JSON-RPC client | Standard EVM library |
| `eth-account` | `>=0.11.0` | EIP-712 cryptographic signature handling | Official Ethereum Foundation SDK |

### 2.2 Frontend Dependencies (`frontend/package.json`)
- React `^18.3.1`, React DOM `^18.3.1`
- Vite `^5.4.21` (bundler)
- TypeScript `^5.5.3`
- Lucide React `^0.441.0` (accessible icon library)

---

## 3. Configuration Management & Environment Variables

All configuration is loaded via `Settings` (`pydantic_settings.BaseSettings`) in `backend/shared/config.py`:

| Variable | Default Value | Production Requirement |
|----------|---------------|------------------------|
| `ENVIRONMENT` | `"development"` | Set to `"production"` |
| `BLOCKCHAIN_NETWORK` | `"eip155:84532"` | Fixed to Base Sepolia (locked) |
| `BASE_SEPOLIA_RPC_URL` | `"https://sepolia.base.org"` | Verified RPC endpoint or private node |
| `USDC_CONTRACT_ADDRESS` | `0x036CbD53842c5426634e7929541eC2318f3dCF7e` | Fixed to Base Sepolia USDC |
| `BUYER_WALLET_ADDRESS` | `0x000...` | Provisioned funded testnet address |
| `BUYER_PRIVATE_KEY` | `None` | Injected via secure vault/secret manager |
| `DATABASE_URL` | `sqlite:///./local_data/ledger.db` | PostgreSQL connection string for production |
| `SELLER_PROVIDER_MODE` | `"fake"` | Set to `"live"` only when API keys are provisioned |
| `GEMINI_API_KEY` | `None` | Required for live inference via Gemini |
| `GROQ_API_KEY` | `None` | Required for live inference via Groq |

---

## 4. Supply Chain & Configuration Findings

1. **Explicit Testnet Confinement:** `BLOCKCHAIN_NETWORK` and `USDC_CONTRACT_ADDRESS` are pinned to Base Sepolia testnet constants. Production deployment configs are prevented from connecting to Ethereum mainnet without manual codebase alterations.
2. **CORS Exposure:** `allow_origins=["*"]` is active in `backend/main.py` for hackathon developer velocity. In an enterprise internet-facing deployment, origins must be restricted to the authoritative frontend domain.
3. **Absence of Secrets in Repository:** The `.gitignore` properly excludes `.env`, `*.db`, and key files. All templates (`.env.example`) contain placeholders (`0x000...`).

**Gate Status:** PHASE 5 GATE H (CONFIGURATION REVIEW) — **PASSED**.
