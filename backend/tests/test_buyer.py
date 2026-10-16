"""Tests for Buyer Agent Task Planning and Execution."""
from fastapi import status
from backend.buyer.task_planner import TaskPlanner
from backend.buyer.service_selector import ServiceSelector
from backend.shared.constants import ServiceCategory


def test_task_planner_decomposition():
    planner = TaskPlanner()
    plan = planner.plan_task(
        prompt="Scrape ethereum article and summarize key takeaways",
        budget_usdc="0.05"
    )
    assert len(plan.steps) >= 2
    categories = [s.category for s in plan.steps]
    assert ServiceCategory.SCRAPING in categories
    assert ServiceCategory.INFERENCE in categories
    assert plan.estimated_total_units > 0


def test_service_selector():
    selector = ServiceSelector()
    # Market data is 2000 units
    service = selector.select_best_service(
        category=ServiceCategory.DATA,
        max_budget_units=5000
    )
    assert service is not None
    assert service.service_id == "data_001"

    # If max budget is only 1000 units, data_001 (2000 units) cannot be selected
    none_service = selector.select_best_service(
        category=ServiceCategory.DATA,
        max_budget_units=1000
    )
    assert none_service is None


def test_buyer_task_endpoint_success(client):
    response = client.post(
        "/api/v1/buyer/tasks",
        json={
            "task": "Collect crypto market data and summarize",
            "budget_usdc": "0.02"
        }
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "task_id" in data
    assert data["status"] == "completed"
    assert len(data["executions"]) >= 1
    assert "total_cost_usdc" in data
    assert "cost_explanation" in data
    assert "final_result" in data


def test_buyer_task_endpoint_budget_refusal(client):
    # Allocate tiny budget (0.0001 USDC = 100 base units) where services cost 2000+ units
    response = client.post(
        "/api/v1/buyer/tasks",
        json={
            "task": "Collect crypto market data and summarize",
            "budget_usdc": "0.0001"
        }
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "refused"
    assert "refused" in data["final_result"].lower()
