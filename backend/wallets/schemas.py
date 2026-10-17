"""Pydantic Schemas for Multi-Wallet Management."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from backend.shared.constants import (
    NETWORK_BASE_SEPOLIA,
    CHAIN_ID_BASE_SEPOLIA,
    WalletRole,
    WalletType,
)


class WalletChallengeRequest(BaseModel):
    address: str = Field(..., description="EVM wallet address (0x...)")
    wallet_type: WalletType = WalletType.METAMASK


class WalletChallengeResponse(BaseModel):
    nonce: str
    address: str
    challenge_text: str
    expires_at: datetime
    network: str = NETWORK_BASE_SEPOLIA
    chain_id: int = CHAIN_ID_BASE_SEPOLIA


class WalletLinkRequest(BaseModel):
    address: str
    signature: str = Field(..., description="EIP-191 signature hex string (0x...)")
    nonce: str
    role: WalletRole = WalletRole.IDENTITY
    wallet_type: WalletType = WalletType.METAMASK
    is_primary: bool = False


class WalletResponse(BaseModel):
    id: str
    user_id: str
    address: str
    role: WalletRole
    wallet_type: WalletType
    is_primary: bool
    network: str
    chain_id: int
    verified_at: datetime


class WalletRoleUpdateRequest(BaseModel):
    role: Optional[WalletRole] = None
    is_primary: Optional[bool] = None


class WalletBalanceResponse(BaseModel):
    address: str
    network: str = NETWORK_BASE_SEPOLIA
    chain_id: int = CHAIN_ID_BASE_SEPOLIA
    token: str = "USDC"
    token_address: str = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
    balance_base_units: int = 0
    balance_usdc: str = "0.000000"
    native_balance_wei: str = "0"
    native_balance_eth: str = "0.000000"
    is_verified_onchain: bool = False
    source: str = "simulated_offline"
