# AGENTICA — PHASE 6 CONFIGURATION & SECURITY AUDIT

**Phase:** 6.6 Configuration, CORS, Secrets, and Dependency Hygiene  
**Status:** **ACCEPTED**  
**Date:** 2026-10-17  
**Module Owner:** Setup Lead / Shared Architecture & DevOps  
**Evidence Classification:** VERIFIED BY CODE INSPECTION  

---

## 1. Executive Summary

This audit establishes the security posture, credential safety, dependency versioning, and environment boundaries of AGENTICA.

### Key Verified Invariants:
1. **Zero Secret Leakage:** Tracked files, example templates (`.env.example`), logs, and frontend bundles were audited. No live private keys, mnemonic phrases, or paid vendor API tokens are present in the repository.
2. **Environment Variable Confinement:** Configuration is loaded strictly via Pydantic Settings (`pydantic_settings.BaseSettings`) in `backend/shared/config.py` with type enforcement.
3. **CORS Deployment Boundary:** 
   - Development Mode: Configures `allow_origins=["*"]` for frictionless Vite and Docker development.
   - Production Requirement: Public deployments must configure explicit trusted origins (`["https://app.agentica.network"]`).
4. **Log Sanitization:** Sensitive authorization headers, full EIP-712 signatures, and raw request bodies are redacted or hashed before writing to logs.

---

## 2. Environment Variable Specification

| Variable | Type | Default | Production Requirement |
|---|---|---|---|
| `ENVIRONMENT` | string | `"development"` | Set to `"production"` |
| `BLOCKCHAIN_NETWORK` | string | `"eip155:84532"` | Fixed to Base Sepolia (locked) |
| `BASE_SEPOLIA_RPC_URL` | string | `"https://sepolia.base.org"` | Verified JSON-RPC endpoint |
| `USDC_CONTRACT_ADDRESS` | string | `0x036CbD...` | Base Sepolia USDC contract |
| `BUYER_WALLET_ADDRESS` | string | `0x000...` | Injected via secure vault |
| `BUYER_PRIVATE_KEY` | string | `None` | Injected via secure secret manager |
| `DATABASE_URL` | string | `sqlite:///./local_data/ledger.db` | PostgreSQL connection string |
| `SELLER_PROVIDER_MODE` | string | `"fake"` | Set to `"live"` only when API keys provisioned |
| `GEMINI_API_KEY` | string | `None` | Required for live Gemini Flash 3.8 inference |
| `GROQ_API_KEY` | string | `None` | Required for live Groq Qwen inference |

---

## 3. Dependency & Version Standards

- **Python Runtime:** Requires Python `>=3.11` (verified on Python `3.14.3`).
- **Core Packages:** `fastapi>=0.115.0`, `pydantic>=2.8.0`, `httpx>=0.27.0`, `SQLAlchemy>=2.0.30`, `web3>=6.19.0`, `eth-account>=0.11.0`.
- **Node Runtime:** Node `>=18` (verified on Node `v24.16.0`).
- **Frontend Stack:** React `^18.3.1`, Vite `^5.4.21`, TypeScript `^5.5.3`.

---

## 4. Supply Chain & Git Security Signoff

- `.gitignore` verified: Excludes `.env`, `*.db`, `*.sqlite`, `local_data/`, `node_modules/`, `dist/`.
- Zero credentials committed in Git history.
- Fail-closed configuration: Missing live credentials raise `ProviderConfigurationError` with zero silent fallback to mock data.

**Gate Status:** PHASE 6 GATE D (SECURITY & CONFIGURATION HYGIENE) — **PASSED**.
