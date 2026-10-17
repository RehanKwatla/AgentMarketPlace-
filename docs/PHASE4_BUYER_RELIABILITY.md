# AGENTICA — PHASE 4 BUYER ORCHESTRATION & RELIABILITY REPORT
**Document:** `docs/PHASE4_BUYER_RELIABILITY.md`  
**Date:** 17 October 2026  
**Auditor:** Member 3 (Buyer & Registry Integration Engineer)  
**Status:** COMPLETE (Stage 4 Master Plan)  
**Classification:** VERIFIED BY AUTOMATED TESTS & CODE INSPECTION  

---

## 1. Executive Summary

This report documents the verification of the Buyer Agent and Registry orchestration subsystem. The Buyer Agent decomposes natural-language objectives into directed acyclic graphs (DAGs), selects optimal services based on capability metadata, enforces strict budget reservations, bounds execution concurrency, validates seller outputs against registered Draft-7 schemas, and provides transparent purchase explanations.

---

## 2. Capability-Aware Service Discovery & Selection

Implemented in `backend/buyer/selector.py` and `backend/registry/service.py`:
- **Hard Eligibility Gates:**
  1. Service must be active (`is_active == True`).
  2. Estimated cost in integer base units must not exceed remaining task budget.
  3. Pre-execution constraints (e.g. `max_tokens`, `supported_schemes`) must satisfy step requirements.
- **Multi-Attribute Ranking Scoring:**
  ```python
  score = (
      w_reputation * reputation_score +
      w_success * success_rate -
      w_cost * normalized_cost -
      w_latency * normalized_latency +
      w_tag * tag_match_bonus
  )
  ```
- **Capability Metadata Support:** Inspects `service.capability_metadata` (tags, SLA p95 latency, payload byte limits, deterministic flags) to guarantee that chosen sellers match task constraints.

---

## 3. Deterministic Planning & DAG Validation

Implemented in `backend/buyer/planner.py` and `backend/buyer/plan_validator.py`:
- **Deterministic Capability Mapping:** Evaluates user prompt keywords and required categories (`data`, `scraping`, `inference`).
- **DAG Construction:** Emits `PlannedStep` records with explicit `step_id`, `service_id`, `depends_on`, `input_template`, and `estimated_cost_base_units`.
- **Validation Gates:**
  - Detects and rejects circular dependencies (cycle detection via Kahn's algorithm / DFS).
  - Validates that total estimated cost in base units is strictly `<= max_budget_atomic`.
  - Rejects DAGs containing references to missing or unregistered service IDs.

---

## 4. Execution Reliability, Dependency Gating & Concurrency

Implemented in `backend/buyer/service.py`:
- **Upstream Dependency Isolation:**
  If step B depends on step A (`depends_on = ["step_1"]`):
  - Step B will **never** execute if Step A fails, times out, or produces invalid output.
  - Step B is transitioned immediately to `FAILED_AND_NOT_CHARGED` without invoking payment or seller endpoints.
- **Concurrency Bounding:**
  - Tasks enforce `asyncio.Semaphore(max_concurrency)` (default 3, range 1–10).
  - Parallel branches in the DAG execute concurrently without exceeding the semaphore limit.
- **Output Validation & Safe Fallbacks:**
  - Output is validated against seller's registered Draft-7 JSON schema via `OutputValidator` (`backend/buyer/output_validator.py`).
  - If output fails schema validation, the call is marked `PAID_OUTPUT_REJECTED`, and the buyer attempts a designated fallback service or concludes the step gracefully.

---

## 5. Purchase Explanation & Authoritative Reconciliation

Implemented in `backend/buyer/explanation.py`:
- **Single Source of Truth:**
  - Does NOT rely on in-memory estimates or optimistic claims.
  - Queries `LedgerRepository` directly to obtain verified `amount_paid` and confirmed `tx_hash` identifiers.
- **Base Sepolia Explorer Deep Links:**
  Constructs verified Base Sepolia block explorer links for 66-character hexadecimal transaction hashes:
  ```
  https://sepolia.basescan.org/tx/0x...
  ```
  Unconfirmed facilitator receipts or simulation identifiers are clearly labeled as facilitator-verified or off-chain receipts.

---

## 6. Automated Test Coverage & Evidence

| Test Suite | Scenario Verified | Status |
|---|---|---|
| `test_buyer_dependency_execution.py` (8 tests) | Sequential DAG dependencies, input synthesis, upstream failure gating | **PASSED** |
| `test_buyer_orchestration_payment.py` (6 tests) | Routing through payment client, budget locks, concurrency limits | **PASSED** |
| `test_buyer_agent_multihop.py` (6 tests) | 3-step pipeline (Data -> Scraping -> Inference) end-to-end | **PASSED** |
| `test_purchase_explanation.py` (8 tests) | Verified spend summaries, ledger queries, explorer URL construction | **PASSED** |
| `test_output_validation_provenance.py` (5 tests) | Draft-7 output compliance, zero-hallucination provenance tagging | **PASSED** |
| `test_planner_validator.py` (11 tests) | DAG cycle detection, budget ceilings, capability ranking | **PASSED** |
