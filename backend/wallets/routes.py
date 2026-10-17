"""FastAPI Router for Multi-Wallet Management."""
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.database.models import UserModel
from backend.auth.policy import get_current_user
from .schemas import (
    WalletChallengeRequest,
    WalletChallengeResponse,
    WalletLinkRequest,
    WalletResponse,
    WalletRoleUpdateRequest,
)
from .service import WalletService

router = APIRouter(prefix="/api/v1/wallets", tags=["Wallet Management"])


@router.post("/challenge", response_model=WalletChallengeResponse)
async def request_wallet_challenge(
    payload: WalletChallengeRequest,
    db: Session = Depends(get_db)
):
    """Generate server-side short-lived challenge for EVM wallet ownership verification."""
    challenge = WalletService.issue_challenge(db, payload.address, payload.wallet_type)
    return WalletChallengeResponse(
        nonce=challenge.nonce,
        address=challenge.address,
        challenge_text=challenge.challenge_text,
        expires_at=challenge.expires_at,
    )


@router.post("/link", response_model=WalletResponse, status_code=status.HTTP_201_CREATED)
async def link_wallet(
    payload: WalletLinkRequest,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify cryptographic signature on single-use challenge and link wallet to authenticated user."""
    link = WalletService.link_wallet(
        db=db,
        user_id=current_user.id,
        raw_address=payload.address,
        signature=payload.signature,
        nonce=payload.nonce,
        role=payload.role,
        wallet_type=payload.wallet_type,
        is_primary=payload.is_primary,
    )
    return WalletResponse(
        id=link.id,
        user_id=link.user_id,
        address=link.address,
        role=link.role,
        wallet_type=link.wallet_type,
        is_primary=link.is_primary,
        network=link.network,
        chain_id=link.chain_id,
        verified_at=link.verified_at,
    )


@router.get("", response_model=List[WalletResponse])
async def list_wallets(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all verified EVM wallets linked to the authenticated user."""
    wallets = WalletService.get_user_wallets(db, current_user.id)
    return [
        WalletResponse(
            id=w.id,
            user_id=w.user_id,
            address=w.address,
            role=w.role,
            wallet_type=w.wallet_type,
            is_primary=w.is_primary,
            network=w.network,
            chain_id=w.chain_id,
            verified_at=w.verified_at,
        )
        for w in wallets
    ]


@router.patch("/{wallet_id}", response_model=WalletResponse)
async def update_wallet(
    wallet_id: str,
    payload: WalletRoleUpdateRequest,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update role or primary status of a linked wallet."""
    wallet = WalletService.update_wallet(
        db=db,
        user_id=current_user.id,
        wallet_id=wallet_id,
        new_role=payload.role,
        is_primary=payload.is_primary,
    )
    return WalletResponse(
        id=wallet.id,
        user_id=wallet.user_id,
        address=wallet.address,
        role=wallet.role,
        wallet_type=wallet.wallet_type,
        is_primary=wallet.is_primary,
        network=wallet.network,
        chain_id=wallet.chain_id,
        verified_at=wallet.verified_at,
    )


@router.delete("/{wallet_id}", status_code=status.HTTP_200_OK)
async def unlink_wallet(
    wallet_id: str,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Safely unlink a wallet from the user's account."""
    WalletService.unlink_wallet(db, current_user.id, wallet_id)
    return {"message": f"Wallet '{wallet_id}' successfully unlinked."}
