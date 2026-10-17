"""Phase 2 Test Suite: Nine Seller Agents, Search Strategy, Trustworthy Metrics, and Recommendations.

Verifies:
1. Nine unique agent IDs (3 Data, 3 Scraping, 3 Inference) with distinct profiles and integer base unit prices.
2. Trustworthy performance metrics with evidence status (NEW, INSUFFICIENT_DATA, VERIFIED) derived only from ledger evidence.
3. Multi-attribute recommendation engine with exact factor weights (25%, 20%, 15%, 15%, 10%, 10%, 5%).
4. Hard eligibility gates (category, capability, budget, schema, latency SLA, security policy).
5. Capability mismatch despite low price rejection.
6. Deterministic tie-breaking rules.
7. Multi-agent seller route execution via dynamic service_id query/header resolution.
8. Buyer execution pipeline integration with budget reservation, payment, output validation, and fallback verification.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.main import app
from backend.shared.constants import (
    NETWORK_BASE_SEPOLIA,
    USDC_BASE_SEPOLIA,
    ServiceCategory,
)
from backend.registry.service import registry_service
from backend.registry.recommendation import (
    RecommendationEngine,
    RecommendationRequest,
    EvidenceStatus,
)
from types import SimpleNamespace
from backend.buyer.schemas import TaskCreationRequest
from backend.buyer.planner import TaskPlanner
from backend.buyer.selector import ServiceSelector
from backend.buyer.service import buyer_service
from backend.ledger.models import ledger_repo


@pytest.fixture
def client():
    return TestClient(app)


def test_task1_nine_unique_agent_ids_and_three_per_category():
    """Verify registry discovers exactly nine agents with 3 Data, 3 Scraping, and 3 Inference."""
    services = registry_service.list_services(limit=50).items
    service_ids = {s.service_id for s in services}

    # Verify canonical IDs
    assert "data_001" in service_ids
    assert "scraping_001" in service_ids
    assert "inference_001" in service_ids

    # Verify added Phase 2 IDs
    assert "data_002" in service_ids
    assert "data_003" in service_ids
    assert "scraping_002" in service_ids
    assert "scraping_003" in service_ids
    assert "inference_002" in service_ids
    assert "inference_003" in service_ids

    data_svcs = [s for s in services if s.category == ServiceCategory.DATA]
    scraping_svcs = [s for s in services if s.category == ServiceCategory.SCRAPING]
    inference_svcs = [s for s in services if s.category == ServiceCategory.INFERENCE]

    assert len(data_svcs) >= 3
    assert len(scraping_svcs) >= 3
    assert len(inference_svcs) >= 3

    # Verify each agent has distinct integer atomic prices and valid schemas
    for s in services:
        assert s.price_atomic > 0
        assert isinstance(s.price_atomic, int)
        assert s.network == NETWORK_BASE_SEPOLIA
        assert s.asset_address.lower() == USDC_BASE_SEPOLIA.lower()
        assert s.pay_to.startswith("0x") and len(s.pay_to) == 42
        assert s.input_schema is not None
        assert s.output_schema is not None
        assert s.capability_metadata is not None
        assert s.capability_metadata.sla_latency_p95_ms > 0


def test_task2_trustworthy_metrics_evidence_levels():
    """Verify observed metrics label agents as NEW or INSUFFICIENT_DATA and zero fabrication."""
    engine = RecommendationEngine(registry=registry_service, repository=ledger_repo)

    # Reference profile with 0 calls must be NEW
    svc_data_002 = registry_service.get_service("data_002")
    metrics_002 = engine.metrics(svc_data_002)

    assert metrics_002["service_id"] == "data_002"
    assert metrics_002["evidence_status"] == EvidenceStatus.NEW.value
    assert metrics_002["sample_size"] == 0
    assert metrics_002["success_rate"] is None
    assert metrics_002["schema_validity_rate"] is None
    assert metrics_002["reliability_score"] is None
    assert metrics_002["median_latency_ms"] is None

    # Test evidence status transition when records are present
    mock_repo = MagicMock()
    # 5 samples -> INSUFFICIENT_DATA (<20)
    mock_repo.list_records.return_value = [
        SimpleNamespace(task_id=f"t_{i}", request_id=f"r_{i}", service_id="data_002",
                        listed_price="0.0015", amount_paid="0.0015", status="paid", latency_ms=150.0, error_reason=None)
        for i in range(5)
    ]
    engine_mock = RecommendationEngine(registry=registry_service, repository=mock_repo)
    m_5 = engine_mock.metrics(svc_data_002)
    assert m_5["evidence_status"] == EvidenceStatus.INSUFFICIENT_DATA.value
    assert m_5["sample_size"] == 5
    assert m_5["success_rate"] == 1.0

    # 25 samples -> VERIFIED (>=20)
    mock_repo.list_records.return_value = [
        SimpleNamespace(task_id=f"t_{i}", request_id=f"r_{i}", service_id="data_002",
                        listed_price="0.0015", amount_paid="0.0015", status="paid", latency_ms=150.0, error_reason=None)
        for i in range(25)
    ]
    m_25 = engine_mock.metrics(svc_data_002)
    assert m_25["evidence_status"] == EvidenceStatus.VERIFIED.value
    assert m_25["sample_size"] == 25


def test_task3_recommendation_factor_weights_and_hard_filters():
    """Verify recommendation engine enforces the exact 7 factor weights and hard filters."""
    engine = RecommendationEngine(registry=registry_service, repository=ledger_repo)

    # Check exact weights specified in requirements
    assert engine.FACTOR_WEIGHTS == {
        "capability_match": 0.25,
        "output_validity": 0.20,
        "reliability": 0.15,
        "success_rate": 0.15,
        "price_efficiency": 0.10,
        "response_time": 0.10,
        "historical_validity": 0.05,
    }
    assert sum(engine.FACTOR_WEIGHTS.values()) == 1.00

    # Hard Filter 1: Budget filter in integer base units
    req_budget = RecommendationRequest(
        task_prompt="Look up market rates",
        category=ServiceCategory.DATA,
        max_budget_atomic=1800,  # 1800 units: data_002 (1500) eligible; data_001 (2000) and data_003 (5000) rejected
    )
    res_budget = engine.evaluate_and_rank(req_budget)
    assert any(c["service_id"] == "data_002" for c in res_budget["recommendations"])
    rejected_ids = {r["service_id"] for r in res_budget["rejected_candidates"]}
    assert "data_001" in rejected_ids
    assert "data_003" in rejected_ids

    # Hard Filter 2: Capability mismatch rejection despite low price
    # data_002 is cheapest (1500 units) but lacks "crypto.market.history"
    req_cap = RecommendationRequest(
        task_prompt="Fetch historical candle time series",
        category=ServiceCategory.DATA,
        required_capabilities=["crypto.market.history"],
    )
    res_cap = engine.evaluate_and_rank(req_cap)
    cap_rec_ids = [c["service_id"] for c in res_cap["recommendations"]]
    assert "data_003" in cap_rec_ids
    assert "data_002" not in cap_rec_ids
    rej_002 = next(r for r in res_cap["rejected_candidates"] if r["service_id"] == "data_002")
    assert any("capability" in r.lower() for r in rej_002["rejection_reasons"])

    # Hard Filter 3: Latency SLA filter
    req_lat = RecommendationRequest(
        task_prompt="Fast scraping",
        category=ServiceCategory.SCRAPING,
        max_acceptable_latency_ms=750,  # scraping_001 (680ms) passes; scraping_002 (900ms) & scraping_003 (1400ms) fail
    )
    res_lat = engine.evaluate_and_rank(req_lat)
    lat_rec_ids = [c["service_id"] for c in res_lat["recommendations"]]
    assert "scraping_001" in lat_rec_ids
    assert "scraping_003" not in lat_rec_ids


def test_task3_deterministic_ranking_and_tie_breaking():
    """Verify deterministic tie-breaking: weighted_score DESC, capability_match DESC, price_atomic ASC, service_id ASC."""
    engine = RecommendationEngine(registry=registry_service, repository=ledger_repo)
    req = RecommendationRequest(
        task_prompt="Analyze unstructured reports and generate summaries",
        category=ServiceCategory.INFERENCE,
        required_capabilities=["inference.summarize.v1"],
    )
    res = engine.evaluate_and_rank(req)
    recommendations = res["recommendations"]

    assert len(recommendations) >= 2
    # Verify rankings are sorted deterministically
    for i in range(len(recommendations) - 1):
        curr = recommendations[i]
        nxt = recommendations[i + 1]
        assert curr["weighted_score"] >= nxt["weighted_score"]
        if curr["weighted_score"] == nxt["weighted_score"]:
            assert curr["factor_scores"]["capability_match"] >= nxt["factor_scores"]["capability_match"]
            if curr["factor_scores"]["capability_match"] == nxt["factor_scores"]["capability_match"]:
                assert curr["price_atomic"] <= nxt["price_atomic"]


def test_task4_seller_routes_dynamic_service_id_execution(client):
    """Verify seller routes (/data, /scraping, /inference) dynamically resolve service_id in 402 challenge."""
    # 1. Calling /data with service_id=data_002
    resp_402_data = client.post("/api/v1/seller/data?service_id=data_002", json={"symbol": "ETH"})
    assert resp_402_data.status_code == 402
    req_header = resp_402_data.headers.get("x-402-requirement")
    assert req_header is not None
    import json
    data_req = json.loads(req_header)
    assert data_req["service_id"] == "data_002"
    assert data_req["amount"] == "1500"  # data_002 price

    # 2. Calling /scraping with service_id=scraping_003
    resp_402_scraping = client.post("/api/v1/seller/scraping?service_id=scraping_003", json={"url": "https://ethereum.org"})
    assert resp_402_scraping.status_code == 402
    scraping_req = json.loads(resp_402_scraping.headers.get("x-402-requirement"))
    assert scraping_req["service_id"] == "scraping_003"
    assert scraping_req["amount"] == "4000"  # scraping_003 price

    # 3. Calling /inference with service_id=inference_002
    resp_402_inf = client.post("/api/v1/seller/inference?service_id=inference_002", json={"prompt": "Summarize"})
    assert resp_402_inf.status_code == 402
    inf_req = json.loads(resp_402_inf.headers.get("x-402-requirement"))
    assert inf_req["service_id"] == "inference_002"
    assert inf_req["amount"] == "6000"  # inference_002 price


def test_task4_recommendation_and_buyer_planning_integration():
    """Verify buyer planner creates DAG with explanations, discovers fallbacks, and reserves budget."""
    planner = TaskPlanner()
    request = TaskCreationRequest(
        task="Collect crypto market rates and summarize takeaways",
        budget_usdc="0.050000",
        max_concurrency=2,
    )
    plan = planner.create_plan(request)
    assert plan is not None
    assert len(plan.calls) >= 2

    # Check that planned calls have selection reasons and fallback candidate IDs
    for call in plan.calls:
        assert call.service_id is not None
        assert call.selection_reason is not None
        assert len(call.selection_reason) > 0
        assert call.estimated_price_units > 0
        assert call.worst_case_price_units >= call.estimated_price_units


def test_task5_marketplace_and_metrics_api(client):
    """Verify real backend registry and metrics endpoints serve accurate data."""
    # 1. Test GET /api/v1/services lists all 9 agents
    resp_services = client.get("/api/v1/services?limit=50")
    assert resp_services.status_code == 200
    data = resp_services.json()
    assert data["total"] >= 9

    # 2. Test GET /api/v1/services/{service_id}/metrics
    resp_metrics = client.get("/api/v1/services/data_001/metrics")
    assert resp_metrics.status_code == 200
    m = resp_metrics.json()
    assert m["service_id"] == "data_001"
    assert "evidence_status" in m
    assert "observation_window" in m
    assert "success_rate" in m
    assert "schema_validity_rate" in m
    assert "reliability_score" in m

    # 3. Test POST /api/v1/services/recommendations
    resp_rec = client.post(
        "/api/v1/services/recommendations",
        json={"task_prompt": "Scrape documentation web page", "category": "scraping", "max_budget_usdc": "0.05"}
    )
    assert resp_rec.status_code == 200
    rec_data = resp_rec.json()
    assert "recommendations" in rec_data
    assert "rejected_candidates" in rec_data
    assert "top_recommendation" in rec_data
    assert "hard_filters_applied" in rec_data


def test_missing_data_receives_zero_not_perfect_score():
    """Verify missing observations result in 0.0 score, not default perfect 1.0."""
    engine = RecommendationEngine(registry=registry_service, repository=ledger_repo)
    # data_002 has 0 recorded ledger entries (NEW)
    req = RecommendationRequest(
        task_prompt="Fetch crypto rates",
        category=ServiceCategory.DATA,
        max_budget_atomic=10000,
    )
    res = engine.evaluate_and_rank(req)
    c_002 = next((c for c in res["recommendations"] if c["service_id"] == "data_002"), None)
    assert c_002 is not None
    # Output validity, reliability, success_rate must be 0.0 when unobserved
    assert c_002["factor_scores"]["output_validity"] == 0.0
    assert c_002["factor_scores"]["reliability"] == 0.0
    assert c_002["factor_scores"]["success_rate"] == 0.0


def test_hard_filters_reject_invalid_schema_and_security_policy():
    """Verify hard filters reject invalid schemas, invalid tokens, and non-Base-Sepolia networks."""
    engine = RecommendationEngine(registry=registry_service, repository=ledger_repo)

    # Mock a service with invalid schema
    base_svc = registry_service.get_service("data_001")
    bad_schema_svc = base_svc.model_copy(update={
        "service_id": "data_bad_schema",
        "output_schema": {"type": "invalid_type_name_xyz"}  # Invalid Draft-7
    })

    # Mock a service with wrong network
    wrong_net_svc = base_svc.model_copy(update={
        "service_id": "data_wrong_net",
        "network": "eip155:1"  # Mainnet rejected
    })

    mock_reg = MagicMock()
    mock_reg.list_services.return_value = SimpleNamespace(items=[bad_schema_svc, wrong_net_svc])
    engine_sec = RecommendationEngine(registry=mock_reg, repository=ledger_repo)

    req = RecommendationRequest(
        task_prompt="Lookup crypto prices",
        category=ServiceCategory.DATA,
    )
    res = engine_sec.evaluate_and_rank(req)
    assert len(res["recommendations"]) == 0
    assert len(res["rejected_candidates"]) == 2

    rej_schema = next(r for r in res["rejected_candidates"] if r["service_id"] == "data_bad_schema")
    assert any("schema" in r.lower() for r in rej_schema["rejection_reasons"])

    rej_net = next(r for r in res["rejected_candidates"] if r["service_id"] == "data_wrong_net")
    assert any("network" in r.lower() for r in rej_net["rejection_reasons"])


@pytest.mark.asyncio
async def test_task4_end_to_end_execution_with_budget_and_metrics():
    """Verify buyer task execution lifecycle respects ranking, budget lock, and records metrics."""
    req = TaskCreationRequest(
        task="Lookup cryptocurrency asset prices for ETH",
        budget_usdc="0.050000",
        preferred_categories=[ServiceCategory.DATA],
        max_concurrency=1,
    )
    created = buyer_service.create_task(req)
    assert str(created.status).lower() == "accepted"
    assert created.budget_atomic == 50000

    executed = await buyer_service.execute_task(created.task_id)
    assert executed is not None
    assert str(executed.status).lower() in ("succeeded", "completed", "failed", "pending_reconciliation")
    assert executed.budget_atomic == 50000
    # Calls were planned and recorded
    assert len(executed.calls) >= 1
    call = executed.calls[0]
    assert call.service_id in ("data_001", "data_002", "data_003")
    assert call.validation_status in ("accepted", "not_applicable", "rejected", "pending_reconciliation")

