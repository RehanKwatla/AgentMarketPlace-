"""Comprehensive Unit and API Tests for Service Registry and Discovery."""
import pytest
from fastapi import status
from backend.registry.service import registry_service
from backend.registry.schemas import ServiceRecord
from backend.registry.validation import validate_service_registration
from backend.shared.constants import ServiceCategory, NETWORK_BASE_SEPOLIA, USDC_BASE_SEPOLIA
from backend.registry.validation import ValidationError


def test_list_services(client):
    """Verify registry listing contains all 3 canonical seeded categories labeled as demo/seed."""
    response = client.get("/api/v1/services")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    services = data.get("services") or data.get("items")
    assert len(services) >= 3

    service_map = {s["service_id"]: s for s in services}
    assert "data_001" in service_map or "data-001" in service_map
    assert "scraping_001" in service_map or "scraping-001" in service_map
    assert "inference_001" in service_map or "inference-001" in service_map

    # Check required capabilities & demo/seed tag
    data_svc = service_map.get("data_001") or service_map.get("data-001")
    assert "data.lookup.v1" in data_svc["capabilities"]
    assert data_svc["is_demo_seed"] is True

    scraping_svc = service_map.get("scraping_001") or service_map.get("scraping-001")
    assert "scraping.extract.v1" in scraping_svc["capabilities"]

    infer_svc = service_map.get("inference_001") or service_map.get("inference-001")
    assert "inference.summarize.v1" in infer_svc["capabilities"]


def test_service_schema_validation(client):
    """Verify single service endpoint returns full metadata, schemas, and atomic pricing."""
    response = client.get("/api/v1/services/data_001")
    assert response.status_code == status.HTTP_200_OK
    service = response.json()
    assert service["service_id"] == "data_001"
    assert service["category"] == "data"
    assert service["network"] == NETWORK_BASE_SEPOLIA
    assert service["price_usdc"] == "0.002"
    assert service["price_base_units"] == 2000
    assert service["price_atomic"] == 2000
    assert "pay_to" in service
    assert "input_schema" in service
    assert "output_schema" in service
    assert service["is_demo_seed"] is True


