# AGENTICA — PHASE 6 CONTROLLED BASE SEPOLIA VERIFICATION GATE

**Phase:** 6.7 Controlled Base Sepolia Verification Gate  
**Status:** **BLOCKED BY AUTHORIZATION / NOT RUN**  
**Date:** 2026-10-17  
**Module Owner:** Member 1 (`backend/payments/`) & Setup Lead  
**Evidence Classification:** NOT RUN (Awaiting Explicit User Authorization)  

---

## 1. Executive Summary

In strict accordance with **Rule 0.1 (Financial & Git Safety)** and **Section 6.7 of the Phase 6 Plan**, live blockchain transactions on Base Sepolia (`eip155:84532`) were **deliberately NOT broadcast** during Phase 6 execution.

The on-chain verification engine (`SettlementVerifier` in `backend/payments/settlement.py`) was fully audited against Base Sepolia RPC specifications using offline tests and mock receipts. The live transaction broadcast gate remains in:
`BLOCKED BY AUTHORIZATION / NOT RUN` status.

---

## 2. Stage A — Read-Only Preparation & Configuration Audit

| Parameter | Configured Value | Verification Source |
|---|---|---|
| **Network CAIP-2** | `eip155:84532` | `backend.shared.constants.NETWORK_BASE_SEPOLIA` |
| **Chain ID** | `84532` | Base Sepolia Testnet |
| **RPC Endpoint** | `https://sepolia.base.org` | Official Base Sepolia JSON-RPC |
| **Token Contract** | `0x036CbD53842c5426634e7929541eC2318f3dCF7e` | Official Base Sepolia USDC |
| **Token Decimals** | `6` (1 USDC = 1,000,000 base units) | Standard ERC-20 |
| **Facilitator Endpoint** | `https://facilitator.x402.org` | Official x402 Facilitator |

---

## 3. Stage B — Authorization Checkpoint

Before any live transaction may be executed:
1. **Explicit User Mandate:** The user must explicitly prompt: `"Authorize live Base Sepolia testnet settlement"`.
2. **Funded Testnet Account:** A Base Sepolia address must be provisioned with testnet ETH (gas) and testnet USDC.
3. **Secure Environment Ingestion:** `BUYER_PRIVATE_KEY` must be set in local `.env`. **Private keys must never be shared in AI chat prompts.**
4. **Controlled Spend Limit:** Single execution capped at 0.002000 USDC (`data_001`).

---

## 4. Stage C — Post-Authorization Verification Procedure

Upon receiving user authorization, `scripts/verify_base_sepolia_live.py` executes:
1. Query Base Sepolia JSON-RPC for `eth_getTransactionReceipt(tx_hash)`.
2. Confirm `status == "0x1"`.
3. Decode ERC-20 `Transfer(address,address,uint256)` event logs.
4. Validate recipient matches seller `payTo` address and value matches exact atomic units.
5. Record confirmed settlement to Member 4's ledger.
6. Verify duplicate submissions do not create duplicate ledger rows.

---

## 5. Certification of Non-Broadcast

- **Zero on-chain transactions were broadcast during Phase 6.**
- **Zero testnet or mainnet funds were spent.**
- **Zero fake transaction hashes were fabricated.**
- **Offline and simulated demonstration evidence was verified with zero false claims.**

---

## 6. Path 1 — Read-Only Live RPC Verification

**Date & UTC Timestamp:** `2026-10-17T02:12:46Z`  
**Repository Branch & HEAD Observed:** `M2` (`0beeb33`)  
**Public RPC Endpoint:** `https://sepolia.base.org`  
**HTTP Protocol Connectivity:** `200 OK` (JSON-RPC 2.0 transport)  
**Evidence Classification:** `VERIFIED IN LIVE ENVIRONMENT` (Read-Only Connectivity Only)  

### 6.1 Live JSON-RPC Query Results

| # | Check / Method | Parameter / Selector | Raw Hex Response | Decoded Value | Expected | Result | Evidence Classification |
|---|---|---|---|---|---|---|---|
| 1 | `eth_chainId` | `[]` | `0x14a34` | `84532` | `84532` (`eip155:84532`) | **PASS** | `VERIFIED IN LIVE ENVIRONMENT` |
| 2 | `eth_blockNumber` | `[]` | `0x2dfbd5f` | `48,217,439` | Valid non-negative integer | **PASS** | `VERIFIED IN LIVE ENVIRONMENT` |
| 3 | `eth_getBlockByNumber` | `["0x2dfbd5f", false]` | Hash: `0x0628237f5a9933f7c156dcd2ec27be51564f56b5ee258eb2e93e9ce48575bedb` | Block time: `2026-10-17T02:12:46Z` | Matching block number | **PASS** | `VERIFIED IN LIVE ENVIRONMENT` |
| 4a | `eth_call` (`decimals()`) | `0x313ce567` | `0x0000000000000000000000000000000000000000000000000000000000000006` | `6` | `6` (USDC atomic units) | **PASS** | `VERIFIED IN LIVE ENVIRONMENT` |
| 4b | `eth_call` (`symbol()`) | `0x95d89b41` | `0x00...20...045553444300...` | `"USDC"` | `"USDC"` | **PASS** | `VERIFIED IN LIVE ENVIRONMENT` |
| 4c | `eth_call` (`name()`) | `0x06fdde03` | `0x00...20...045553444300...` | `"USDC"` | Valid non-empty string | **PASS** | `VERIFIED IN LIVE ENVIRONMENT` |
| 5 | Resilience (`eth_chainId`) | `[]` (req #2) | `0x14a34` | `84532` | Consistent chain ID | **PASS** | `VERIFIED IN LIVE ENVIRONMENT` |

### 6.2 Target Contract Verification
- **Configured Address:** `0x036CbD53842c5426634e7929541eC2318f3dCF7e`
- **Address Verification:** Confirmed matching official Base Sepolia testnet USDC contract deployment documented by Base / Circle documentation.
- **RPC Contract Responses:** Responded with exact ERC-20 metadata (`decimals=6`, `symbol="USDC"`, `name="USDC"`).

### 6.3 Safety & Non-Financial Verification Confirmation
- **All requests performed were strictly read-only JSON-RPC queries (`eth_chainId`, `eth_blockNumber`, `eth_getBlockByNumber`, `eth_call`).**
- **Zero transactions were broadcast.**
- **Zero wallets were generated or imported.**
- **Zero private keys were created, accessed, or stored.**
- **Zero testnet or mainnet funds were spent or transferred.**
- **Zero paid external provider APIs were invoked.**
- **Zero Git mutations occurred.**

### 6.4 Status Boundary & Explicit Settlement Disclaimer
- **Read-Only RPC Connectivity:** **VERIFIED IN LIVE ENVIRONMENT**
- **USDC Contract Metadata Readability:** **VERIFIED IN LIVE ENVIRONMENT**
- **LIVE BASE SEPOLIA PAYMENT SETTLEMENT STATUS:** **BLOCKED BY AUTHORIZATION / NOT RUN**

*Disclaimer:* Successful read-only RPC connectivity and contract metadata queries prove that the application environment can communicate with the live Base Sepolia testnet node. They **DO NOT** prove that payment transactions have been signed, broadcast, or settled on-chain. Live payment settlement remains strictly held pending explicit user authorization and provision of funded testnet credentials.

