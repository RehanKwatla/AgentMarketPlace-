# AGENTICA — PHASE 5 BUYER ORCHESTRATION RELIABILITY SPECIFICATION

**Phase:** 5.6 Buyer Orchestration Reliability  
**Status:** ACCEPTED  
**Date:** 2026-10-17  
**Module Owner:** Member 3 (`backend/buyer/`, `backend/registry/`)  
**Evidence Classification:** VERIFIED BY AUTOMATED TESTS & VERIFIED BY CODE INSPECTION  

---

## 1. Executive Summary

This document audits the reliability, deterministic execution, and dependency enforcement of the Buyer Agent orchestration engine. The buyer orchestrates multi-hop service execution across autonomous sellers using directed acyclic graphs (DAGs), capability matching, and budget management.

All 43 focused orchestration tests in `backend/tests/` passed (`43 passed in 1.20s`), demonstrating:
- Strict cycle and self-dependency rejection before execution.
- Automated topological ordering and dependency output propagation.
- Graceful degradation: upstream failures safely skip downstream dependent tasks without executing or charging them.
- Absolute prevention of unauthorized fallback execution when settlement is ambiguous.

---

## 2. Service Discovery & Capability-Aware Selection

In `backend/registry/service_catalog.py` and `backend/buyer/selector.py`:
- Services declare granular `CapabilityMetadata` including:
  - `domains` (e.g. `["finance", "market_intelligence"]`)
  - `supported_inputs` (e.g. `["company_ticker", "symbol"]`)
  - `output_fields` (e.g. `["company_name", "stock_price_usd"]`)
  - `rate_limit_per_minute`, `max_concurrency`, `sla_latency_p95_ms`
  - `offline_available` flag
- The Service Selector runs strict **hard-eligibility filters** before ranking:
  1. Service enabled state (`is_enabled == True`).
  2. Domain compatibility.
  3. Budget compliance ($price \le task\_budget$).
- Only eligible services proceed to cost/reputation ranking.

---

## 3. DAG Planning, Cycle Detection & Topological Ordering

In `backend/buyer/planner.py` and `backend/buyer/validator.py`:
1. **DAG Validation:** Before any step runs, `PlanValidator.validate()` inspects the plan:
   - Rejects non-existent dependency IDs (`MissingDependencyError`).
   - Rejects self-referencing dependencies (`SelfDependencyError`).
   - Runs cycle detection via depth-first search / Tarjan's algorithm; raises `PlanCycleError` on cyclic graphs.
   - Asserts total estimated plan cost $\le$ task spending limit.
   - Enforces catalog registered price over any client-provided price tampering.
2. **Topological Ordering:** Tasks are scheduled based on dependency levels:
   - Steps with no dependencies run first (in parallel up to `max_concurrency` via `asyncio.Semaphore`).
   - Steps with dependencies wait until all parent steps reach terminal `COMPLETED` status.

---

## 4. Upstream Dependency Propagation & Failure Isolation

In `backend/buyer/dependency_executor.py`:
- **Output Synthesis:** Completed upstream outputs are passed into downstream step payloads using JSON-pointer or template keys (e.g., `"${step_1.output.price}"`).
- **Upstream Failure Isolation:**
  - If step $A$ fails or times out, dependent step $B$ is immediately marked `SKIPPED`.
  - **Zero funds are reserved, zero payments are initiated, and zero seller calls are dispatched for skipped steps.**
- **Safe Fallbacks:**
  - If a primary service fails with `FAILED_AND_NOT_CHARGED`, a fallback service may only be attempted if:
    1. The fallback is registered and enabled.
    2. The remaining budget accommodates the fallback price.
    3. The prior attempt was **definitively not charged**.
  - **CRITICAL INVARIANT:** If the prior attempt is `PENDING_RECONCILIATION`, fallbacks are **strictly blocked** to prevent duplicate charging.

---

## 5. Output Validation & Provenance Aggregation

In `backend/buyer/output_validator.py` and `backend/buyer/aggregator.py`:
- **Schema Validation:** Seller outputs are validated against the catalog's `output_schema` using `Draft202012Validator`.
- **Integrity Preservation:** If an output fails schema validation:
  - Seller payment is recorded as `PAID` (work was executed and settled).
  - Task step is recorded as `FAILED` (output unusable).
  - Result aggregator includes explicit error explanation: `"Seller output failed registered schema validation."`
- **Zero Fact Fabrication:** Aggregated results only include values actually returned by seller services with cryptographic receipt links.

---

## 6. Automated Test Verification Results

```
backend/tests/test_buyer_dependency_execution.py::test_sequential_dependencies_and_input_synthesis PASSED
backend/tests/test_buyer_dependency_execution.py::test_parallel_execution_of_independent_calls PASSED
backend/tests/test_buyer_dependency_execution.py::test_failed_upstream_dependency_skips_dependent_call PASSED
backend/tests/test_buyer_dependency_execution.py::test_pre_payment_timeout_releases_budget_reservation PASSED
backend/tests/test_buyer_dependency_execution.py::test_concurrency_limit_bounded_by_semaphore PASSED
backend/tests/test_buyer_dependency_execution.py::test_budget_exhaustion_refuses_subsequent_calls PASSED
backend/tests/test_buyer_dependency_execution.py::test_ambiguous_payment_outcome_never_runs_fallback PASSED
backend/tests/test_buyer_dependency_execution.py::test_fallback_budget_safety_recheck PASSED
backend/tests/test_buyer_agent_multihop.py::test_buyer_agent_multi_hop_flow_with_x402_headers PASSED
backend/tests/test_buyer_orchestration_payment.py::test_every_paid_call_routes_through_member1_payment_client PASSED
backend/tests/test_planner_validator.py::test_plan_validator_rejects_cycles PASSED
backend/tests/test_output_validation_provenance.py::test_rejected_output_after_verified_payment_preserves_cost_and_evidence PASSED
backend/tests/test_purchase_explanation.py::test_basescan_explorer_link_no_fabrication PASSED
[43 passed in 1.20s]
```

**Gate Status:** PHASE 5 GATE E (AGENT RELIABILITY) — **PASSED**.
