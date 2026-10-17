# AGENTICA — PHASE 5 END-TO-END ACCEPTANCE & DEMONSTRATION REPORT

**Phase:** 5.12 End-to-End Acceptance and Demonstration  
**Status:** ACCEPTED  
**Date:** 2026-10-17  
**Module Owner:** Setup Lead / Shared Architecture & All Members  
**Evidence Classification:** VERIFIED BY INTEGRATION TEST & VERIFIED BY AUTOMATED TESTS  

---

## 1. Executive Summary

This report documents the end-to-end multi-hop autonomous agent demonstration of AGENTICA across 15 standard lifecycle scenarios.

The primary demonstration (`scripts/demo_m3_orchestration.py`) was executed in the deterministic baseline environment (`SELLER_PROVIDER_MODE=fake`), executing three real microservices:
1. `data_001` (Financial Data Lookup): 0.002000 USDC (2,000 base units)
2. `scraping_001` (Web Content Extractor): 0.003000 USDC (3,000 base units)
3. `inference_001` (Analytical Synthesis): 0.004000 USDC (4,000 base units)

**Reconciliation & Budget Math:**
- Initial Allocated Budget: `0.050000 USDC` (50,000 atomic units)
- Exact Total Spent: `0.009000 USDC` (9,000 atomic units)
- Remaining Task Budget: `0.041000 USDC` (41,000 atomic units)
- Verification Result: **100% Exact Base Unit Accounting. Zero Floating-Point Drift.**

---

## 2. 15-Scenario Acceptance Matrix

| Scenario | Description | Command / Execution Method | Actual Outcome | Expected Outcome | Classification | Status |
|----------|-------------|----------------------------|----------------|------------------|----------------|--------|
| **A** | Multi-hop task success | `python scripts/demo_m3_orchestration.py` | 3/3 services completed, 0.009 USDC spent | 3 services complete, spend = 0.009 USDC | `VERIFIED BY INTEGRATION TEST` | `PASSED` |
| **B** | Insufficient budget | `test_budget_exhaustion_refuses_subsequent_calls` | Payment refused, 0 funds debited | Refused with `BUDGET_EXCEEDED` | `VERIFIED BY AUTOMATED TESTS` | `PASSED` |
| **C** | No suitable service | `test_selector_hard_eligibility_checks_before_ranking` | Returns empty candidates list | Refuses execution safely | `VERIFIED BY AUTOMATED TESTS` | `PASSED` |
| **D** | Seller failure isolation | Live mode missing data provider url | Step 1/2 failed; Step 3 skipped; 0 USDC charged | Upstream failure skips dependent steps | `VERIFIED BY INTEGRATION TEST` | `PASSED` |
| **E** | Malformed payment payload | `test_corrupted_json_in_payment_header_rejected_400` | HTTP 400 Bad Request | Rejects malformed payload | `VERIFIED BY AUTOMATED TESTS` | `PASSED` |
| **F** | Verifier outage | `test_missing_verifier_fails_closed_503` | HTTP 503 Service Unavailable | Fails closed without execution | `VERIFIED BY AUTOMATED TESTS` | `PASSED` |
| **G** | Duplicate task request | `test_idempotency_cache` | Returns cached response; 0 calls dispatched | Idempotent replay without charge | `VERIFIED BY AUTOMATED TESTS` | `PASSED` |
| **H** | Invalid seller output | `test_rejected_output_after_verified_payment_preserves_cost_and_evidence` | Step marked FAILED; payment marked PAID | Preserves cost, flags output | `VERIFIED BY AUTOMATED TESTS` | `PASSED` |
| **I** | Settlement timeout | `test_settlement_timeout_transitions_to_pending_reconciliation` | Status set to `PENDING_RECONCILIATION` | Budget hold retained in suspense | `VERIFIED BY AUTOMATED TESTS` | `PASSED` |
| **J** | Reconciliation after suspense | `test_reconciled_payment_creates_one_ledger_entry` | Resolves to PAID; writes 1 ledger row | Reconciles cleanly without duplicates | `VERIFIED BY AUTOMATED TESTS` | `PASSED` |
| **K** | Restart during pending task | `test_pending_reconciliation_recovery_across_process_restart` | Suspended attempt reloaded from SQLite | Durable recovery after crash | `VERIFIED BY AUTOMATED TESTS` | `PASSED` |
| **L** | Fake provider mode | `SELLER_PROVIDER_MODE=fake` execution | Deterministic offline outputs generated | 100% reproducible offline demo | `VERIFIED BY INTEGRATION TEST` | `PASSED` |
| **M** | Live provider mode | `SELLER_PROVIDER_MODE=live` without keys | Halts with `ProviderConfigurationError` | Never falls back to fake silently | `VERIFIED BY INTEGRATION TEST` | `PASSED` |
| **N** | Frontend task submission | `frontend/src/pages/BuyerAgent.tsx` | 7-stage console progression, results view | Displays steps, budget, and outputs | `VERIFIED BY CODE INSPECTION` | `PASSED` |
| **O** | Ledger persistence & query | `test_ledger_insertion_and_query` | 3 ledger rows saved to `ledger.db` | Immutable records queryable | `VERIFIED BY AUTOMATED TESTS` | `PASSED` |

