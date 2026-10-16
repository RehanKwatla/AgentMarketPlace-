# AGENTS.md — CODE OF CONDUCT & BINDING RULES FOR ALL AI AGENTS & DEVELOPERS

Welcome to the **DI-06: Pay-Per-Call Agent Economy** hackathon project.
All AI models (Gemini, Claude, GPT, Antigravity subagents), pair programmers, and human contributors collaborating on this codebase **MUST** adhere strictly to the following binding rules.

---

## 1. Scope & Module Boundary Rules

1. **Strict Ownership by Feature Branch:**
   - **Member 1 (`feature/payments`):** Owns `backend/payments/`.
   - **Member 2 (`feature/sellers`):** Owns `backend/sellers/`.
   - **Member 3 (`feature/buyer-registry`):** Owns `backend/buyer/` and `backend/registry/`.
   - **Member 4 (`feature/dashboard-ledger`):** Owns `backend/ledger/`, `backend/database/`, `frontend/`, and deployment docs.
   - **Setup Lead (`main`):** Owns `backend/shared/`, `backend/main.py`, root configs, and `docs/API_CONTRACTS.md`.
2. **Never Overwrite Code in Unrelated Modules:**
   - If an agent is assigned to `backend/sellers/`, it must NOT edit `backend/payments/` or `backend/buyer/`.
3. **No Unilateral Changes to Shared Interfaces:**
   - `backend/shared/schemas.py`, `backend/shared/constants.py`, and `docs/API_CONTRACTS.md` are the single source of truth.
   - Changes require coordination with the Setup Lead and other affected team members.

---

## 2. Integrity & Truthfulness Rules (Zero Fabrication)

1. **Never Fabricate Payment Evidence:**
   - **DO NOT** create dummy responses claiming successful payment unless verified against the actual x402 payment lifecycle or genuine testnet receipt.
   - **DO NOT** mock fake transaction hashes (e.g., `0x1234...fake`).
   - HTTP 200 DOES NOT prove settlement without on-chain or facilitator evidence.
2. **Honesty on Feature Completeness:**
   - Always label code explicitly:
     - `[IMPLEMENTED]` — fully functional, tested, and verifiable.
     - `[DEFINED INTERFACE]` — abstract base class or protocol awaiting implementation.
     - `[STUB]` — temporary scaffold returning mock/501 Not Implemented.
3. **Report Actual Test Results:**
   - Run tests using `pytest` or `python scripts/run_tests.py` and report true stdout/stderr outputs.
   - Never claim tests passed when they failed or were not executed.

---

## 3. Cryptographic, Network & Payment Safety Rules

1. **Official x402 v2 Protocol Standards:**
   - Do NOT invent a custom replacement for x402 v2.
   - Use official x402 v2 HTTP headers:
     - `X-402-Requirement`: Emitted with HTTP 402 by seller.
     - `X-402-Payment-Payload`: Sent with HTTP 200 re-request by buyer.
     - `X-402-Settlement-Proof`: Returned with HTTP 200 by seller.
2. **Testnet Lockdown:**
   - Network identifier MUST be `eip155:84532` (Base Sepolia).
   - Token MUST be Base Sepolia USDC (`0x036CbD53842c5426634e7929541eC2318f3dCF7e`).
   - NEVER use mainnet funds, real money, or mainnet chain IDs.
3. **Zero Secrets in Code:**
   - NEVER commit `.env` files, private keys, or wallet seed phrases.
   - NEVER embed private keys in frontend bundles or client-facing code.
4. **Enforce Payment Safety Boundaries:**
   - Verify registered price, network, token, and seller `payTo` address before issuing payment.
   - Atomic budget reservation: Check and lock budget *before* payment initiation.
   - Replay protection & idempotency: Cache nonces and verify idempotency keys.
   - Integer base units only: All internal USDC arithmetic MUST use integers (`1 USDC = 1,000,000 base units`). Floating-point money math is strictly forbidden.

---

## 4. Code Quality & Engineering Standards

1. **Read Contracts Before Writing Code:**
   - Always review [`docs/API_CONTRACTS.md`](docs/API_CONTRACTS.md), [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), and [`docs/SECURITY.md`](docs/SECURITY.md) before writing code.
2. **Type Hints & Schemas:**
   - Use Python type hints, Pydantic v2 models, and explicit error handlers everywhere.
3. **Preserve Working Functionality:**
   - Ensure the backend remains runnable and `GET /health` continues to return `200 OK`.
4. **Test With Every PR:**
   - Every feature addition must include dedicated pytest unit/integration tests in `backend/tests/`.

---

## 5. Git & Collaboration Etiquette

1. **Branch Hygiene:** Commit only to your assigned feature branch.
2. **No Force Pushes:** Never run `git push --force` on shared branches.
3. **Keep Commits Clean:** Make small, clear, atomic commits with conventional commit messages (e.g., `feat(payments): ...`, `fix(sellers): ...`).
4. **Pull Before Push:** Always fetch and rebase/merge `origin/main` before opening a pull request.
