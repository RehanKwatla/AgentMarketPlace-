"""Pydantic Schemas for Authentication and User Accounts."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


class UserSignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, description="Minimum 8 characters password")


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class EmailVerificationRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class UserSummaryResponse(BaseModel):
    id: str
    email: str
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: UserSummaryResponse


class UserProfileResponse(UserSummaryResponse):
    linked_wallets_count: int = 0
    active_payment_wallet: Optional[str] = None
    kyc_status: str = "NOT_STARTED"
    is_kyc_simulated: bool = True
