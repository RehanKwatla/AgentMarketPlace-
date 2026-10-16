# MEMBER 3: SERVICE REGISTRY (`backend/registry/`)

**Assigned Owner:** Member 3 (Buyer & Marketplace Engineer)  
**Assigned Git Branch:** `feature/buyer-registry`  
**Status:** `[IMPLEMENTED FOUNDATION & EXTENSIBLE CATALOG]`

---

## 📋 Responsibilities Checklist

- [ ] **Service Catalog Management (`service_catalog.py`):**
  - Store and query service definitions with schemas, price, endpoint, network, `payTo`.
  - Filter by `category` and `max_price_usdc`.
  - Provide fallback provider lookup when primary provider fails.
- [ ] **Registry API Routes (`routes.py`):**
  - `GET /api/v1/services`: List services with filtering.
  - `GET /api/v1/services/{service_id}`: Retrieve single service.
- [ ] **Integration with Database Models:** Wire persistent storage in `backend/database/` with Member 4.
- [ ] **Registry Tests (`backend/tests/test_registry.py`):**
  - Test listing services.
  - Test filtering by price and category.
  - Test 404 for unknown service.
