# DI-06: PAY-PER-CALL AGENT ECONOMY — OFFICIAL REQUIREMENTS & SPECIFICATION

## Hackathon Track: DI-06
## Deadline: 24-Hour Execution Window
## Core Problem: Decentralized Autonomous Agent Market with Pay-Per-Call Micropayments

---

### 1. Executive Summary
The DI-06 challenge requires building a robust, fault-tolerant, decentralized agent economy where autonomous agents purchase and sell specialized micro-services on a per-call basis. Payments are settled using **USDC on Base Sepolia (`eip155:84532`)** governed strictly by the **x402 v2 payment standard**.

---

### 2. Mandatory Core Requirements

| # | System Component | Requirement Specification |
|---|---|---|
| **REQ-01** | **Service Registry & Marketplace** | Searchable registry of seller agents with metadata, pricing in USDC, category, endpoint, network, `payTo` address, and input/output JSON schemas. Filterable by price and category. |
| **REQ-02** | **Three Seller Agents** | 1. **Data Seller:** Provides structured financial/market or analytical datasets.<br>2. **Scraping Seller:** Fetches, parses, and extracts clean markdown/JSON from web targets.<br>3. **Inference Seller:** Synthesizes, analyzes, or summarizes data via LLM or analytical models. |
| **REQ-03** | **Buyer Agent** | Autonomous client capable of decomposing high-level user tasks into sequential/parallel service calls, discovering providers, enforcing budgets, purchasing services via x402, and aggregating results. |
| **REQ-04** | **Official x402 v2 Integration** | Standard HTTP 402 Payment Required flow using official x402 specification. Headers: `X-402-Requirement`, `X-402-Payment-Payload`, `X-402-Settlement-Proof`. |
| **REQ-05** | **Base Sepolia USDC** | Blockchain network `eip155:84532`. Transactions denominated in testnet USDC base units (6 decimals). Real on-chain recipient addresses. |
| **REQ-06** | **Budget & Price Safety** | Atomic budget reservations preventing overspending under concurrency (minimum 3 concurrent worker tasks). Verification that seller quotes match registry prices. |
| **REQ-07** | **Replay Protection & Idempotency** | Protection against double charging. Request nonces, idempotency keys, and transaction hashes recorded to prevent replaying payment payloads. |
| **REQ-08** | **Output Schema Validation** | Buyer validates all seller outputs against the registered schema. If output is invalid, status transitions to `paid output rejected`. |
| **REQ-09** | **Persistent Payment Ledger** | Immutable audit trail storing: Request ID, Timestamp, Buyer ID, Seller ID, Service ID, Listed Price, Amount Paid, TX Hash, Status, Latency, Error Reason. |
| **REQ-10** | **Provider Reputation Metrics** | Dynamic calculation of provider reliability: Success rate, median latency, total calls, failure counts, schema violation counts. Used by buyer for routing decisions. |
| **REQ-11** | **Web Dashboard** | Real-time frontend displaying active agents, marketplace catalog, live buyer task execution logs, ledger transactions, and seller reputation badges. |
| **REQ-12** | **Public Endpoints for Judging** | Publicly accessible HTTPS endpoints for registry, buyer task trigger, seller endpoints, and ledger. |
| **REQ-13** | **Reproducible Tests & Startup** | Single-command startup (`start_dev.py`), automated pytest test suite covering unit, safety, budget, replay, and integration flows. |

---

### 3. Payment Status Definitions & Lifecycle Transitions

The payment ledger must record strictly one of the four required terminal states:

1. `paid`: Payment was successfully negotiated/settled, seller executed task, and output matched registered schema.
2. `paid output rejected`: Payment was negotiated/settled, but the seller's response failed JSON schema validation or returned corrupt payload.
3. `refused`: Buyer policy or seller pre-flight rejected the call (e.g., price exceeds budget, unregistered payTo address, network mismatch) before payment settlement occurred.
4. `failed and not charged`: An execution error occurred before settlement, or payment authorization failed with zero funds deducted.

---

### 4. Concurrency & Performance Thresholds
- The buyer execution engine must support at least **3 concurrent requests** executing distinct or parallel subtasks.
- Budget checks must be **atomic** (mutex or transactional row locking) so that parallel tasks cannot overdraw available budget.
- Calculations must use **integer USDC base units** (1 USDC = 1,000,000 units) to avoid floating-point rounding errors.
