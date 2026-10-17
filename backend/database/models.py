"""Persistent SQLAlchemy Models for Ledger, Services, and Tasks."""
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Boolean
from backend.database.session import Base
from backend.shared.constants import (
    LedgerStatus,
    NETWORK_BASE_SEPOLIA,
    USDC_BASE_SEPOLIA,
)


class LedgerRecordModel(Base):
    """Immutable audit record for every pay-per-call service request."""
    __tablename__ = "ledger_records"

    request_id = Column(String(64), primary_key=True, index=True)
    task_id = Column(String(64), index=True, nullable=True)
    call_id = Column(String(64), index=True, nullable=True)
    payment_id = Column(String(64), index=True, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    buyer_id = Column(String(64), nullable=False, index=True)
    seller_id = Column(String(64), nullable=False, index=True)
    service_id = Column(String(64), nullable=False, index=True)
    listed_price = Column(String(32), nullable=False)
    amount_paid = Column(String(32), nullable=False)
    listed_price_units = Column(Integer, nullable=True)
    amount_paid_units = Column(Integer, nullable=True)
    amount_base_units = Column(Integer, nullable=True, default=0)
    tx_hash = Column(String(128), nullable=True, index=True)
    settlement_proof = Column(Text, nullable=True)
    network = Column(String(64), nullable=True, default=NETWORK_BASE_SEPOLIA)
    token = Column(String(64), nullable=True, default=USDC_BASE_SEPOLIA)
    token_address = Column(String(128), nullable=True)
    status = Column(String(32), nullable=False, index=True)
    latency_ms = Column(Float, nullable=False, default=0.0)
    error_reason = Column(Text, nullable=True)


class SellerReputationModel(Base):
    """Persistent aggregated telemetry and reputation scores for sellers."""
    __tablename__ = "seller_reputation"

    service_id = Column(String(64), primary_key=True, index=True)
    total_calls = Column(Integer, default=0, nullable=False)
    successful_calls = Column(Integer, default=0, nullable=False)
    success_rate = Column(Float, default=1.0, nullable=False)
    median_latency_ms = Column(Float, default=0.0, nullable=False)
    failure_counts = Column(Integer, default=0, nullable=False)
    schema_invalid_counts = Column(Integer, default=0, nullable=False)
    reputation_score = Column(Float, default=100.0, nullable=False)
    total_volume_units = Column(Integer, default=0, nullable=False)
    total_volume_usdc = Column(String(32), default="0.000000", nullable=False)
    sync_status = Column(String(32), default="synced", nullable=False)
    last_error = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class ServiceRecordModel(Base):
    """Persistent catalog records for registered seller services."""
    __tablename__ = "services"

    service_id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    category = Column(String(32), nullable=False, index=True)
    endpoint_url = Column(String(512), nullable=False)
    price_usdc = Column(String(32), nullable=False)
    price_base_units = Column(Integer, nullable=False)
    network = Column(String(64), nullable=False)
    pay_to = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    input_schema_json = Column(Text, nullable=True)
    output_schema_json = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)


class TaskRecordModel(Base):
    """Records for high-level buyer task sessions."""
    __tablename__ = "tasks"

    task_id = Column(String(64), primary_key=True, index=True)
    task_prompt = Column(Text, nullable=False)
    budget_usdc = Column(String(32), nullable=False)
    total_cost_usdc = Column(String(32), default="0.000000")
    status = Column(String(32), nullable=False)
    failure_reason = Column(Text, nullable=True)
    final_result = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# --- Phase 3: Auth, Multi-Wallet, and KYC Models ---

class UserModel(Base):
    """User account entity with credentials and status."""
    __tablename__ = "users"

    id = Column(String(64), primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(32), default="user", nullable=False)  # "user", "admin", "seller"
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class EmailVerificationTokenModel(Base):
    """Single-use email verification tokens."""
    __tablename__ = "email_verification_tokens"

    token = Column(String(128), primary_key=True, index=True)
    user_id = Column(String(64), index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class PasswordResetTokenModel(Base):
    """Single-use password recovery tokens."""
    __tablename__ = "password_reset_tokens"

    token = Column(String(128), primary_key=True, index=True)
    user_id = Column(String(64), index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class RevokedTokenModel(Base):
    """Token revocation blacklist (jti) for instant logout and session revocation."""
    __tablename__ = "revoked_tokens"

    jti = Column(String(128), primary_key=True, index=True)
    user_id = Column(String(64), index=True, nullable=False)
    revoked_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at = Column(DateTime, nullable=False)


class WalletChallengeModel(Base):
    """Server-generated, short-lived, single-use signed challenges for EVM wallet verification."""
    __tablename__ = "wallet_challenges"

    nonce = Column(String(64), primary_key=True, index=True)
    address = Column(String(64), index=True, nullable=False)
    challenge_text = Column(Text, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class WalletLinkModel(Base):
    """Linked EVM wallet addresses mapped to accounts with distinct roles."""
    __tablename__ = "wallet_links"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), index=True, nullable=False)
    address = Column(String(64), index=True, nullable=False)  # Normalized checksum address
    role = Column(String(32), default="identity", nullable=False)  # "identity", "payment", "receiving"
    wallet_type = Column(String(32), default="metamask", nullable=False)  # "metamask", "coinbase", "other"
    is_primary = Column(Boolean, default=False, nullable=False)
    network = Column(String(64), default=NETWORK_BASE_SEPOLIA, nullable=False)
    chain_id = Column(Integer, default=84532, nullable=False)
    verified_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class KycRecordModel(Base):
    """Provider-neutral KYC verification record for account identity status."""
    __tablename__ = "kyc_records"

    user_id = Column(String(64), primary_key=True, index=True)
    status = Column(String(32), default="NOT_STARTED", nullable=False)  # NOT_STARTED, PENDING, VERIFIED, REJECTED, REQUIRES_REVIEW, EXPIRED
    provider = Column(String(64), default="mock_simulated", nullable=False)
    provider_reference_id = Column(String(128), index=True, nullable=True)
    is_simulated = Column(Boolean, default=True, nullable=False)
    simulation_disclaimer = Column(Text, default="SIMULATED - NOT REAL-WORLD IDENTITY VERIFICATION", nullable=False)
    rejection_reasons = Column(Text, nullable=True)
    session_url = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    verified_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)


class KycAuditModel(Base):
    """Audit trail for all KYC state transitions and provider webhook events."""
    __tablename__ = "kyc_audit_log"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), index=True, nullable=False)
    from_status = Column(String(32), nullable=False)
    to_status = Column(String(32), nullable=False)
    provider = Column(String(64), nullable=False)
    provider_reference_id = Column(String(128), nullable=True)
    reason = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