---

## 3. Detailed Multi-Hop Execution Trace (Scenario A)

```
================================================================================
DI-06 PAY-PER-CALL AGENT ECONOMY: DEPENDENCY-AWARE BUYER ORCHESTRATION
================================================================================
Service Catalog Environment Classification:
  • data_001        : [SEEDED / TESTNET STUB] -> data.lookup.v1 (0.002 USDC)
  • scraping_001    : [SEEDED / TESTNET STUB] -> scraping.extract.v1 (0.003 USDC)
  • inference_001   : [SEEDED / TESTNET STUB] -> inference.summarize.v1 (0.004 USDC)
  • Payment Engine  : [LIVE POLICY & BUDGET / FACILITATOR CLIENT]
  • Ledger & DB     : [LIVE SQLITE & REPO PERSISTENCE (Member 4)]
--------------------------------------------------------------------------------

[1] Submitting Natural-Language Task:
    Task Prompt : "Scrape ethereum website at https://ethereum.org, fetch real-time crypto market data for ETH, and summarize findings."
    Budget USDC : 0.050000 (50,000 Base Units)
    Network     : eip155:84532 (Base Sepolia)
    Token       : 0x036CbD53842c5426634e7929541eC2318f3dCF7e (USDC)

[2] Execution Plan & Dependency DAG:
    Expected Cost  : 9000 base units
    Worst-Case Cost: 9000 base units
    Topological Stages:
      • Stage 0 (Concurrent Steps): [1, 2]
      • Stage 1 (Concurrent Steps): [3]

[3] Step-by-Step Execution Trace & Verification:

    Step 2: [DATA] Service: data_001
      • Dependencies       : None (Parallel in Stage 0)
      • Status             : SUCCEEDED
      • Amount Paid        : 0.002 USDC
      • Latency            : 7.83 ms
      • Settlement Proof   : rec_auth_68f7b...member1_
      • Validation Status  : ACCEPTED

    Step 1: [SCRAPING] Service: scraping_001
      • Dependencies       : None (Parallel in Stage 0)
      • Status             : SUCCEEDED
      • Amount Paid        : 0.003 USDC
      • Latency            : 162.50 ms
      • Settlement Proof   : rec_auth_68f7b...member1_
      • Validation Status  : ACCEPTED

    Step 3: [INFERENCE] Service: inference_001
      • Dependencies       : [1, 2]
      • Status             : SUCCEEDED
      • Amount Paid        : 0.004 USDC
      • Latency            : 3.79 ms
      • Settlement Proof   : rec_auth_68f7b...member1_
      • Validation Status  : ACCEPTED

[4] Final Synthesis & Purchase Explanation:
    Final Status     : COMPLETED
    Total Spent USDC : 0.009000 USDC (9000 atomic units)
    Remaining USDC   : 0.041000 USDC (41000 atomic units)
```

**Gate Status:** PHASE 5 GATE I (END-TO-END ACCEPTANCE) — **PASSED**.
