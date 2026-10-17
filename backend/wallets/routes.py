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
    WalletBalanceResponse,
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


@router.get("/{address}/balance", response_model=WalletBalanceResponse, summary="Get EVM Wallet Balance on Base Sepolia")
async def get_wallet_balance(address: str):
    """Retrieve on-chain USDC and ETH balance for an EVM wallet on Base Sepolia.

    Resilient fallback: If RPC is unreachable or in offline test environment,
    returns valid structure with is_verified_onchain=False and source='simulated_offline'.
    """
    from .verifier import normalize_address
    from backend.shared.config import get_settings
    from backend.shared.constants import (
        NETWORK_BASE_SEPOLIA,
        CHAIN_ID_BASE_SEPOLIA,
        USDC_BASE_SEPOLIA,
        base_units_to_usdc,
    )
    import httpx

    try:
        norm_addr = normalize_address(address)
    except Exception:
        norm_addr = address

    settings = get_settings()
    rpc_url = getattr(settings, "base_sepolia_rpc_url", "https://sepolia.base.org")

    usdc_units = 0
    native_wei = 0
    is_verified = False
    source = "simulated_offline"

    try:
        clean_addr = norm_addr.lower()
        if clean_addr.startswith("0x") and len(clean_addr) == 42:
            async with httpx.AsyncClient(timeout=3.0) as client:
                eth_resp = await client.post(
                    rpc_url,
                    json={
                        "jsonrpc": "2.0",
                        "method": "eth_getBalance",
                        "params": [norm_addr, "latest"],
                        "id": 1,
                    }
                )
                if eth_resp.status_code == 200:
                    eth_data = eth_resp.json()
                    if "result" in eth_data and isinstance(eth_data["result"], str):
                        native_wei = int(eth_data["result"], 16)
                        is_verified = True
                        source = "rpc"

                padded_addr = norm_addr[2:].lower().rjust(64, "0")
                data_hex = f"0x70a08231{padded_addr}"
                usdc_resp = await client.post(
                    rpc_url,
                    json={
                        "jsonrpc": "2.0",
                        "method": "eth_call",
                        "params": [{"to": USDC_BASE_SEPOLIA, "data": data_hex}, "latest"],
                        "id": 2,
                    }
                )
                if usdc_resp.status_code == 200:
                    usdc_data = usdc_resp.json()
                    if "result" in usdc_data and isinstance(usdc_data["result"], str):
                        usdc_units = int(usdc_data["result"], 16)
                        is_verified = True
                        source = "rpc"
    except Exception:
        pass

    native_eth_str = f"{(native_wei / 1e18):.6f}" if native_wei > 0 else "0.000000"

    return WalletBalanceResponse(
        address=norm_addr,
        network=NETWORK_BASE_SEPOLIA,
        chain_id=CHAIN_ID_BASE_SEPOLIA,
        token="USDC",
        token_address=USDC_BASE_SEPOLIA,
        balance_base_units=usdc_units,
        balance_usdc=base_units_to_usdc(usdc_units),
        native_balance_wei=str(native_wei),
        native_balance_eth=native_eth_str,
        is_verified_onchain=is_verified,
        source=source,
    )

