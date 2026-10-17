# AGENTICA — PHASE 5 LIVE TESTNET SETTLEMENT VERIFICATION GATE

**Phase:** 5.13 Optional Live Testnet Settlement Gate  
**Status:** BLOCKED BY AUTHORIZATION / NOT RUN  
**Date:** 2026-10-17  
**Module Owner:** Member 1 (`backend/payments/`) & Release Coordinator  
**Evidence Classification:** NOT RUN (Awaiting User Authorization)  

---

## 1. Executive Summary

In strict compliance with **Engineering Rule 5 (No Unauthorized Financial Operations)** and **Engineering Rule 6 (No Fabricated Evidence)**, live blockchain transactions on Base Sepolia (`eip155:84532`) were **deliberately NOT broadcast** during Phase 5 testing.

The system's on-chain settlement verification engine (`SettlementVerifier` in `backend/payments/settlement.py`) was fully audited and verified against Base Sepolia RPC specifications using offline mocks and simulated receipts.

**Current Live Settlement Gate Status:**  
`BLOCKED BY AUTHORIZATION / NOT RUN`

---

## 2. Pre-Flight Specification for Live Settlement

When authorized by the user, the following configuration parameters are required for live Base Sepolia settlement:

| Parameter | Authoritative Value | Source |
|-----------|---------------------|--------|
| **Network CAIP-2** | `eip155:84532` | `backend.shared.constants.NETWORK_BASE_SEPOLIA` |
| **Chain ID** | `84532` | Base Sepolia Testnet |
| **JSON-RPC Endpoint** | `https://sepolia.base.org` | Official Base Documentation |
| **Settlement Token** | `0x036CbD53842c5426634e7929541eC2318f3dCF7e` | Official Base Sepolia USDC Contract |
| **Token Decimals** | `6` (1 USDC = 1,000,000 base units) | Standard ERC-20 |
| **Facilitator Gateway** | `https://facilitator.x402.org` | Official x402 Protocol Facilitator |

---

## 3. Required Preconditions for Live Activation

Before live settlement can be triggered:
1. **User Authorization:** Explicit user consent provided in chat authorizing testnet gas and USDC spend.
2. **Funded Testnet Wallet:** A Base Sepolia wallet address with:
   - Sufficient Base Sepolia ETH for L2 transaction gas fees.
   - Sufficient Base Sepolia testnet USDC balance for service payments.
3. **Secure Key Ingestion:** The wallet private key must be injected via local `.env` (`BUYER_PRIVATE_KEY=0x...`). **Private keys must never be shared or pasted into AI chat prompts.**
4. **Environment Mode:** Set `ENVIRONMENT=staging` or `ENVIRONMENT=production` to disable synthetic test double bypasses in `SettlementVerifier`.

---

## 4. Live Settlement Verification Protocol (Post-Authorization)

Upon authorization, `SettlementVerifier.verify_full_settlement` executes the following on-chain checks:
1. Issues `eth_getTransactionReceipt(tx_hash)` to `https://sepolia.base.org`.
2. Asserts receipt `status == "0x1"`.
3. Decodes the receipt logs for the standard ERC-20 `Transfer` topic:
   `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef`.
4. Asserts log emitter equals `0x036CbD53842c5426634e7929541eC2318f3dCF7e`.
5. Asserts topic[2] (recipient) equals seller `payTo` address.
6. Asserts log data decodes to the exact service price in integer units (e.g., 2,000 units for `data_001`).

---

## 5. Certification of Non-Broadcast

- **Zero on-chain transactions were broadcast during Phase 5.**
- **Zero testnet or mainnet funds were transferred.**
- **Zero fake transaction hashes were generated or presented as real on-chain proofs.**
- **The baseline demonstration successfully utilized simulated facilitator receipts (`rec_auth_...`) without claiming false settlement.**
