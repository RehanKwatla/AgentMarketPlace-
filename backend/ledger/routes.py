"""Ledger and Reputation API Routes."""
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from backend.shared.schemas import (
    LedgerListResponse,
    LedgerRecordSchema,
    ReputationMetrics,
    PaymentReconciliationInput,
    ReconciliationResult,
)
from backend.ledger.models import ledger_repo
from backend.ledger.reputation import ReputationCalculator
from backend.ledger.reconciliation import reconciler

router = APIRouter(tags=["Ledger & Reputation"])
reputation_calc = reconciler.reputation_calc


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


@router.post(
    "/api/v1/ledger/reconcile",
    response_model=ReconciliationResult,
    summary="Reconcile a payment execution and update ledger & reputation"
)
async def reconcile_payment(payload: PaymentReconciliationInput):
    """Audits and reconciles a payment. Reaches PAID only upon verified settlement evidence."""
    return await reconciler.reconcile_payment(payload)


@router.get(
    "/api/v1/reputation",
    response_model=Dict[str, ReputationMetrics],
    summary="Get reputation metrics for all services"
)
async def get_all_reputations():
    return reputation_calc.calculate_all()


@router.get(
    "/api/v1/reputation/pending-repairs",
    response_model=List[str],
    summary="List service IDs requiring reputation telemetry repair"
)
async def get_pending_repairs():
    return reconciler.get_pending_repairs()


@router.get(
    "/api/v1/reputation/{service_id}",
    response_model=ReputationMetrics,
    summary="Get reputation metric for a single service"
)
async def get_service_reputation(service_id: str):
    return reputation_calc.calculate_for_service(service_id)


@router.post(
    "/api/v1/reputation/repair/{service_id}",
    response_model=ReputationMetrics,
    summary="Retryable recovery: repair reputation metrics for a service"
)
async def repair_service_reputation(service_id: str):
    return reconciler.repair_reputation(service_id)


@router.post(
    "/api/v1/reputation/repair",
    response_model=Dict[str, ReputationMetrics],
    summary="Retryable recovery: repair reputation metrics for all services"
)
async def repair_all_reputations():
    return reconciler.repair_reputation()
