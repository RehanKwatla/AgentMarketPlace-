"""Tests for Service Registry and Discovery."""
from fastapi import status


def test_list_services(client):
    response = client.get("/api/v1/services")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "services" in data
    assert data["total"] >= 3
    service_ids = [s["service_id"] for s in data["services"]]
    assert "data_001" in service_ids
    assert "scraping_001" in service_ids
    assert "inference_001" in service_ids


def test_service_schema_validation(client):
    response = client.get("/api/v1/services/data_001")
    assert response.status_code == status.HTTP_200_OK
    service = response.json()
    assert service["service_id"] == "data_001"
    assert service["category"] == "data"
    assert service["network"] == "eip155:84532"
    assert service["price_usdc"] == "0.002"
    assert service["price_base_units"] == 2000
    assert "pay_to" in service
    assert "input_schema" in service
    assert "output_schema" in service


def test_registry_category_filtering(client):
    response = client.get("/api/v1/services?category=scraping")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    for s in data["services"]:
        assert s["category"] == "scraping"


def test_registry_price_filtering(client):
    # Max price 0.0025 should include data_001 (0.002), but not scraping_001 (0.003) or inference_001 (0.004)
    response = client.get("/api/v1/services?max_price_usdc=0.0025")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 1
    assert data["services"][0]["service_id"] == "data_001"


def test_service_not_found(client):
    response = client.get("/api/v1/services/unknown_service_999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
