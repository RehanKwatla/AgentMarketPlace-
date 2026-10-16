# SYSTEM ARCHITECTURE — PAY-PER-CALL AGENT ECONOMY (DI-06)

## 1. High-Level Architecture Overview

The system implements a decentralized, autonomous pay-per-call microservice economy where software agents interact across HTTP using the **x402 v2 payment standard**.

```mermaid
graph TB
    User[User / Judge Dashboard] -->|Submit Task & Budget| BuyerAgent[Buyer Agent System]
    BuyerAgent -->|Discover Services| Registry[Service Registry]
    BuyerAgent -->|Check Reputation| ReputationEngine[Reputation Engine]
    BuyerAgent -->|Reserve Budget| BudgetMgr[Atomic Budget Manager]
    
    subgraph Seller Ecosystem [Seller Microservices]
        DataSeller[Data Seller Agent]
        ScrapeSeller[Scraping Seller Agent]
        InferSeller[Inference Seller Agent]
    end

    BuyerAgent -->|1. Request Service| SellerEcosystem
    SellerEcosystem -->|2. HTTP 402 + Payment Requirement| BuyerAgent
    BuyerAgent -->|3. Validate Policy & Sign| PaymentEngine[x402 v2 Payment Engine]
    PaymentEngine -->|4. Request + Signed Payload| SellerEcosystem
    SellerEcosystem -->|5. Settle via Facilitator| Facilitator[x402 Facilitator / Base Sepolia]
    SellerEcosystem -->|6. Service Output + Settlement Proof| BuyerAgent
    
    BuyerAgent -->|Validate Output Schema| Validator[Schema Validator]
    BuyerAgent -->|Record Transaction| Ledger[Persistent Payment Ledger]
    Ledger -->|Update Metrics| ReputationEngine
    Ledger -->|Read Audit Records| Dashboard[Web Dashboard / REST API]
```

---

## 2. Component Separation & Ownership

```mermaid
classDiagram
    class SetupLead {
        +backend/shared/
        +backend/main.py
        +docs/API_CONTRACTS.md
        +requirements.txt
    }
    class Member1_Payments {
        +backend/payments/
        +BuyerPaymentClient
        +SellerPaymentVerifier
        +BudgetManager
        +IdempotencyStore
    }
    class Member2_Sellers {
        +backend/sellers/
        +DataSellerService
        +ScrapingSellerService
        +InferenceSellerService
    }
    class Member3_BuyerRegistry {
        +backend/buyer/
        +backend/registry/
        +TaskPlanner
        +ServiceSelector
        +ResultAggregator
    }
    class Member4_LedgerDashboard {
        +backend/ledger/
        +backend/database/
        +frontend/
        +LedgerRepository
        +ReputationCalculator
    }
    SetupLead --> Member1_Payments
    SetupLead --> Member2_Sellers
    SetupLead --> Member3_BuyerRegistry
    SetupLead --> Member4_LedgerDashboard
```

---

## 3. x402 v2 Protocol Lifecycle Sequence

The pay-per-call transaction adheres strictly to the official HTTP 402 payment lifecycle:

```mermaid
sequenceDiagram
    autonumber
    actor Buyer as Buyer Agent
    participant Seller as Seller Agent
    participant Facilitator as x402 Facilitator (Base Sepolia)
    participant Ledger as Persistent Ledger

    Buyer->>Seller: POST /api/v1/seller/{service} (Payload, no auth)
    Seller-->>Buyer: HTTP 402 Payment Required<br/>(Header: X-402-Requirement: {token, network, amount, payTo, nonce})
    
    critical Policy & Budget Verification
        Buyer->>Buyer: Verify Network == eip155:84532
        Buyer->>Buyer: Verify Token == Registered USDC
        Buyer->>Buyer: Verify payTo == Registered Seller Address
        Buyer->>Buyer: Verify Price <= Registry Quote && Budget Remaining
        Buyer->>Buyer: Reserve Budget Atomically (Integer Base Units)
    end

    Buyer->>Buyer: Sign EIP-712 Payment Authorization
    Buyer->>Seller: POST /api/v1/seller/{service}<br/>(Header: X-402-Payment-Payload: {sig, authorization})
    
    Seller->>Facilitator: Verify & Settle Payment Authorization
    Facilitator-->>Seller: Settlement Confirmation & Settlement Proof (TX Hash)
    
    Seller->>Seller: Execute Service Logic
    Seller-->>Buyer: HTTP 200 OK (Data Payload + X-402-Settlement-Proof)
    
    Buyer->>Buyer: Validate Output Schema against Registry
    alt Schema Valid
        Buyer->>Ledger: Record Status: "paid"
    else Schema Corrupt / Invalid
        Buyer->>Ledger: Record Status: "paid output rejected"
    end
```

---

## 4. Database Schema (Entity-Relationship)

```mermaid
erDiagram
    SERVICES ||--o{ LEDGER_RECORDS : references
    TASKS ||--o{ LEDGER_RECORDS : generates

    SERVICES {
        string service_id PK
        string name
        string category
        string endpoint_url
        string price_usdc
        string network
        string pay_to
        json input_schema
        json output_schema
        boolean is_active
    }

    TASKS {
        string task_id PK
        string prompt
        int budget_base_units
        int spent_base_units
        string status
        datetime created_at
        datetime completed_at
    }

    LEDGER_RECORDS {
        string request_id PK
        string task_id FK
        string service_id FK
        string buyer_id
        string seller_id
        int listed_price_units
        int amount_paid_units
        string tx_hash
        string status
        float latency_ms
        string error_reason
        datetime timestamp
    }
```
