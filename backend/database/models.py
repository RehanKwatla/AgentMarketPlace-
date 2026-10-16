"""Persistent SQLAlchemy Models for Ledger, Services, and Tasks."""
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Boolean
from backend.database.session import Base
from backend.shared.constants import LedgerStatus


class LedgerRecordModel(Base):
    """Immutable audit record for every pay-per-call service request."""
    __tablename__ = "ledger_records"

    request_id = Column(String(64), primary_key=True, index=True)
    task_id = Column(String(64), index=True, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    buyer_id = Column(String(64), nullable=False, index=True)
    seller_id = Column(String(64), nullable=False, index=True)
    service_id = Column(String(64), nullable=False, index=True)
    listed_price = Column(String(32), nullable=False)
    amount_paid = Column(String(32), nullable=False)
    tx_hash = Column(String(128), nullable=True, index=True)
    status = Column(String(32), nullable=False, index=True)
    latency_ms = Column(Float, nullable=False, default=0.0)
    error_reason = Column(Text, nullable=True)


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
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
