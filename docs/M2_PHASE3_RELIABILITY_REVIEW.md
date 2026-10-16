# M2 Phase 3: Seller Reliability & Lifecycle Review

**Reviewer:** Member 2 — Seller Agents Technical Lead  
**Scope:** `backend/sellers/common.py`, `backend/sellers/data_seller.py`, `backend/sellers/scraping_seller.py`, and `backend/sellers/inference_seller.py`  
**Date:** 2026-10-17  
**Status:** COMPLETE — RELIABILITY-VERIFIED  

---

## 1. Executive Summary

This review audited the reliability and operational bounds enforced across all three seller services (`data_001`, `scraping_001`, `inference_001`) via the standardized lifecycle pattern in `BaseSellerService`.

---

## 2. Invariant Verification

### 2.1 Input Pre-Validation
- In `BaseSellerService.execute_lifecycle()`:
  - Input payload is validated against `self.input_model` using Pydantic v2 before calling `_execute_business_logic`.
  - Schema violations immediately raise `SellerInputValidationError` (HTTP 422), avoiding execution of downstream providers.

### 2.2 Output Post-Validation
- Output from `_execute_business_logic` is validated against `self.output_model` before formulating a success response.
- If seller logic produces corrupted or schema-violating data, `SellerOutputValidationError` is raised, resulting in HTTP 502 Bad Gateway and preventing malformed data from reaching the buyer.

### 2.3 Timeout Enforcement & Async Cancellation Semantics
- Business logic is executed inside `asyncio.wait_for(..., timeout=effective_timeout)`.
- If timeout expires, `asyncio.TimeoutError` is caught and translated to `SellerExecutionTimeoutError` (HTTP 504).
- **Technical Clarification on Task Cancellation:**
  - `asyncio.wait_for` issues `task.cancel()` to the inner coroutine.
  - In Python asyncio, `task.cancel()` raises `asyncio.CancelledError` inside the coroutine at the next `await` statement.
  - It does NOT physically interrupt non-cooperative C extensions, blocking system calls, or threads.
  - However, all I/O operations in Member 2 services utilize cooperative async clients (`httpx`, `anyio`), ensuring cancellation is honored as soon as the event loop cycles. Sockets are closed during transport teardown.

### 2.4 Bounded Concurrency & Semaphore Release
- Concurrency bounding is enforced per service via an `asyncio.Semaphore(max_concurrency)`:
  - Data Seller: 50
  - Scraping Seller: 20
  - Inference Seller: 10
- Execution is wrapped in `async with self.semaphore:`:
  - Python context manager semantics guarantee that `semaphore.release()` is executed in the `__aexit__` block under all conditions (successful completion, timeout, unhandled exception, or task cancellation).
  - No permit leakage is possible.

### 2.5 Exception Sanitization & Telemetry
- All exceptions are caught, logged with correlation IDs (`request_id`, `service_id`), and sanitized before being returned to clients.
- Telemetry metrics (`ExecutionMetrics`) measure wall-clock duration (`perf_counter`), success flags, timeout flags, and schema validation flags without fabricating performance numbers.
- Sensitive user inputs and scraped body content are excluded from application logs to protect privacy.
