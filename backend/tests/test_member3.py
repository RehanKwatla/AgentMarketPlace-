"""Comprehensive Unit and Integration Tests for Member 3: Service Registry & Buyer Agent."""
import pytest
from fastapi import status


def test_registry_filters_text_query(client):
    """Test searching services by capability/text query."""
    response = client.get("/api/v1/services?q=market")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    items = data.get("services") or data.get("items")
    assert len(items) >= 1
    assert any("data" in item["service_id"] for item in items)


def test_registry_filters_min_max_price(client):
    """Test min_price_usdc and max_price_usdc filters."""
    # Data is 0.002, scraping is 0.003, inference is 0.004
    response = client.get("/api/v1/services?min_price_usdc=0.0025&max_price_usdc=0.0035")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    items = data.get("services") or data.get("items")
    assert len(items) == 1
    assert "scraping" in items[0]["service_id"]


def test_registry_reputation_endpoint(client):
    """Test GET /api/v1/services/{service_id}/reputation."""
    response = client.get("/api/v1/services/data_001/reputation")
    assert response.status_code == status.HTTP_200_OK
    rep = response.json()
    assert rep["service_id"] == "data_001"
    assert "reputation_score" in rep
    assert "success_rate" in rep
    assert "latency_p95_ms" in rep


def test_registry_reputation_not_found(client):
    """Test GET /api/v1/services/{service_id}/reputation for invalid ID."""
    response = client.get("/api/v1/services/non_existent_999/reputation")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_buyer_task_creation_and_polling(client):
    """Test POST /api/v1/tasks, GET /api/v1/tasks/{task_id}, result, and calls endpoints."""
    # Submit a task via canonical /api/v1/tasks endpoint
    response = client.post(
        "/api/v1/tasks",
        json={
            "description": "Scrape trending crypto news and generate an AI summary",
            "max_budget_atomic": 20000,
            "required_categories": ["scraping", "inference"],
            "max_concurrency": 3
        }
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    task_id = data["task_id"]
    assert task_id
    assert data["status"] in ["created", "planning", "executing", "completed"]

    # Poll status: GET /api/v1/tasks/{task_id}
    detail_res = client.get(f"/api/v1/tasks/{task_id}")
    assert detail_res.status_code == status.HTTP_200_OK
    detail = detail_res.json()
    assert detail["task_id"] == task_id
    assert "status" in detail
    assert "actual_spent_atomic" in detail

    # Get calls: GET /api/v1/tasks/{task_id}/calls
    calls_res = client.get(f"/api/v1/tasks/{task_id}/calls")
    assert calls_res.status_code == status.HTTP_200_OK
    calls_data = calls_res.json()
    assert "calls" in calls_data

    # Get result: GET /api/v1/tasks/{task_id}/result
    result_res = client.get(f"/api/v1/tasks/{task_id}/result")
    assert result_res.status_code == status.HTTP_200_OK
    result_data = result_res.json()
    assert "status" in result_data
    assert "final_result" in result_data
    assert "cost_explanation" in result_data


def test_buyer_task_rejection_negative_budget(client):
    """Test rejection when budget is zero or negative."""
    response = client.post(
        "/api/v1/tasks",
        json={
            "description": "Perform analysis",
            "max_budget_atomic": 0
        }
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_buyer_task_rejection_excessive_concurrency(client):
    """Test rejection when max_concurrency exceeds safe limits."""
    response = client.post(
        "/api/v1/tasks",
        json={
            "description": "Perform analysis",
            "max_budget_atomic": 10000,
            "max_concurrency": 25
        }
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_buyer_task_budget_exceeded_refusal(client):
    """Test plan refusal when worst-case cost exceeds max budget."""
    # max_budget_atomic of 500 units is less than minimum service price (2000 units)
    response = client.post(
        "/api/v1/tasks",
        json={
            "description": "Fetch real-time financial market data",
            "max_budget_atomic": 500,
            "required_categories": ["data"]
        }
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    task_id = data["task_id"]

    detail_res = client.get(f"/api/v1/tasks/{task_id}")
    detail = detail_res.json()
    assert detail["status"] in ["failed", "refused"]
    assert "budget" in (detail.get("failure_reason") or "").lower()


def test_output_validator_rejection():
    """Test output validator rejects payloads not conforming to JSON draft-7 schema."""
    from backend.buyer.output_validator import OutputValidator

    schema = {
        "type": "object",
        "required": ["symbol", "price_usd"],
        "properties": {
            "symbol": {"type": "string"},
            "price_usd": {"type": "number"}
        }
    }

    # Valid payload
    assert OutputValidator.validate_seller_output({"symbol": "ETH", "price_usd": 3200.5}, schema) is True

    # Invalid payload missing required field
    assert OutputValidator.validate_seller_output({"symbol": "ETH"}, schema) is False

    # Invalid payload wrong type
    assert OutputValidator.validate_seller_output({"symbol": "ETH", "price_usd": "three thousand"}, schema) is False
