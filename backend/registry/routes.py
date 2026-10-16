"""Service Registry Endpoints."""
from typing import Optional
from fastapi import APIRouter, Query, status
from backend.shared.schemas import ServiceDefinition, ServiceListResponse
from backend.shared.errors import ServiceNotFoundError
from backend.registry.service_catalog import catalog

router = APIRouter(prefix="/api/v1/services", tags=["Registry"])


@router.get("", response_model=ServiceListResponse, summary="List available services")
async def list_services(
    category: Optional[str] = Query(None, description="Filter by category (data, scraping, inference)"),
    max_price_usdc: Optional[str] = Query(None, description="Filter by maximum price in USDC"),
    is_active: Optional[bool] = Query(True, description="Filter by active status"),
):
    services = catalog.list_services(
        category=category,
        max_price_usdc=max_price_usdc,
        is_active=is_active
    )
    return ServiceListResponse(services=services, total=len(services))


@router.get("/{service_id}", response_model=ServiceDefinition, summary="Get service by ID")
async def get_service_by_id(service_id: str):
    service = catalog.get_service(service_id)
    if not service:
        raise ServiceNotFoundError(service_id)
    return service
