# SECURITY & PAYMENT SAFETY SPECIFICATION — DI-06

This document specifies the non-negotiable security boundaries and payment integrity rules governing the **Pay-Per-Call Agent Economy**.

---

## 1. Core Cryptographic & Network Rules

1. **Official x402 v2 Protocol Standards:**
   - All micropayments MUST follow the official x402 v2 payment protocol.
   - Do NOT implement custom, ad-hoc payment mechanisms or fake simulation layers.
2. **Network & Token Lockdown:**
   - **Allowed Network:** Base Sepolia testnet ONLY. CAIP-2 Identifier: `eip155:84532`.
   - **Allowed Token:** Base Sepolia USDC (`0x036CbD53842c5426634e7929541eC2318f3dCF7e`).
   - Any payment challenge specifying a different chain ID or token address must be immediately rejected with status `refused`.
3. **Strict Recipient Address (`payTo`) Verification:**
   - The recipient address in the HTTP 402 challenge must match the pre-registered `pay_to` address of the seller in the Service Registry.
   - Mitigates Man-in-the-Middle (MITM) attacks diverting funds to rogue addresses.

---

## 2. Budget Enforcement & Concurrency Safety

4. **Atomic Budget Reservation:**
   - Before signing any payment authorization, the buyer must reserve the requested funds using an atomic reservation lock (`BudgetManager.reserve()`).
   - Parallel tasks (minimum 3 concurrent worker threads/tasks supported) must never be able to race and overdraw the user's allocated task budget.
   - If an unspent reservation completes or fails prior to settlement, the reserved funds must be atomically returned to the available balance.
5. **Integer Base Unit Arithmetic:**
   - Floating-point representations (`float`, `double`) are strictly prohibited in budget and payment calculations.
   - USDC uses 6 decimals: `1.000000 USDC = 1,000,000 base units`.
   - All internal arithmetic, balances, prices, and reservations MUST operate on standard 64-bit integers (`int`).
6. **Maximum Service Price Ceiling:**
   - Configurable per-request maximum (default `0.05 USDC` / `50,000 base units`).
   - Prevents malicious or compromised seller agents from quoting exorbitant prices to drain buyer wallets.

---

## 3. Replay Protection & Idempotency

7. **Nonce Verification & Protocol Replay Protection:**
   - Every payment challenge must include a unique server-generated nonce or deadline.
   - The client tracks used nonces and validates that nonces cannot be re-used across distinct HTTP requests.
8. **Request Idempotency:**
   - All state-altering buyer requests and seller calls must include an `Idempotency-Key` header (UUIDv4).
   - The seller's payment verifier records idempotency keys. If a request is received with an identical key, it returns the cached result without charging the buyer a second time.
9. **No Blind Retries on Uncertain Settlement:**
   - If an HTTP request times out after the payment authorization has been dispatched, the buyer MUST NOT blindly re-issue a second payment.
   - The buyer must first query the facilitator or the seller's idempotency endpoint to reconcile the status of the in-flight authorization.

---

## 4. Verification & Audit Truthfulness

10. **Schema Validation Before "Paid" State:**
    - An HTTP 200 response with settlement proof DOES NOT automatically qualify as a complete success.
    - The buyer must validate the returned payload against the seller's registered JSON schema (`output_schema`).
    - If the seller returns invalid, truncated, or malformed data after payment settlement, the ledger MUST record:
      - `status = "paid output rejected"`
      - Seller reputation penalty must be applied.
11. **Cryptographic Settlement Proof:**
    - An HTTP 200 status code DOES NOT prove on-chain settlement.
    - True settlement requires either:
      - A valid Base Sepolia transaction hash (`tx_hash`) confirmed on-chain, or
      - A signed settlement receipt from the official x402 facilitator.
12. **Verifiable Uncharged Failures:**
    - A transaction may only be marked `failed and not charged` if the payment authorization was never settled with the facilitator or on-chain.

---

## 5. Secrets Management & Operational Hygiene

13. **Zero Private Keys in Frontend:**
    - The web dashboard runs purely in read-only client mode or communicates through authenticated backend APIs.
    - Private keys, seed phrases, and signer instances must NEVER be imported, bundled, or accessible in browser JavaScript/TypeScript.
14. **No Committed Credentials:**
    - `.env` files, `.key`, `.wallet`, and testnet private keys must remain excluded via `.gitignore`.
    - Only `.env.example` with blank placeholders is committed.
