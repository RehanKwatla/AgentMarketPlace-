# MEMBER 1: PAYMENT & SECURITY ENGINE (`backend/payments/`)

**Assigned Owner:** Member 1 (Payment & Security Engineer)  
**Assigned Git Branch:** `feature/payments`  
**Status:** `[DEFINED INTERFACES AWAITING IMPLEMENTATION]`

---

## 📋 Responsibilities Checklist

- [ ] **Official x402 v2 SDK Integration:** Verify installed `x402` package API and build client/verifier wrappers.
- [ ] **BuyerPaymentClient (`interfaces.py`):** Implement challenge parser, EIP-712 payment authorization signer with `eth-account`.
- [ ] **SellerPaymentVerifier (`interfaces.py`):** Implement 402 challenge issuer and facilitator settlement verifier.
- [ ] **Payment Policy Verification (`policy.py`):**
  - Verify network matches `eip155:84532`.
  - Verify token address matches Base Sepolia USDC.
  - Verify seller `payTo` matches registered recipient address.
  - Verify quote matches registered catalog price and does not exceed `max_price_usdc`.
- [ ] **Atomic Budget Reservation (`budget.py`):**
  - Concurrency-safe budget reservation using integer base units.
  - Minimum 3 concurrent requests supported without race conditions.
  - Automatic balance release on failure/rejection.
- [ ] **Replay Protection & Idempotency (`idempotency.py`):**
  - Nonce generation and single-use cache.
  - Request hash / idempotency key caching.
- [ ] **Settlement Verification (`settlement.py`):**
  - Real settlement proof tracking with Facilitator or Base Sepolia RPC.
  - Strict rule: HTTP 200 does NOT prove settlement without on-chain/facilitator evidence.
- [ ] **Payment Security Tests (`backend/tests/test_payments.py`, `test_budget.py`, `test_replay.py`):**
  - Unit test all policy checks, budget overdraw edge cases, and replay detections.

---

## 🚫 Critical Constraints
- **NO MOCKED TRANSACTION HASHES:** Never emit fake hashes like `"0x123...fake"`.
- **NO FAKE PAYMENT SUCCESS:** Return actual protocol states or clearly raised exceptions.
- **NEVER COMMIT PRIVATE KEYS:** All tests must use ephemeral test keys or mocks of the signer.
