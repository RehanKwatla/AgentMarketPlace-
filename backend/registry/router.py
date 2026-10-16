"""FastAPI Router for the Service Registry subsystem."""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import JSONResponse
from backend.registry.schemas import (
    ServiceRecord,
    ServiceListResponse,
    ServiceReputationSummary,
)
from backend.registry.service import registry_service

router = APIRouter(prefix="/api/v1/services", tags=["Service Registry"])


@router.get(
    "",
    response_model=ServiceListResponse,
    summary="Search & Filter Registered Seller Services",
    description="Discover active seller agent microservices by category, max/min price, text query, and active status."
)
async def list_services(
    category: Optional[str] = Query(None, description="Filter by category: data, scraping, or inference"),
    max_price_usdc: Optional[str] = Query(None, description="Maximum per-call price in decimal USDC (e.g. '0.003000')"),
    min_price_usdc: Optional[str] = Query(None, description="Minimum per-call price in decimal USDC"),
    active: Optional[bool] = Query(True, description="Filter by active status (default: true)"),
    enabled: Optional[bool] = Query(None, description="Alias for active filter"),
    q: Optional[str] = Query(None, description="Text search across service name, description, and keywords"),
    limit: int = Query(20, ge=1, le=100, description="Pagination limit"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
):
    # Support both 'active' and 'enabled' query parameter names
    is_active = enabled if enabled is not None else active

    response = registry_service.list_services(
        category=category,
        max_price_usdc=max_price_usdc,
        min_price_usdc=min_price_usdc,
        active=is_active,
        q=q,
        limit=limit,
        offset=offset,
    )
    # Return dictionary with both 'items' and 'services' for full contract compatibility
    return JSONResponse(status_code=status.HTTP_200_OK, content=response.model_dump())


@router.get(
    "/{service_id}",
    response_model=ServiceRecord,
    summary="Get Service Metadata by ID",
    description="Retrieve a single seller agent's full specification, JSON schemas, terms, and payment addresses."
)
async def get_service(service_id: str):
    service = registry_service.get_service(service_id)
    if not service:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Service with ID '{service_id}' was not found in the registry.",
                    "details": {"service_id": service_id}
                }
            }
        )
    return JSONResponse(status_code=status.HTTP_200_OK, content=service.model_dump())


@router.get(
    "/{service_id}/reputation",
    response_model=ServiceReputationSummary,
    summary="Get Service Reputation Summary",
    description="Retrieve observed reliability, success rate, median latency, and call history for a seller."
)
async def get_service_reputation(service_id: str):
    reputation = registry_service.get_reputation(service_id)
    if not reputation:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Reputation records for service '{service_id}' were not found.",
                    "details": {"service_id": service_id}
                }
            }
        )
    return JSONResponse(status_code=status.HTTP_200_OK, content=reputation.model_dump())
