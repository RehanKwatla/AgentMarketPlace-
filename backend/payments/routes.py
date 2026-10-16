"""[IMPLEMENTED] Payment Subsystem Routes (Member 1)."""
from typing import Any, Dict
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from backend.payments.service import payment_service
from backend.payments.errors import PaymentEngineError

router = APIRouter(prefix="/api/v1/payments", tags=["Payments"])


@router.get("/status", summary="Check payment subsystem status")
async def get_payment_status():
    """Returns current state of x402 payment subsystem."""
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "module": "payments",
            "status": "operational",
            "protocol_version": "2.0",
            "network": "eip155:84532",
            "facilitator_configured": True,
            "pending_reconciliations_count": len(payment_service.get_pending_reconciliations()),
        }
    )


@router.get("/reconciliations", summary="List pending payment reconciliations")
async def list_pending_reconciliations():
    """Returns all payment attempts currently held in suspense pending on-chain reconciliation."""
    pending = payment_service.get_pending_reconciliations()
    serialized = {k: v.model_dump(mode="json") for k, v in pending.items()}
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"pending_reconciliations": serialized, "total": len(serialized)}
    )


@router.post("/reconcile/{attempt_id}", summary="Authoritatively reconcile an uncertain payment attempt")
async def reconcile_payment_attempt(attempt_id: str):
    """Trigger authoritative re-query of on-chain / facilitator evidence for a pending attempt.

    Applies permitted state transitions only:
    - Confirmed on-chain -> PAID (commits budget, updates ledger).
    - Reverted / definitively failed -> FAILED_AND_NOT_CHARGED (releases budget).
    - Unresolved -> retains PENDING_RECONCILIATION.
    """
    try:
        outcome = await payment_service.reconcile_attempt(attempt_id)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=outcome
        )
    except PaymentEngineError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc)
        )


@router.post("/reconcile", summary="Batch reconcile all pending payment attempts")
async def batch_reconcile_pending_attempts():
    """Trigger authoritative re-query of all attempts currently held in suspense."""
    results = await payment_service.reconcile_all_pending()
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"reconciled_attempts": results, "total": len(results)}
    )
