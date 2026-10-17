"""FastAPI Endpoints validating Access Policy Gates for DI-06."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.database.models import UserModel, WalletLinkModel
from .policy import (
    get_current_user,
    require_kyc_verified,
    require_payment_wallet,
    require_admin,
)

router = APIRouter(prefix="/api/v1/policy", tags=["Access Policy"])


@router.get("/public-browse", status_code=status.HTTP_200_OK)
async def public_browse():
    """Policy Rule: Browsing catalog, services, categories, and ledger is public."""
    return {
        "access": "granted",
        "policy": "public_browsing",
        "requires_auth": False,
        "requires_kyc": False,
    }


@router.post("/buyer-task-gate", status_code=status.HTTP_200_OK)
async def buyer_task_gate(
    wallet: WalletLinkModel = Depends(require_payment_wallet),
    current_user: UserModel = Depends(get_current_user),
):
    """Policy Rule: Buyer task submission requires authenticated user and verified payment wallet."""
    return {
        "access": "granted",
        "policy": "buyer_task_submission",
        "user_id": current_user.id,
        "payment_wallet": wallet.address,
    }


@router.post("/seller-registration-gate", status_code=status.HTTP_200_OK)
async def seller_registration_gate(
    current_user: UserModel = Depends(require_kyc_verified),
):
    """Policy Rule: Seller registration requires authenticated user with completed KYC verification."""
    return {
        "access": "granted",
        "policy": "seller_registration",
        "user_id": current_user.id,
        "role": current_user.role,
        "kyc_verified": True,
    }


@router.post("/kyc-gate", status_code=status.HTTP_200_OK)
async def kyc_gate(
    current_user: UserModel = Depends(require_kyc_verified),
):
    """Policy Rule: KYC-gated sensitive actions require KYC status VERIFIED."""
    return {
        "access": "granted",
        "policy": "kyc_gated_action",
        "user_id": current_user.id,
    }


@router.post("/admin-gate", status_code=status.HTTP_200_OK)
async def admin_gate(
    current_user: UserModel = Depends(require_admin),
):
    """Policy Rule: Administrative controls require administrator role."""
    return {
        "access": "granted",
        "policy": "administrative_controls",
        "user_id": current_user.id,
        "role": current_user.role,
    }
