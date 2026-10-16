"""Focused test suite for capability metadata validation, serialization, backward compatibility, service selection, and planning."""
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.shared.constants import (
    NETWORK_BASE_SEPOLIA,
    USDC_BASE_SEPOLIA,
    ServiceCategory,
)
from backend.shared.schemas import CapabilityMetadata, ServiceDefinition
from backend.registry.schemas import ServiceRecord, ServiceRegistrationRequest
from backend.registry.service import RegistryService
from backend.registry.validation import validate_service_registration, ValidationError
from backend.buyer.selector import ServiceSelector
from backend.buyer.planner import TaskPlanner
from backend.buyer.schemas import TaskCreationRequest
from backend.buyer.plan_validator import PlanValidationError


client = TestClient(app)


# ==============================================================================
# 1. Metadata Validation & Serialization Tests
# ==============================================================================

def test_capability_metadata_instantiation_defaults():
    meta = CapabilityMetadata()
    assert meta.version == "1.0.0"
    assert meta.tags == []
    assert meta.supported_formats == []
    assert meta.max_payload_bytes is None
    assert meta.rate_limit_per_minute is None
    assert meta.sla_latency_p95_ms is None
    assert meta.deterministic is True
    assert meta.constraints == {}


def test_capability_metadata_serialization_roundtrip():
    meta = CapabilityMetadata(
        version="1.2.0",
        tags=["crypto", "spot-prices"],
        supported_formats=["application/json"],
        max_payload_bytes=2048,
        rate_limit_per_minute=120,
        sla_latency_p95_ms=150,
        deterministic=False,
        constraints={"supported_symbols": ["ETH", "BTC"]},
    )
    dumped = meta.model_dump()
    assert dumped["version"] == "1.2.0"
    assert dumped["max_payload_bytes"] == 2048
    assert dumped["constraints"]["supported_symbols"] == ["ETH", "BTC"]

    restored = CapabilityMetadata.model_validate(dumped)
    assert restored == meta


# ==============================================================================
# 2. Backward Compatibility Tests
# ==============================================================================

def test_service_definition_backward_compatibility():
    # Legacy instantiation without capability_metadata
    legacy_data = {
        "service_id": "legacy_001",
        "name": "Legacy Service",
        "category": ServiceCategory.DATA,
        "endpoint_url": "https://legacy.example.com",
        "price_usdc": "0.002",
        "pay_to": "0x1111111111111111111111111111111111111111",
    }
    svc = ServiceDefinition.model_validate(legacy_data)
    assert svc.capability_metadata is None
    assert svc.price_base_units == 2000

    # Serialization preserves omitted metadata as None
    data = svc.model_dump()
    assert "capability_metadata" in data
    assert data["capability_metadata"] is None


def test_service_record_backward_compatibility():
    legacy_rec = {
        "service_id": "legacy_rec_001",
        "name": "Legacy Record",
        "category": ServiceCategory.SCRAPING,
        "endpoint_url": "https://legacy.example.com",
        "price_usdc": "0.003",
        "pay_to": "0x2222222222222222222222222222222222222222",
    }
    rec = ServiceRecord.model_validate(legacy_rec)
    assert rec.capability_metadata is None
    assert rec.price_atomic == 3000


# ==============================================================================
# 3. Seeded Services Capability Metadata Tests
# ==============================================================================

def test_seed_services_have_capability_metadata():
    reg = RegistryService()
    data_svc = reg.get_service("data_001")
    scraping_svc = reg.get_service("scraping_001")
    inference_svc = reg.get_service("inference_001")

    assert data_svc.capability_metadata is not None
    assert "crypto" in data_svc.capability_metadata.tags
    assert data_svc.capability_metadata.sla_latency_p95_ms == 180
    assert "ETH" in data_svc.capability_metadata.constraints["supported_symbols"]

    assert scraping_svc.capability_metadata is not None
    assert "web" in scraping_svc.capability_metadata.tags
    assert "text/html" in scraping_svc.capability_metadata.supported_formats
    assert scraping_svc.capability_metadata.constraints["max_url_length"] == 2048

    assert inference_svc.capability_metadata is not None
    assert "llm" in inference_svc.capability_metadata.tags
    assert inference_svc.capability_metadata.constraints["max_prompt_length"] == 4000


def test_api_services_endpoint_returns_capability_metadata():
    resp = client.get("/api/v1/services/data_001")
    assert resp.status_code == 200
    body = resp.json()
    assert "capability_metadata" in body
    assert body["capability_metadata"] is not None
    assert "crypto" in body["capability_metadata"]["tags"]


def test_registry_search_by_capability_tag():
    resp = client.get("/api/v1/services?q=spot-prices")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) >= 1
    assert any(i["service_id"] == "data_001" for i in items)


