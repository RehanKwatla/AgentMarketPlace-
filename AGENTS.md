# AGENTS.md — CODE OF CONDUCT & RULES FOR ALL AGENTS

Welcome to the **DI-06: Pay-Per-Call Agent Economy** hackathon project.
All AI agents, pair programmers, and human developers collaborating on this repository **MUST** adhere strictly to the following binding rules.

---

## 1. Scope & Module Boundaries
1. **Module Ownership is Strict:**
   - **Member 1 (feature/payments):** Owns `backend/payments/`.
   - **Member 2 (feature/sellers):** Owns `backend/sellers/`.
   - **Member 3 (feature/buyer-registry):** Owns `backend/buyer/` and `backend/registry/`.
   - **Member 4 (feature/dashboard-ledger):** Owns `backend/ledger/`, `backend/database/`, `frontend/`, and deployment docs.
   - **Project Setup Lead:** Owns `backend/shared/`, `backend/main.py`, root configs, and `docs/API_CONTRACTS.md`.
2. **Never Overwrite Unrelated Modules:** Do not modify code outside your assigned directory without formal review and approval from the module owner and setup lead.
3. **No Unilateral Changes to Shared Interfaces:** `backend/shared/schemas.py`, `config.py`, and `docs/API_CONTRACTS.md` are the single source of truth. Changes require explicit consensus.

---

## 2. Integrity & Truthfulness
1. **Never Fabricate Payment Evidence:**
   - **DO NOT** mock fake transaction hashes (e.g. `0x1234...fake`).
   - **DO NOT** create dummy responses claiming successful payment unless verified against the actual x402 payment lifecycle or genuine testnet receipt.
   - HTTP 200 DOES NOT prove settlement.
2. **Honesty on Unimplemented Features:**
   - Clearly label code as:
     - `[IMPLEMENTED]` — fully functional and tested.
     - `[DEFINED INTERFACE]` — abstract contract awaiting implementation.
     - `[STUB]` — temporary scaffold returning mock/501 Not Implemented.
3. **Report Actual Test Results:** Always run tests using `pytest` or `scripts/run_tests.py` and report true stdout/stderr outputs. Never claim tests passed when they were not run or failed.

---

## 3. Security & Safety Rules
1. **Official x402 v2 SDK Only:**
   - Do NOT invent a custom replacement for x402 v2.
   - Use the official x402 protocol specification and Python SDK.
2. **Testnet Funds Only:**
   - Network: Base Sepolia (`eip155:84532`).
   - Token: Base Sepolia USDC.
   - NEVER use mainnet funds or real money.
3. **Zero Secrets in Code:**
   - NEVER commit `.env` files, private keys, or wallet seed phrases.
   - NEVER embed private keys in frontend bundles or client-facing code.
4. **Enforce Payment Boundaries:**
   - Verify registered price, network identifier (`eip155:84532`), token address, and seller `payTo` address before issuing payment.
   - Atomic budget reservation: Check budget *before* payment initiation.
   - Replay protection & idempotency: Cache and verify request nonces/hashes.

---

## 4. Code Quality & Testing
1. **Read Before Writing:** Always read [docs/API_CONTRACTS.md](file:///c:/Users/Rehan/OneDrive/Desktop/hacakathon/kurukshetradyp/AgentMarketPlace/docs/API_CONTRACTS.md), [docs/ARCHITECTURE.md](file:///c:/Users/Rehan/OneDrive/Desktop/hacakathon/kurukshetradyp/AgentMarketPlace/docs/ARCHITECTURE.md), and [docs/SECURITY.md](file:///c:/Users/Rehan/OneDrive/Desktop/hacakathon/kurukshetradyp/AgentMarketPlace/docs/SECURITY.md) before writing code.
2. **Type Hints & Schemas:** Use Python type hints, Pydantic v2 models, and explicit error handlers everywhere.
3. **Test With Every PR:** Every feature PR must include dedicated pytest unit/integration tests in `backend/tests/`.
4. **Preserve Working Code:** Ensure the backend remains runnable and `GET /health` continues to return 200 OK.
