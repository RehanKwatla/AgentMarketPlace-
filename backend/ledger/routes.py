"""Ledger and Reputation API Routes."""
from typing import Dict, Optional
from fastapi import APIRouter, HTTPException, Query, status
from backend.shared.schemas import (
    LedgerListResponse,
    LedgerRecordSchema,
    ReputationMetrics,
)
from backend.ledger.models import ledger_repo
from backend.ledger.reputation import ReputationCalculator

router = APIRouter(tags=["Ledger & Reputation"])
reputation_calc = ReputationCalculator(ledger_repo)


@router.get(
    "/api/v1/ledger",
    response_model=LedgerListResponse,
    summary="Query audit ledger transactions"
)
async def list_ledger_records(
    status: Optional[str] = Query(None, description="Filter by status (paid, paid output rejected, refused, failed and not charged)"),
    service_id: Optional[str] = Query(None, description="Filter by service_id"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    records = ledger_repo.list_records(
        status=status,
        service_id=service_id,
        limit=limit,
        offset=offset
    )
    total = ledger_repo.count(status=status, service_id=service_id)
    return LedgerListResponse(total=total, records=records)


@router.get(
    "/api/v1/ledger/{request_id}",
    response_model=LedgerRecordSchema,
    summary="Get individual ledger record"
)
async def get_ledger_record(request_id: str):
    record = ledger_repo.get_record(request_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ledger record with request_id '{request_id}' not found."
        )
    return record


@router.get(
    "/api/v1/reputation",
    response_model=Dict[str, ReputationMetrics],
    summary="Get reputation metrics for all services"
)
async def get_all_reputations():
    return reputation_calc.calculate_all()


@router.get(
    "/api/v1/reputation/{service_id}",
    response_model=ReputationMetrics,
    summary="Get reputation metric for a single service"
)
async def get_service_reputation(service_id: str):
    return reputation_calc.calculate_for_service(service_id)