def test_service_registration_validation_with_capability_metadata():
    valid_payload = {
        "service_id": "test_custom_001",
        "name": "Custom Seller Service",
        "category": "data",
        "endpoint_url": "https://seller.example.com/api",
        "price_usdc": "0.005",
        "network": NETWORK_BASE_SEPOLIA,
        "pay_to": "0x3333333333333333333333333333333333333333",
        "input_schema": {"type": "object"},
        "output_schema": {"type": "object"},
        "capability_metadata": {
            "version": "1.0.0",
            "tags": ["finance", "custom"],
            "max_payload_bytes": 1024,
        },
    }
    # Should not raise
    validate_service_registration(valid_payload)

    # Invalid capability metadata type
    invalid_payload = dict(valid_payload)
    invalid_payload["capability_metadata"] = "not-a-dict-or-model"
    with pytest.raises(ValidationError):
        validate_service_registration(invalid_payload)


# ==============================================================================
# 4. Capability-Aware Selector Tests
# ==============================================================================

def test_selector_matches_required_capability_tags():
    reg = RegistryService()
    selector = ServiceSelector(registry=reg)

    # data_001 has tag 'crypto'
    selected = selector.select_service_for_category(
        category=ServiceCategory.DATA,
        max_budget_units=10000,
        required_tags=["crypto"],
    )
    assert selected is not None
    assert selected.service_id == "data_001"

    # Non-existent tag should fail eligibility
    selected_none = selector.select_service_for_category(
        category=ServiceCategory.DATA,
        max_budget_units=10000,
        required_tags=["non-existent-tag-12345"],
    )
    assert selected_none is None


def test_selector_enforces_sla_latency_constraint():
    reg = RegistryService()
    selector = ServiceSelector(registry=reg)

    # data_001 has SLA 180ms. If max allowed is 200ms, it passes
    svc = selector.select_service_for_category(
        category=ServiceCategory.DATA,
        max_budget_units=10000,
        max_latency_ms=200,
    )
    assert svc is not None

    # If max allowed is 100ms, it fails SLA gate
    svc_tight = selector.select_service_for_category(
        category=ServiceCategory.DATA,
        max_budget_units=10000,
        max_latency_ms=100,
    )
    assert svc_tight is None


def test_selector_enforces_max_payload_constraint():
    reg = RegistryService()
    selector = ServiceSelector(registry=reg)

    # data_001 allows up to 1024 bytes. 500 bytes is ok.
    svc_ok = selector.select_service_for_category(
        category=ServiceCategory.DATA,
        max_budget_units=10000,
        payload_bytes=500,
    )
    assert svc_ok is not None

    # 2048 bytes exceeds data_001 max_payload_bytes
    svc_fail = selector.select_service_for_category(
        category=ServiceCategory.DATA,
        max_budget_units=10000,
        payload_bytes=2048,
    )
    assert svc_fail is None


# ==============================================================================
# 5. Planner Capability Input Validation Tests
# ==============================================================================

def test_planner_creates_valid_plan_with_capability_metadata():
    planner = TaskPlanner()
    req = TaskCreationRequest(
        task="Extract data from https://ethereum.org, get crypto rate for ETH, and summarize findings.",
        budget_usdc="0.05",
        max_concurrency=3,
    )
    plan = planner.create_plan(req)
    assert len(plan.calls) == 3
    assert plan.expected_cost_units > 0


def test_planner_rejects_scraping_blocked_host():
    planner = TaskPlanner()
    # Attempting to plan scraping on localhost should be rejected before execution
    req = TaskCreationRequest(
        task="Scrape internal details from http://localhost:8000/admin and summarize.",
        budget_usdc="0.05",
        preferred_categories=[ServiceCategory.SCRAPING],
    )
    with pytest.raises(PlanValidationError) as exc:
        planner.create_plan(req)
    assert "blocked host destination" in str(exc.value).lower()


def test_planner_rejects_scraping_unsupported_scheme():
    planner = TaskPlanner()
    req = TaskCreationRequest(
        task="Scrape file contents from ftp://files.example.com/data.txt and extract text.",
        budget_usdc="0.05",
        preferred_categories=[ServiceCategory.SCRAPING],
    )
    with pytest.raises(PlanValidationError) as exc:
        planner.create_plan(req)
    assert "allowed schemes" in str(exc.value).lower()


def test_planner_rejects_data_unsupported_symbol():
    planner = TaskPlanner()
    req = TaskCreationRequest(
        task="Look up market price of UNKNOWNCOINXYZ and report metrics.",
        budget_usdc="0.05",
        preferred_categories=[ServiceCategory.DATA],
    )
    with pytest.raises(PlanValidationError) as exc:
        planner.create_plan(req)
    assert "not supported" in str(exc.value).lower()


def test_planner_rejects_inference_prompt_exceeding_max_length():
    planner = TaskPlanner()
    huge_prompt = "Summarize: " + ("A" * 5000)
    req = TaskCreationRequest(
        task=huge_prompt,
        budget_usdc="0.05",
        preferred_categories=[ServiceCategory.INFERENCE],
    )
    with pytest.raises(PlanValidationError) as exc:
        planner.create_plan(req)
    assert "exceeds declared service limit" in str(exc.value).lower()
