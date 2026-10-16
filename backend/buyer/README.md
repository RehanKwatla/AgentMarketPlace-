# MEMBER 3: BUYER AGENT SYSTEM (`backend/buyer/`)

**Assigned Owner:** Member 3 (Buyer & Marketplace Engineer)  
**Assigned Git Branch:** `feature/buyer-registry`  
**Status:** `[DEFINED INTERFACES & PLANNING FOUNDATION]`

---

## 📋 Responsibilities Checklist

- [ ] **Task Planner (`task_planner.py`):**
  - Parse unstructured user goals (e.g. "Scrape site X and summarize findings").
  - Decompose goal into an execution DAG (Directed Acyclic Graph) of microservice calls.
  - Calculate estimated budget and cost upper bounds.
- [ ] **Service Selector (`service_selector.py`):**
  - Discover suitable candidate services from `ServiceCatalog`.
  - Perform reputation-aware routing (prefer providers with high reputation score and low latency).
  - Select alternative fallback providers if primary seller fails.
- [ ] **Buyer Agent Coordinator (`buyer_agent.py`):**
  - Manage concurrent or sequential task step executions.
  - Interface with Member 1's `BudgetManager` to reserve funds atomically before each step.
  - Interface with Member 1's `BuyerPaymentClient` to handle HTTP 402 challenge/response with seller.
  - Validate seller outputs against registered schema.
- [ ] **Result Aggregator (`result_aggregator.py`):**
  - Collect intermediate step outputs.
  - Synthesize clear final answer and transparent cost explanation.
- [ ] **Buyer Task API (`routes.py`):**
  - `POST /api/v1/buyer/tasks`: Trigger task execution.
- [ ] **Buyer Tests (`backend/tests/test_buyer.py`):**
  - Test task decomposition.
  - Test budget overdraw refusal.
  - Test provider routing.
