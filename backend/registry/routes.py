"""Service Registry REST Endpoints matching API_CONTRACTS.md."""
from typing import Optional
from fastapi import APIRouter, Query, status
from fastapi.responses import JSONResponse
from backend.registry.schemas import (
    ServiceRecord,
    ServiceListResponse,
    ServiceReputationSummary,
)
from backend.registry.service import registry_service
from backend.registry.recommendation import RecommendationRequest, recommendation_engine

router = APIRouter(prefix="/api/v1/services", tags=["Service Registry"])


@router.post("/recommendations", summary="Rank eligible registered agents")
async def recommend_services(request: RecommendationRequest):
    """Return a deterministic candidate ranking; this endpoint does not initiate payment."""
    return recommendation_engine.evaluate_and_rank(request)


@router.get(
    "",
    response_model=ServiceListResponse,
    summary="List and Filter Registered Services",
    description="Discover active seller microservices by category, capability, price range, text search, and enabled status."
)
async def list_services(
    category: Optional[str] = Query(None, description="Filter by category (data, scraping, inference)"),
    max_price_usdc: Optional[str] = Query(None, description="Filter by maximum price in USDC (e.g. '0.003000')"),
    min_price_usdc: Optional[str] = Query(None, description="Filter by minimum price in USDC"),
    active: Optional[bool] = Query(None, description="Filter by active status"),
    enabled: Optional[bool] = Query(None, description="Filter by enabled status (alias for active)"),
    capability: Optional[str] = Query(None, description="Filter by capability URI, e.g. 'data.lookup.v1'"),
    q: Optional[str] = Query(None, description="Text/capability search across service name, description, and keywords"),
    limit: int = Query(20, ge=1, le=100, description="Pagination limit"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
):
    # Default active/enabled filter to None so callers can list all if specified, or default to active
    response = registry_service.list_services(
        category=category,
        max_price_usdc=max_price_usdc,
        min_price_usdc=min_price_usdc,
        active=active,
        enabled=enabled,
        capability=capability,
        q=q,
        limit=limit,
        offset=offset,
    )
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
    description="Retrieve observed reliability, success rate, median latency, and call history for a seller via Member 4."
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
