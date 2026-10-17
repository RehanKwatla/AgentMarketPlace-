# AGENTICA — PHASE 7 FRONTEND PAYMENT TRUTH AND OPERATOR UX

**Phase:** 7.5 Frontend Payment Trust, Explorer Links, and Operator UX  
**Date:** 2026-10-17  
**Module Owner:** Member 4 (`frontend/`, `backend/ledger/`, `backend/database/`)  
**Evidence Classification:** VERIFIED BY AUTOMATED TESTS, VERIFIED BY CODE INSPECTION & BUILD  
**Status:** **ACCEPTED**  

---

## 1. Executive Summary

This evaluation audits the AGENTICA operator frontend (React + Vite + TypeScript) for payment evidence honesty, cryptographic link validity, and precise state representation. The frontend production build was executed and verified without TypeScript or bundler errors:

```
> tsc && vite build
✓ 1975 modules transformed.
dist/index.html                   1.01 kB │ gzip:  0.58 kB
dist/assets/index-CBlva542.css   41.01 kB │ gzip:  7.43 kB
dist/assets/index-5BQlKE4Z.js   350.51 kB │ gzip: 93.91 kB
✓ built in 3.25s
Exit Code: 0
```

---

## 2. Payment Evidence Labeling & Truthfulness Matrix

The UI maintains strict semantic distinctions between simulated, facilitator-backed, and verified on-chain settlements via `frontend/src/components/ReputationBadge.tsx`:

| Backend State | UI Label | Visual Token | Semantics |
|---|---|---|---|
| `verified on-chain` | **Verified On-Chain** | Solid White Dot / High-Contrast Border | Requires verified on-chain transaction receipt |
| `verified facilitator receipt` | **Verified Facilitator Receipt** | Subdued Gray Dot / Neutral Border | Facilitator-signed off-chain payment authorization |
| `simulated` / `simulated settlement` | **Simulated Settlement** | Subdued Slate Dot / Slate Border | Local offline mock/test run |
| `paid` / `completed` | **Verified Paid / Settled** | Neutral Gray Dot | Settled seller payment |
| `paid output rejected` | **Paid / Output Rejected** | Amber/Gray Alert | Seller was paid, but output failed validation |
| `pending reconciliation` | **Pending Reconciliation** | Pulsing White Dot | Suspense state; outcome pending verification |
| `refused` | **Refused Before Payment** | Muted Slate Dot | Blocked prior to budget debit or payment |
| `failed and not charged` | **Failed / Not Charged** | Dark Slate Dot | Execution aborted without charging buyer |

---

## 3. Blockchain Explorer Link Generation Verification

In `frontend/src/types/index.ts`:
```typescript
export const isValidBaseSepoliaTxHash = (hash: string | null | undefined): boolean => {
  if (!hash) return false;
  // Strict 66-character hex string starting with 0x (Base Sepolia transaction hash)
  // Synthetics like rec_auth_..., simulated_..., mock_... evaluate to false
  return /^0x[0-9a-fA-F]{64}$/.test(hash.trim());
};

export const getBaseSepoliaExplorerUrl = (hash: string | null | undefined): string | null => {
  if (!isValidBaseSepoliaTxHash(hash)) return null;
  return `https://sepolia.basescan.org/tx/${hash?.trim()}`;
};
```

### Invariants Enforced:
1. **Zero Fake Explorer Links:** Synthetic IDs (`rec_auth_...`, `sim_...`, mock strings) evaluate to `false` and return `null`.
2. **Strict Regex:** Explorer links are constructed only for strict 66-character hex hashes matching `/^0x[0-9a-fA-F]{64}$/`.
3. **Modal Formatting:** In `LedgerDetailModal.tsx`:
   - If an explorer link exists, it displays an outbound link to `https://sepolia.basescan.org/tx/<hash>`.
   - If `record.tx_hash` is a facilitator receipt (`rec_...`), it is explicitly labeled `Facilitator Receipt ID:` with plain-text display and **no** fake explorer link.

---

## 4. Integer Base Unit Formatting

All monetary values rendered in the UI (budget, spend, step costs) originate from backend integer base units (`1 USDC = 1,000,000 base units`). Floating-point arithmetic on monetary values is prohibited in backend logic, and the UI displays fixed 6-decimal string representations (e.g. `0.009000 USDC`).

---

## 5. Audit Verdict

| UX / Trust Control | Requirement | Observed Status |
|---|---|---|
| Synthetic vs Live Separation | Never render synthetic receipt as on-chain | **PASS** |
| Explorer Link Guard | Link only strict 0x[a-fA-F0-9]{64} hashes to BaseScan | **PASS** |
| Status Differentiation | Distinct badges for facilitator, on-chain, simulated, rejected | **PASS** |
| TypeScript Validation | Clean type checking and bundling | **PASS** (1,975 modules in 3.25s) |

**Phase 7 Gate 5 Status:** **ACCEPTED**.
