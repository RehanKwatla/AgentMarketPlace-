# AGENTICA — PHASE 6 DEMONSTRATION & FAILURE RUNBOOK

**Phase:** 6.8 Reproducible Demo and Failure Scenarios  
**Status:** **ACCEPTED**  
**Date:** 2026-10-17  
**Module Owner:** Setup Lead / Shared Architecture & All Members  
**Evidence Classification:** VERIFIED BY INTEGRATION TEST & VERIFIED BY AUTOMATED TESTS  

---

## 1. Executive Summary

This runbook provides reproducible, judge-facing execution procedures for AGENTICA's default 3-hop multi-service demonstration and key failure isolation scenarios. All demonstrations run offline in deterministic fake mode without requiring live blockchain transactions or paid vendor API quota.

---

## 2. Default End-to-End Demonstration (3-Hop Workflow)

### 2.1 Execution Procedure
```bash
# Set provider mode to deterministic fake simulation
$env:SELLER_PROVIDER_MODE="fake"  # Windows PowerShell
# On Linux/macOS: export SELLER_PROVIDER_MODE="fake"

# Execute autonomous orchestration demonstration
python scripts/demo_m3_orchestration.py
```

### 2.2 Expected Terminal Output & Verification Points
```
================================================================================
DI-06 PAY-PER-CALL AGENT ECONOMY: DEPENDENCY-AWARE BUYER ORCHESTRATION
================================================================================
[1] Submitting Natural-Language Task:
    Task Prompt : "Scrape ethereum website at https://ethereum.org, fetch real-time crypto market data for ETH, and summarize findings."
    Budget USDC : 0.050000 (50,000 Base Units)
    Network     : eip155:84532 (Base Sepolia)
    Token       : 0x036CbD53842c5426634e7929541eC2318f3dCF7e (USDC)

[2] Execution Plan & Dependency DAG:
    Expected Cost  : 9000 base units
    Topological Stages:
      • Stage 0 (Concurrent Steps): [1, 2]
      • Stage 1 (Concurrent Steps): [3]

[3] Step-by-Step Execution Trace:
    Step 1: [SCRAPING] scraping_001 -> SUCCEEDED | Paid: 0.003 USDC | Status: ACCEPTED
    Step 2: [DATA]     data_001     -> SUCCEEDED | Paid: 0.002 USDC | Status: ACCEPTED
    Step 3: [INFERENCE] inference_001 -> SUCCEEDED | Paid: 0.004 USDC | Status: ACCEPTED

[4] Member 4 Persistence & Ledger Audit:
    Total Audit Records in Ledger: 3 entries recorded

[5] Final Synthesis & Purchase Explanation:
    Final Status     : COMPLETED
    Total Spent USDC : 0.009000 USDC (9000 atomic units)
    Remaining USDC   : 0.041000 USDC (41000 atomic units)
================================================================================
DEMO RUN COMPLETED SUCCESSFULLY: 100% SPECIFICATION ADHERENCE VERIFIED
================================================================================
```

---

## 3. Failure Isolation Scenarios

### Scenario 1: Insufficient Budget Refusal Before Payment
- **Description:** Task spending limit is lower than service price.
- **Verification Command:** `python -m pytest backend/tests/test_budget.py::test_budget_overdraw_prevention -v`
- **Safety Property:** Payment engine refuses payment with `BUDGET_EXCEEDED` before dispatching network call; zero funds are locked or transferred.

### Scenario 2: Upstream Failure Skips Dependent Calls
- **Description:** Upstream data or scraping step fails or times out.
- **Verification Command:** `python -m pytest backend/tests/test_buyer_dependency_execution.py::test_failed_upstream_dependency_skips_dependent_call -v`
- **Safety Property:** Downstream inference step transitions to `SKIPPED`; zero funds reserved, zero payments initiated for unfulfilled dependent work.

### Scenario 3: Ambiguous Payment Halts Fallback Execution
- **Description:** Primary call settlement times out (`PENDING_RECONCILIATION`).
- **Verification Command:** `python -m pytest backend/tests/test_buyer_dependency_execution.py::test_ambiguous_payment_outcome_never_runs_fallback -v`
- **Safety Property:** Automated fallback is strictly blocked while prior settlement outcome is uncertain, preventing double charging.

---

## 4. Certification

The demo workflow is deterministic, reproducible, and verifiable locally with zero external financial or cloud dependencies.

**Gate Status:** PHASE 6 GATE E (REPRODUCIBLE DEMO RUNBOOK) — **PASSED**.
