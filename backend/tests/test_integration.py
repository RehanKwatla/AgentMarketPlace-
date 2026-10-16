"""Integration Workflow Test Harness for DI-06."""
from fastapi import status


def test_end_to_end_marketplace_workflow(client):
    """Verifies complete loop: Discover -> Execute Task -> Audit Ledger -> Verify Reputation."""

    # 1. System Health
    health_res = client.get("/health")
    assert health_res.status_code == status.HTTP_200_OK

    # 2. Service Discovery
    services_res = client.get("/api/v1/services")
    assert services_res.status_code == status.HTTP_200_OK
    assert services_res.json()["total"] >= 3

    # 3. Buyer Agent Task Execution
    task_res = client.post(
        "/api/v1/buyer/tasks",
        json={
            "task": "Extract Ethereum data and summarize findings",
            "budget_usdc": "0.05"
        }
    )
    assert task_res.status_code == status.HTTP_200_OK
    task_data = task_res.json()
    assert task_data["status"] == "completed"
    assert len(task_data["executions"]) >= 1

    # 4. Check Reputation Endpoint
    rep_res = client.get("/api/v1/reputation")
    assert rep_res.status_code == status.HTTP_200_OK
    rep_data = rep_res.json()
    assert "data_001" in rep_data
    assert "scraping_001" in rep_data
    assert "inference_001" in rep_data
