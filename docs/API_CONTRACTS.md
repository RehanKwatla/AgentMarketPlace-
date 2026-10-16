# SHARED API CONTRACTS — PAY-PER-CALL AGENT ECONOMY (DI-06)

This document is the **binding contract** for all four engineering team members.
All endpoints, headers, payloads, query parameters, and status codes defined here must be followed without ad-hoc deviation.

---

## 1. Health & Diagnostics

### `GET /health`
Returns system operational status, database connectivity, and blockchain network connectivity.

- **Request:** None
- **Response `200 OK`:**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "network": "eip155:84532",
  "timestamp": "2026-10-16T12:00:00Z",
  "services": {
    "database": "connected",
    "registry": "active"
  }
}
```

---

## 2. Service Registry (`backend/registry/`)

### `GET /api/v1/services`
Lists all registered seller agent microservices with optional filtering.

- **Query Parameters:**
  - `category` (optional, string): Filter by category (`data`, `scraping`, `inference`).
  - `max_price_usdc` (optional, string): Max price in decimal USDC (e.g., `0.01`).
  - `is_active` (optional, boolean): Filter active providers (default `true`).

- **Response `200 OK`:**
```json
{
  "services": [
    {
      "service_id": "data_001",
      "name": "Alpha Financial Market Data",
      "category": "data",
      "endpoint_url": "http://localhost:8000/api/v1/seller/data",
      "price_usdc": "0.002",
      "price_base_units": 2000,
      "network": "eip155:84532",
      "pay_to": "0x0000000000000000000000000000000000000001",
      "description": "Provides real-time and historical asset market statistics",
      "input_schema": {
        "type": "object",
        "required": ["symbol"],
        "properties": {
          "symbol": { "type": "string", "example": "ETH" }
        }
      },
      "output_schema": {
        "type": "object",
        "required": ["symbol", "price", "volume_24h"],
        "properties": {
          "symbol": { "type": "string" },
          "price": { "type": "number" },
          "volume_24h": { "type": "number" }
        }
      },
      "is_active": true
    }
  ],
  "total": 1
}
```

### `GET /api/v1/services/{service_id}`
Returns the specific service definition or `404 Not Found`.

---

## 3. Buyer Agent Tasks (`backend/buyer/`)

### `POST /api/v1/buyer/tasks`
Submits a complex objective to the autonomous buyer agent. The buyer decomposes the goal, discovers services, reserves budget, executes x402-paid calls, validates responses, and synthesizes a final answer.

- **Request Body:**
```json
{
  "task": "Scrape trending AI research topics and summarize key takeaways",
  "budget_usdc": "0.05"
}
```

- **Response `200 OK`:**
```json
{
  "task_id": "task_20261016_001",
  "status": "completed",
  "budget_allocated_usdc": "0.05",
  "total_cost_usdc": "0.007",
  "cost_explanation": "1 scraping call (0.003 USDC) + 1 inference summary call (0.004 USDC)",
  "selected_services": ["scraping_001", "inference_001"],
  "executions": [
    {
      "step": 1,
      "service_id": "scraping_001",
      "request_id": "req_scrape_881a",
      "price_paid_usdc": "0.003",
      "tx_hash": "0x4b7c...",
      "status": "paid",
      "latency_ms": 320.5,
      "output": { "raw_text": "Recent breakthrough in pay-per-call agents..." }
    },
    {
      "step": 2,
      "service_id": "inference_001",
      "request_id": "req_infer_992b",
      "price_paid_usdc": "0.004",
      "tx_hash": "0x5d9e...",
      "status": "paid",
      "latency_ms": 780.2,
      "output": { "summary": "Autonomous payment protocols enable micro-economies." }
    }
  ],
  "final_result": "Summary of research: Autonomous payment protocols enable micro-economies.",
  "errors_and_fallbacks": []
}
```

- **Response `400 Bad Request`:**
```json
{
  "detail": "Requested task exceeds maximum allowed system budget of 1.0 USDC"
}
```

---

## 4. Seller Microservices (`backend/sellers/`)

All seller endpoints operate under the standard **x402 v2 payment handshake**.

### Headers Protocol:
- **Challenge Header (HTTP 402 from Seller):**
  - `X-402-Requirement`: JSON string encoding:
    ```json
    {
      "version": "2.0",
      "network": "eip155:84532",
      "token": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
      "amount": "2000",
      "payTo": "0x0000000000000000000000000000000000000001",
      "nonce": "nonce_unique_uuid",
      "service_id": "data_001"
    }
    ```
- **Payment Header (HTTP 200 re-request from Buyer):**
  - `X-402-Payment-Payload`: JSON string encoding the signed EIP-712 transfer authorization.
  - `Idempotency-Key`: UUID preventing duplicate execution.
- **Settlement Header (HTTP 200 from Seller):**
  - `X-402-Settlement-Proof`: Transaction hash or facilitator receipt proving on-chain settlement.

### Endpoints:
1. `POST /api/v1/seller/data`
   - Input: `{ "symbol": "ETH" }`
   - Output: `{ "symbol": "ETH", "price": 2650.50, "volume_24h": 1420500.0 }`
2. `POST /api/v1/seller/scraping`
   - Input: `{ "url": "https://example.com/article" }`
   - Output: `{ "url": "https://example.com/article", "content": "Clean extracted text", "word_count": 450 }`
3. `POST /api/v1/seller/inference`
   - Input: `{ "prompt": "Summarize this: ...", "max_tokens": 150 }`
   - Output: `{ "response": "Generated summary...", "model_used": "llama-3-8b", "tokens_generated": 42 }`

---

## 5. Ledger & Audit Trail (`backend/ledger/`)

### `GET /api/v1/ledger`
Returns immutable ledger records with pagination and status filtering.

- **Query Parameters:**
  - `status` (optional): Filter by status (`paid`, `paid output rejected`, `refused`, `failed and not charged`).
  - `service_id` (optional): Filter by service.
  - `limit` (default 50): Number of records.
  - `offset` (default 0): Pagination offset.

- **Response `200 OK`:**
```json
{
  "total": 1,
  "records": [
    {
      "request_id": "req_876b5c91",
      "timestamp": "2026-10-16T12:05:30Z",
      "buyer_id": "buyer_agent_primary",
      "seller_id": "seller_data_alpha",
      "service_id": "data_001",
      "listed_price": "0.002",
      "amount_paid": "0.002",
      "tx_hash": "0x89ab12cd...",
      "status": "paid",
      "latency_ms": 312.4,
      "error_reason": null
    }
  ]
}
```

### Ledger Status Transition Rules:
| Status | Explanation | When Emitted |
|---|---|---|
| `paid` | Service delivered successfully; output schema validated. | After verified on-chain settlement and 100% schema match. |
| `paid output rejected` | Service paid on-chain, but output was corrupted or failed schema. | Settlement confirmed, but buyer validator rejected payload. |
| `refused` | Pre-flight policy rejection before any payment payload was signed. | Price mismatch, budget exceeded, invalid network/token. |
| `failed and not charged` | Downstream network timeout or execution crash before settlement. | Facilitator refused signature or server 500 without charge. |

---

## 6. Provider Reputation Metrics (`backend/ledger/reputation.py`)

### `GET /api/v1/reputation`
Returns computed reliability metrics across all registered services.

### `GET /api/v1/reputation/{service_id}`
Returns metrics for a single provider.

- **Response `200 OK`:**
```json
{
  "service_id": "data_001",
  "total_calls": 120,
  "successful_calls": 118,
  "success_rate": 0.9833,
  "median_latency_ms": 285.0,
  "failure_counts": 1,
  "schema_invalid_counts": 1,
  "listed_price_usdc": "0.002",
  "reputation_score": 96.5
}
```