def test_registry_category_filtering(client):
    """Test filtering by category for data, scraping, and inference."""
    for category in ["data", "scraping", "inference"]:
        response = client.get(f"/api/v1/services?category={category}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        items = data.get("services") or data.get("items")
        assert len(items) >= 1
        for s in items:
            assert s["category"] == category


def test_registry_capability_filtering(client):
    """Test filtering by capability identifier."""
    response = client.get("/api/v1/services?capability=data.lookup.v1")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    items = data.get("services") or data.get("items")
    assert len(items) >= 1
    assert any("data" in s["service_id"] for s in items)


def test_registry_text_search(client):
    """Test searching services by capability/text query."""
    response = client.get("/api/v1/services?q=markdown")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    items = data.get("services") or data.get("items")
    assert len(items) >= 1
    assert any("scraping" in s["service_id"] for s in items)


def test_registry_price_filtering(client):
    """Test min_price_usdc and max_price_usdc filtering."""
    # Integer prices include the two data services at or below 0.0025 USDC.
    response = client.get("/api/v1/services?max_price_usdc=0.0025")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    items = data.get("services") or data.get("items")
    assert {item["service_id"] for item in items} == {"data_001", "data_002"}

    # Min price 0.0035 should include inference_001 (0.004)
    response_min = client.get("/api/v1/services?min_price_usdc=0.0035")
    assert response_min.status_code == status.HTTP_200_OK
    data_min = response_min.json()
    items_min = data_min.get("services") or data_min.get("items")
    assert len(items_min) == 1
    assert items_min[0]["service_id"] == "inference_001"


def test_registry_has_nine_unique_differentiated_profiles(client):
    response = client.get("/api/v1/services?limit=100")
    assert response.status_code == status.HTTP_200_OK
    services = response.json()["services"]
    assert len(services) == 9
    assert len({item["service_id"] for item in services}) == 9
    assert {category: sum(item["category"] == category for item in services)
            for category in ("data", "scraping", "inference")} == {"data": 3, "scraping": 3, "inference": 3}
    assert len({item["price_base_units"] for item in services}) > 3
    assert all(item["price_base_units"] > 0 and item["pay_to"].startswith("0x") for item in services)


def test_duplicate_service_id_is_rejected():
    service = registry_service.get_service("data_001")
    with pytest.raises(ValueError, match="already registered"):
        registry_service.register_service(service)


def test_recommendation_has_honest_new_evidence_and_hard_filters(client):
    response = client.post("/api/v1/services/recommendations", json={
        "task_prompt": "Find an agent for current market prices",
        "category": "data",
        "required_capabilities": ["crypto.market.rates"],
        "max_budget_usdc": "0.003000",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["recommendations"]
    assert all(c["performance"]["evidence_status"] in {"NEW", "INSUFFICIENT_DATA", "VERIFIED"}
               for c in data["recommendations"])
    assert all(c["performance"]["success_rate"] is None or c["performance"]["sample_size"] > 0
               for c in data["recommendations"])
    assert any(c["service_id"] == "data_003" for c in data["rejected_candidates"])


def test_service_not_found(client):
    """Unknown service ID returns HTTP 404 with standard error envelope."""
    response = client.get("/api/v1/services/unknown_service_999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    error_data = response.json()
    assert "error" in error_data
    assert error_data["error"]["code"] == "NOT_FOUND"


def test_service_reputation_endpoint(client):
    """Verify reputation retrieval endpoint returns observed metrics via Member 4."""
    response = client.get("/api/v1/services/data_001/reputation")
    assert response.status_code == status.HTTP_200_OK
    rep = response.json()
    assert rep["service_id"] == "data_001"
    assert "reputation_score" in rep
    assert "success_rate" in rep
    assert "median_latency_ms" in rep


def test_disabled_service_exclusion(client):
    """Disabled services must be excluded from active selection even if queryable with active=false."""
    disabled_service = ServiceRecord(
        service_id="disabled_service_001",
        name="Disabled Offline Provider",
        category=ServiceCategory.DATA,
        capabilities=["data.offline.v1"],
        endpoint_url="http://localhost:8000/api/v1/seller/offline",
        price_usdc="0.001",
        network=NETWORK_BASE_SEPOLIA,
        pay_to="0x2000000000000000000000000000000000000009",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        enabled=False,
        is_active=False
    )
    registry_service.register_service(disabled_service)

    # 1. get_active_service must return None (buyer selection safety)
    assert registry_service.get_active_service("disabled_service_001") is None

    # 2. Querying with active=True excludes it
    active_res = client.get("/api/v1/services?active=true")
    assert active_res.status_code == status.HTTP_200_OK
    active_items = (active_res.json().get("services") or active_res.json().get("items"))
    assert not any(s["service_id"] == "disabled_service_001" for s in active_items)

    # 3. Querying explicitly with active=false returns it
    disabled_res = client.get("/api/v1/services?active=false")
    assert disabled_res.status_code == status.HTTP_200_OK
    disabled_items = (disabled_res.json().get("services") or disabled_res.json().get("items"))
    assert any(s["service_id"] == "disabled_service_001" for s in disabled_items)


def test_malformed_service_registration_validation():
    """Verify validation rejects malformed records, wrong networks, non-positive price, or bad schemas."""
    # 1. Invalid network (not Base Sepolia)
    with pytest.raises(ValidationError, match="Unsupported network"):
        validate_service_registration({
            "service_id": "test_invalid_net",
            "name": "Bad Network",
            "category": "data",
            "endpoint_url": "http://example.com",
            "price_usdc": "0.002",
            "network": "eip155:1",  # Mainnet rejected
            "pay_to": "0x2000000000000000000000000000000000000001",
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"}
        })

    # 2. Non-positive price
    with pytest.raises(ValidationError, match="strictly positive"):
        validate_service_registration({
            "service_id": "test_zero_price",
            "name": "Zero Price",
            "category": "data",
            "endpoint_url": "http://example.com",
            "price_usdc": "0",
            "network": NETWORK_BASE_SEPOLIA,
            "pay_to": "0x2000000000000000000000000000000000000001",
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"}
        })

    # 3. Malformed JSON schema
    with pytest.raises(ValidationError, match="Invalid JSON Schema"):
        validate_service_registration({
            "service_id": "test_bad_schema",
            "name": "Bad Schema",
            "category": "data",
            "endpoint_url": "http://example.com",
            "price_usdc": "0.002",
            "network": NETWORK_BASE_SEPOLIA,
            "pay_to": "0x2000000000000000000000000000000000000001",
            "input_schema": {"type": "invalid_type_not_allowed_in_json_schema"},
            "output_schema": {"type": "object"}
        })
