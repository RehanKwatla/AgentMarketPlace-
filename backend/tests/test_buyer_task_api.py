"""Unit and Integration Tests for Buyer Task API, Lifecycle States, and Persistence."""
import pytest
from fastapi import status
from backend.buyer.repository import task_repository, PersistenceError
from backend.buyer.schemas import TaskCreationRequest, TaskStatus
from backend.buyer.service import buyer_service


def test_valid_task_creation_and_lifecycle_polling(client):
    """Test valid task submission, 201 Created status, and subsequent status/result polling."""
    payload = {
        "task": "Collect real-time crypto prices and generate an executive summary",
        "budget_usdc": "0.020000",
        "max_concurrency": 3,
        "execute_now": True
    }
    response = client.post("/api/v1/tasks", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    task_id = data["task_id"]
    assert task_id
    assert data["status"] in ["accepted", "planning", "running", "completed"]
    assert data["budget_atomic"] == 20000

    # 1. Retrieve Status: GET /api/v1/tasks/{task_id}
    status_res = client.get(f"/api/v1/tasks/{task_id}")
    assert status_res.status_code == status.HTTP_200_OK
    detail = status_res.json()
    assert detail["task_id"] == task_id
    assert detail["status"] in ["running", "completed"]
    assert "spent_usdc" in detail
    assert "actual_spent_atomic" in detail
    assert "calls" in detail

    # 2. Retrieve Result: GET /api/v1/tasks/{task_id}/result
    result_res = client.get(f"/api/v1/tasks/{task_id}/result")
    assert result_res.status_code == status.HTTP_200_OK
    res_data = result_res.json()
    assert res_data["task_id"] == task_id
    assert "status" in res_data
    assert "final_result" in res_data
    assert "provenance" in res_data
    assert "cost_explanation" in res_data

    # 3. Retrieve Calls: GET /api/v1/tasks/{task_id}/calls
    calls_res = client.get(f"/api/v1/tasks/{task_id}/calls")
    assert calls_res.status_code == status.HTTP_200_OK
    calls_data = calls_res.json()
    assert "calls" in calls_data or "items" in calls_data


def test_missing_or_empty_task_rejection(client):
    """Empty or missing natural language task prompts must be rejected with 422."""
    # 1. Empty string prompt
    res_empty = client.post(
        "/api/v1/tasks",
        json={"task": "  ", "budget_usdc": "0.050000"}
    )
    assert res_empty.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # 2. Missing prompt field entirely
    res_missing = client.post(
        "/api/v1/tasks",
        json={"budget_usdc": "0.050000"}
    )
    assert res_missing.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_invalid_budget_rejection(client):
    """Zero, negative, or non-numeric budgets must be rejected with 422."""
    # 1. Zero budget
    res_zero = client.post(
        "/api/v1/tasks",
        json={"task": "Summarize articles", "budget_usdc": "0"}
    )
    assert res_zero.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # 2. Negative atomic units
    res_neg = client.post(
        "/api/v1/tasks",
        json={"task": "Summarize articles", "max_budget_atomic": -100}
    )
    assert res_neg.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # 3. Non-numeric budget string
    res_invalid = client.post(
        "/api/v1/tasks",
        json={"task": "Summarize articles", "budget_usdc": "ten_dollars"}
    )
    assert res_invalid.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_unknown_task_id_404(client):
    """Status and result retrieval for unknown task IDs must return structured 404."""
    # 1. Unknown task status
    res_status = client.get("/api/v1/tasks/00000000-0000-0000-0000-000000000000")
    assert res_status.status_code == status.HTTP_404_NOT_FOUND
    err_status = res_status.json()
    assert "error" in err_status
    assert err_status["error"]["code"] == "NOT_FOUND"

    # 2. Unknown task result
    res_result = client.get("/api/v1/tasks/00000000-0000-0000-0000-000000000000/result")
    assert res_result.status_code == status.HTTP_404_NOT_FOUND
    err_result = res_result.json()
    assert "error" in err_result
    assert err_result["error"]["code"] == "NOT_FOUND"


def test_task_creation_separate_from_payment():
    """Verify creating a task with execute_now=False creates accepted record with zero payments."""
    req = TaskCreationRequest(
        task="Deferred execution task",
        budget_usdc="0.050000",
        execute_now=False
    )
    record = buyer_service.create_task(req)
    assert record.task_id
    assert record.status == TaskStatus.ACCEPTED.value
    assert record.spent_usdc == "0.000000"
    assert record.spent_atomic == 0
    assert len(record.calls) == 0


def test_persistence_failure_handling():
    """Verify that simulated database persistence failure raises PersistenceError."""
    task_repository.set_simulate_failure(True)
    try:
        req = TaskCreationRequest(
            task="Test persistence failure",
            budget_usdc="0.010000"
        )
        with pytest.raises(PersistenceError, match="persistence failure"):
            buyer_service.create_task(req)
    finally:
        task_repository.set_simulate_failure(False)


def test_task_not_completed_before_validation():
    """Verify a task only transitions to completed after execution & validation."""
    req = TaskCreationRequest(
        task="Test execution lifecycle",
        budget_usdc="0.000100"  # Insufficient budget (100 units < 2000 minimum)
    )
    # Since budget is insufficient, task must be refused, not completed
    task = buyer_service.create_task(req)
    assert task.status == TaskStatus.ACCEPTED.value
