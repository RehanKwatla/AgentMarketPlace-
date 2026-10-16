"""Tests for Health and System Diagnostics Endpoints."""
from fastapi import status


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "healthy"
    assert data["network"] == "eip155:84532"
    assert "version" in data
    assert "timestamp" in data
    assert "database" in data["services"]


def test_openapi_available(client):
    response = client.get("/openapi.json")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "paths" in data
    assert "/health" in data["paths"]
    assert "/api/v1/services" in data["paths"]
    assert "/api/v1/buyer/tasks" in data["paths"]
    assert "/api/v1/seller/data" in data["paths"]
    assert "/api/v1/seller/scraping" in data["paths"]
    assert "/api/v1/seller/inference" in data["paths"]
    assert "/api/v1/ledger" in data["paths"]
