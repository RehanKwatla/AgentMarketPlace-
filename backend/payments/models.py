"""[IMPLEMENTED] Persistent Database Models and Repository for Member 1 Payments.

Defines:
1. PaymentAttemptModel: Durable storage for payment attempts, idempotency keys, nonces, and receipts.
2. BudgetReservationModel: Durable reservation records preventing double-spend across process restarts.
3. DurablePaymentRepository: Atomic database operations for payment attempts and budget locks.
"""
from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional
from sqlalchemy import Column, String, Integer, DateTime, Text, UniqueConstraint
from sqlalchemy.orm import Session

from backend.database.session import Base, SessionLocal, engine
from backend.payments.schemas import PaymentStatus, PaymentAttemptRecord, BudgetReservationRecord


class PaymentAttemptModel(Base):
    """Durable record of every payment attempt, preserving idempotency and reconciliation state across restarts."""
    __tablename__ = "payment_attempts"

    attempt_id = Column(String(64), primary_key=True, index=True)
    task_id = Column(String(64), index=True, nullable=True)
    call_id = Column(String(64), index=True, nullable=True)
    service_id = Column(String(64), index=True, nullable=False)
    idempotency_key = Column(String(128), unique=True, index=True, nullable=False)
    request_hash = Column(String(64), nullable=False)
    nonce = Column(String(64), unique=True, index=True, nullable=False)
    amount_units = Column(Integer, nullable=False)
    pay_to = Column(String(128), nullable=True)
    status = Column(String(32), index=True, nullable=False)
    tx_hash = Column(String(128), nullable=True, index=True)
    settlement_proof = Column(Text, nullable=True)
    response_json = Column(Text, nullable=True)
    error_code = Column(String(64), nullable=True)
    error_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class BudgetReservationModel(Base):
    """Durable record of atomic budget reservations, preventing overdraws across process restarts."""
    __tablename__ = "budget_reservations"

    reservation_id = Column(String(64), primary_key=True, index=True)
    task_id = Column(String(64), index=True, nullable=False)
    call_id = Column(String(64), index=True, nullable=False)
    amount_base_units = Column(Integer, nullable=False)
    status = Column(String(32), index=True, nullable=False)  # reserved, committed, released
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class DurablePaymentRepository:
    """Manages transactional database operations for payments, idempotency, and budget reservations."""

    def __init__(self, session_factory=SessionLocal):
        self.session_factory = session_factory

    def save_attempt(self, attempt: PaymentAttemptRecord) -> None:
        """Persist or update a payment attempt record."""
        with self.session_factory() as session:
            existing = session.query(PaymentAttemptModel).filter(
                (PaymentAttemptModel.attempt_id == attempt.attempt_id) |
                (PaymentAttemptModel.idempotency_key == attempt.idempotency_key)
            ).first()
            if existing:
                existing.attempt_id = attempt.attempt_id
                existing.status = attempt.status.value
                existing.tx_hash = attempt.tx_hash
                existing.settlement_proof = attempt.settlement_proof
                existing.error_reason = attempt.error_reason
                existing.pay_to = attempt.pay_to
                existing.updated_at = datetime.now(timezone.utc)
            else:
                model = PaymentAttemptModel(
                    attempt_id=attempt.attempt_id,
                    task_id=attempt.task_id,
                    call_id=attempt.call_id,
                    service_id=attempt.service_id,
                    idempotency_key=attempt.idempotency_key,
                    request_hash=attempt.request_hash,
                    nonce=attempt.nonce or f"nonce_{attempt.attempt_id}",
                    amount_units=attempt.amount_base_units,
                    pay_to=attempt.pay_to,
                    status=attempt.status.value,
                    tx_hash=attempt.tx_hash,
                    settlement_proof=attempt.settlement_proof,
                    error_reason=attempt.error_reason,
                    created_at=attempt.created_at,
                    updated_at=datetime.now(timezone.utc),
                )
                session.add(model)
            session.commit()

    def get_attempt_by_idempotency_key(self, key: str) -> Optional[PaymentAttemptModel]:
        """Query payment attempt by idempotency key."""
        with self.session_factory() as session:
            return session.query(PaymentAttemptModel).filter_by(idempotency_key=key).first()

    def get_attempt_by_nonce(self, nonce: str) -> Optional[PaymentAttemptModel]:
        """Query payment attempt by nonce."""
        with self.session_factory() as session:
            return session.query(PaymentAttemptModel).filter_by(nonce=nonce).first()

    def get_attempt_by_id(self, attempt_id: str) -> Optional[PaymentAttemptModel]:
        """Query payment attempt by unique attempt ID."""
        with self.session_factory() as session:
            return session.query(PaymentAttemptModel).filter_by(attempt_id=attempt_id).first()

    def update_attempt_status(
        self,
        attempt_id: str,
        status: Any,
        tx_hash: Optional[str] = None,
        error_reason: Optional[str] = None
    ) -> bool:
        """Update terminal or suspense status of an existing payment attempt."""
        with self.session_factory() as session:
            att = session.query(PaymentAttemptModel).filter_by(attempt_id=attempt_id).first()
            if not att:
                return False
            att.status = status.value if hasattr(status, "value") else str(status)
            if tx_hash:
                att.tx_hash = tx_hash
            if error_reason:
                att.error_reason = error_reason
            att.updated_at = datetime.now(timezone.utc)
            session.commit()
            return True

    def get_pending_reconciliations(self) -> List[PaymentAttemptModel]:
        """Retrieve all payment attempts currently in PENDING_RECONCILIATION status across restarts."""
        with self.session_factory() as session:
            return (
                session.query(PaymentAttemptModel)
                .filter_by(status=PaymentStatus.PENDING_RECONCILIATION.value)
                .order_by(PaymentAttemptModel.created_at.asc())
                .all()
            )

    def record_reservation(
        self,
        reservation_id: str,
        task_id: str,
        call_id: str,
        amount_base_units: int,
        status: str = "reserved"
    ) -> BudgetReservationModel:
        """Atomically persist a budget reservation."""
        with self.session_factory() as session:
            model = BudgetReservationModel(
                reservation_id=reservation_id,
                task_id=task_id,
                call_id=call_id,
                amount_base_units=amount_base_units,
                status=status,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(model)
            session.commit()
            session.refresh(model)
            return model

    def update_reservation_status(self, reservation_id: str, new_status: str) -> bool:
        """Update a reservation status (e.g. to 'committed' or 'released')."""
        with self.session_factory() as session:
            res = session.query(BudgetReservationModel).filter_by(reservation_id=reservation_id).first()
            if res:
                res.status = new_status
                res.updated_at = datetime.now(timezone.utc)
                session.commit()
                return True
            return False

    def get_task_reserved_amount(self, task_id: str) -> int:
        """Sum total active uncommitted reservations for a task from durable storage."""
        with self.session_factory() as session:
            reservations = (
                session.query(BudgetReservationModel)
                .filter_by(task_id=task_id, status="reserved")
                .all()
            )
            return sum(r.amount_base_units for r in reservations)


# Singleton repository instance
durable_payment_repo = DurablePaymentRepository()
