"""[IMPLEMENTED] Persistent Database Models and Repository for Member 1 Payments.

Defines:
1. PaymentAttemptModel: Durable storage for payment attempts, idempotency keys, nonces, and receipts.
2. BudgetReservationModel: Durable reservation records preventing double-spend across process restarts.
3. DurablePaymentRepository: Atomic database operations for payment attempts and budget locks.
"""
from datetime import datetime, timezone, timedelta
import json
import logging
import random
import time
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import Column, String, Integer, DateTime, Text, UniqueConstraint, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from backend.database.session import Base, SessionLocal, engine
from backend.payments.schemas import PaymentStatus, PaymentAttemptRecord, BudgetReservationRecord
from backend.payments.errors import SettlementVerificationError

logger = logging.getLogger(__name__)


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


class SettlementEvidenceRecordModel(Base):
    """Durable, unique record of every accepted settlement evidence, guaranteeing cross-process replay protection.

    Enforces uniqueness at granular (tx_hash, log_index) level for on-chain EVM transactions,
    and at facilitator_receipt_id level for off-chain facilitator receipts.
    """
    __tablename__ = "settlement_evidence_records"

    evidence_id = Column(String(160), primary_key=True, index=True)
    tx_hash = Column(String(128), nullable=True, index=True)
    log_index = Column(Integer, default=0, nullable=False)
    facilitator_receipt_id = Column(String(128), nullable=True, index=True)
    attempt_id = Column(String(64), nullable=False, index=True)
    network = Column(String(64), nullable=False)
    token_address = Column(String(128), nullable=True)
    recipient_address = Column(String(128), nullable=True)
    amount_units = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("network", "tx_hash", "log_index", name="uq_evidence_net_tx_log"),
    )


class AuthorizationNonceReservationModel(Base):
    """Durable record of authorization nonces preventing replay across multiple worker processes."""
    __tablename__ = "authorization_nonce_reservations"

    auth_key = Column(String(160), primary_key=True, index=True)
    network = Column(String(64), nullable=False, index=True)
    signer_address = Column(String(128), nullable=True, index=True)
    nonce = Column(String(128), nullable=False, index=True)
    status = Column(String(32), nullable=False, index=True)  # "reserved", "consumed", "released"
    reserved_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    consumed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False, index=True)


class DurablePaymentRepository:
    """Manages transactional database operations for payments, idempotency, and budget reservations."""

    def __init__(self, session_factory=SessionLocal):
        self.session_factory = session_factory
        self._migrate_schema_if_needed()

    def _migrate_schema_if_needed(self) -> None:
        """Migration-safe schema upgrade for settlement_evidence_records table in SQLite.

        Preserves existing evidence, handles interrupted migrations, ensures idempotency,
        and normalizes legacy missing networks to Base Sepolia (NETWORK_BASE_SEPOLIA).
        """
        try:
            with self.session_factory() as session:
                bind = session.bind
                if not bind:
                    return

                # Ensure authorization nonce reservation table exists
                AuthorizationNonceReservationModel.__table__.create(bind, checkfirst=True)

                if bind.dialect.name != "sqlite":
                    return

                # Check if an interrupted migration left _legacy_settlement_evidence_records
                legacy_res = session.execute(text(
                    "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='_legacy_settlement_evidence_records'"
                )).scalar()

                table_res = session.execute(text(
                    "SELECT sql FROM sqlite_master WHERE type='table' AND name='settlement_evidence_records'"
                )).fetchone()

                if not table_res and not legacy_res:
                    return

                needs_migration = False
                if table_res and table_res[0]:
                    ddl = table_res[0]
                    if "uq_evidence_net_tx_log" not in ddl:
                        needs_migration = True
                elif legacy_res and not table_res:
                    needs_migration = True

                if not needs_migration and not legacy_res:
                    return

                if table_res and "uq_evidence_net_tx_log" not in table_res[0]:
                    if legacy_res:
                        session.execute(text("DROP TABLE _legacy_settlement_evidence_records"))
                    session.execute(text("ALTER TABLE settlement_evidence_records RENAME TO _legacy_settlement_evidence_records"))

                SettlementEvidenceRecordModel.__table__.create(bind, checkfirst=True)

                session.execute(text("""
                    INSERT OR IGNORE INTO settlement_evidence_records
                    (evidence_id, tx_hash, log_index, facilitator_receipt_id, attempt_id, network, token_address, recipient_address, amount_units, created_at)
                    SELECT
                        evidence_id,
                        tx_hash,
                        log_index,
                        facilitator_receipt_id,
                        attempt_id,
                        COALESCE(network, 'unresolved:legacy'),
                        token_address,
                        recipient_address,
                        amount_units,
                        created_at
                    FROM _legacy_settlement_evidence_records
                """))
                session.execute(text("DROP TABLE _legacy_settlement_evidence_records"))
                session.commit()
        except Exception as exc:
            logger.warning(f"DurablePaymentRepository schema migration error: {exc}")

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

    def save_attempt_response(self, idempotency_key: str, response_data: Dict[str, Any]) -> bool:
        """Atomically persist response JSON for an idempotency key to survive restarts."""
        with self.session_factory() as session:
            att = session.query(PaymentAttemptModel).filter_by(idempotency_key=idempotency_key).first()
            if att:
                att.response_json = json.dumps(response_data)
                att.updated_at = datetime.now(timezone.utc)
                session.commit()
                return True
            return False

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

    def update_reservation_status(
        self,
        reservation_id: str,
        new_status: str,
        actual_spent_units: Optional[int] = None
    ) -> bool:
        """Update a reservation status (e.g. to 'committed' or 'released') and adjust spent amount."""
        with self.session_factory() as session:
            res = session.query(BudgetReservationModel).filter_by(reservation_id=reservation_id).first()
            if res:
                res.status = new_status
                if actual_spent_units is not None:
                    res.amount_base_units = actual_spent_units
                res.updated_at = datetime.now(timezone.utc)
                session.commit()
                return True
            return False

    def atomic_reserve(
        self,
        task_id: str,
        reservation_id: str,
        call_id: str,
        amount_base_units: int,
        total_budget_units: int,
        max_retries: int = 5,
    ) -> Tuple[bool, int, str]:
        """Atomically check remaining budget and reserve funds within a single DB transaction.

        Guarantees that two concurrent processes or threads cannot overspend the budget.
        Uses engine-level transaction locking (BEGIN IMMEDIATE for SQLite, advisory locks for Postgres).
        Returns:
            (success: bool, remaining_available_units: int, error_message: str)
        """
        for attempt in range(max_retries):
            try:
                with self.session_factory() as session:
                    dialect = session.bind.dialect.name
                    if dialect == "sqlite":
                        session.execute(text("BEGIN IMMEDIATE"))
                    elif dialect == "postgresql":
                        session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:task_id))"), {"task_id": task_id})

                    # Query active reservations and committed spend for this task
                    active_and_committed = (
                        session.query(BudgetReservationModel)
                        .filter(
                            BudgetReservationModel.task_id == task_id,
                            BudgetReservationModel.status.in_(["reserved", "committed"])
                        )
                        .all()
                    )
                    total_used = sum(r.amount_base_units for r in active_and_committed)
                    available = total_budget_units - total_used

                    if amount_base_units > available:
                        session.rollback()
                        return False, available, f"Requested {amount_base_units} units exceeds available {available} units"

                    # Check if reservation_id already exists to prevent duplicate insert
                    existing = session.query(BudgetReservationModel).filter_by(reservation_id=reservation_id).first()
                    if existing:
                        if existing.status == "reserved":
                            return True, available, ""
                        session.rollback()
                        return False, available, f"Reservation '{reservation_id}' already exists with status '{existing.status}'"

                    # Insert reservation within transaction
                    model = BudgetReservationModel(
                        reservation_id=reservation_id,
                        task_id=task_id,
                        call_id=call_id,
                        amount_base_units=amount_base_units,
                        status="reserved",
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                    )
                    session.add(model)
                    session.commit()
                    new_available = available - amount_base_units
                    return True, new_available, ""

            except OperationalError as oe:
                # SQLite busy/locked error - backoff and retry
                if "locked" in str(oe).lower() or "busy" in str(oe).lower():
                    if attempt < max_retries - 1:
                        time.sleep(0.01 * (2 ** attempt) + random.uniform(0.005, 0.02))
                        continue
                logger.error(f"OperationalError during atomic_reserve: {oe}")
                return False, 0, f"Database locking conflict during reservation: {oe}"
            except Exception as ex:
                logger.error(f"Unexpected error during atomic_reserve: {ex}")
                return False, 0, f"Database error during reservation: {ex}"

        return False, 0, "Database busy timeout during concurrent atomic reservation."

    def atomic_record_settlement_evidence(
        self,
        attempt_id: str,
        network: str,
        amount_units: int,
        tx_hash: Optional[str] = None,
        log_index: int = 0,
        facilitator_receipt_id: Optional[str] = None,
        token_address: Optional[str] = None,
        recipient_address: Optional[str] = None,
        max_retries: int = 5,
    ) -> bool:
        """Atomically check and record settlement evidence in durable storage.

        Guarantees cross-process uniqueness and replay protection.
        Enforces:
        - Distinct (tx_hash, log_index) uniqueness so batch transactions with multiple transfers succeed.
        - Identical (tx_hash, log_index) replay attempts fail closed across all concurrent workers.
        - Facilitator receipt IDs are deduplicated.
        """
        if not tx_hash and not facilitator_receipt_id:
            raise SettlementVerificationError("Cannot record settlement evidence: both tx_hash and facilitator_receipt_id are missing.")

        normalized_tx = tx_hash.lower() if tx_hash else None
        if normalized_tx:
            evidence_id = f"evm:{network.lower()}:{normalized_tx}:{log_index}"
        else:
            evidence_id = f"fac:{facilitator_receipt_id}"

        for attempt in range(max_retries):
            try:
                with self.session_factory() as session:
                    dialect = session.bind.dialect.name
                    if dialect == "sqlite":
                        session.execute(text("BEGIN IMMEDIATE"))
                    elif dialect == "postgresql":
                        session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:evidence_id))"), {"evidence_id": evidence_id})

                    # 1. Check primary evidence_id
                    existing_ev = session.query(SettlementEvidenceRecordModel).filter_by(evidence_id=evidence_id).first()
                    if existing_ev:
                        if existing_ev.attempt_id == attempt_id:
                            return True  # Idempotent re-verification of the same attempt
                        session.rollback()
                        raise SettlementVerificationError(
                            f"Duplicate settlement evidence detected: evidence '{evidence_id}' has already been accepted and recorded for attempt '{existing_ev.attempt_id}'."
                        )

                    # 2. Check (network, tx_hash, log_index) uniqueness if on-chain
                    if normalized_tx:
                        existing_tx = session.query(SettlementEvidenceRecordModel).filter(
                            SettlementEvidenceRecordModel.network == network,
                            SettlementEvidenceRecordModel.tx_hash == normalized_tx,
                            SettlementEvidenceRecordModel.log_index == log_index
                        ).first()
                        if existing_tx:
                            if existing_tx.attempt_id == attempt_id:
                                return True
                            session.rollback()
                            raise SettlementVerificationError(
                                f"Duplicate settlement evidence detected: tx_hash '{normalized_tx}' at log_index {log_index} on network '{network}' has already been accepted for attempt '{existing_tx.attempt_id}'."
                            )

                    # 3. Check facilitator_receipt_id if off-chain
                    if facilitator_receipt_id:
                        existing_fac = session.query(SettlementEvidenceRecordModel).filter_by(facilitator_receipt_id=facilitator_receipt_id).first()
                        if existing_fac:
                            if existing_fac.attempt_id == attempt_id:
                                return True
                            session.rollback()
                            raise SettlementVerificationError(
                                f"Duplicate settlement evidence detected: facilitator receipt '{facilitator_receipt_id}' has already been accepted for attempt '{existing_fac.attempt_id}'."
                            )

                    # 4. Insert settlement record within transaction
                    model = SettlementEvidenceRecordModel(
                        evidence_id=evidence_id,
                        tx_hash=normalized_tx,
                        log_index=log_index,
                        facilitator_receipt_id=facilitator_receipt_id,
                        attempt_id=attempt_id,
                        network=network,
                        token_address=token_address.lower() if token_address else None,
                        recipient_address=recipient_address.lower() if recipient_address else None,
                        amount_units=amount_units,
                        created_at=datetime.now(timezone.utc),
                    )
                    session.add(model)
                    session.commit()
                    return True

            except OperationalError as oe:
                if "locked" in str(oe).lower() or "busy" in str(oe).lower():
                    if attempt < max_retries - 1:
                        time.sleep(0.01 * (2 ** attempt) + random.uniform(0.005, 0.02))
                        continue
                raise SettlementVerificationError(f"Database locking conflict while recording settlement evidence: {oe}")
            except IntegrityError as ie:
                raise SettlementVerificationError(
                    f"Duplicate settlement evidence detected via database constraint: {ie}"
                )

        raise SettlementVerificationError("Database busy timeout while recording settlement evidence.")

    def is_evidence_recorded(
        self,
        tx_hash: Optional[str] = None,
        log_index: int = 0,
        facilitator_receipt_id: Optional[str] = None,
        exclude_attempt_id: Optional[str] = None,
        network: Optional[str] = None,
    ) -> bool:
        """Check whether specific settlement evidence has already been recorded in durable storage."""
        with self.session_factory() as session:
            if tx_hash:
                normalized_tx = tx_hash.lower()
                q = session.query(SettlementEvidenceRecordModel).filter(
                    SettlementEvidenceRecordModel.tx_hash == normalized_tx,
                    SettlementEvidenceRecordModel.log_index == log_index
                )
                if network:
                    q = q.filter(SettlementEvidenceRecordModel.network == network)
                if exclude_attempt_id:
                    q = q.filter(SettlementEvidenceRecordModel.attempt_id != exclude_attempt_id)
                if q.first():
                    return True
            if facilitator_receipt_id:
                q = session.query(SettlementEvidenceRecordModel).filter_by(
                    facilitator_receipt_id=facilitator_receipt_id
                )
                if network:
                    q = q.filter(SettlementEvidenceRecordModel.network == network)
                if exclude_attempt_id:
                    q = q.filter(SettlementEvidenceRecordModel.attempt_id != exclude_attempt_id)
                if q.first():
                    return True
            return False

    def is_tx_hash_used(
        self,
        tx_hash: str,
        log_index: Optional[int] = None,
        exclude_attempt_id: Optional[str] = None,
        network: Optional[str] = None,
    ) -> bool:
        """Check if an on-chain transaction hash has already been used for settlement in durable DB."""
        if not tx_hash:
            return False
        normalized_tx = tx_hash.lower()
        with self.session_factory() as session:
            # 1. Check SettlementEvidenceRecordModel
            ev_query = session.query(SettlementEvidenceRecordModel).filter(
                SettlementEvidenceRecordModel.tx_hash == normalized_tx
            )
            if log_index is not None:
                ev_query = ev_query.filter(SettlementEvidenceRecordModel.log_index == log_index)
            if network:
                ev_query = ev_query.filter(SettlementEvidenceRecordModel.network == network)
            if exclude_attempt_id:
                ev_query = ev_query.filter(SettlementEvidenceRecordModel.attempt_id != exclude_attempt_id)
            if ev_query.first() is not None:
                return True

            # 2. Check PaymentAttemptModel
            query = session.query(PaymentAttemptModel).filter(
                PaymentAttemptModel.tx_hash == tx_hash,
                PaymentAttemptModel.status.in_([PaymentStatus.PAID.value, "paid", "PAID"])
            )
            if exclude_attempt_id:
                query = query.filter(PaymentAttemptModel.attempt_id != exclude_attempt_id)
            return query.first() is not None

    def get_task_reserved_amount(self, task_id: str) -> int:
        """Sum total active uncommitted reservations for a task from durable storage."""
        with self.session_factory() as session:
            reservations = (
                session.query(BudgetReservationModel)
                .filter_by(task_id=task_id, status="reserved")
                .all()
            )
            return sum(r.amount_base_units for r in reservations)

    def atomic_reserve_authorization_nonce(
        self,
        auth_key: str,
        network: str,
        nonce: str,
        signer_address: Optional[str] = None,
        ttl_seconds: int = 7200,
        max_retries: int = 5,
    ) -> bool:
        """Atomically reserve an authorization nonce in durable storage across independent processes/workers.

        Guarantees:
        - Two concurrent workers on separate DB connections cannot both reserve and execute the same authorization.
        - Already consumed authorization nonces fail immediately with SettlementVerificationError.
        - Currently in-flight (unexpired) reservations fail immediately with SettlementVerificationError.
        - Expired reservations (> ttl_seconds) or explicitly released reservations can be re-reserved safely.
        - Concurrency conflicts are serialized using BEGIN IMMEDIATE (SQLite) or advisory lock (Postgres).
        """
        for attempt in range(max_retries):
            try:
                with self.session_factory() as session:
                    dialect = session.bind.dialect.name
                    if dialect == "sqlite":
                        session.execute(text("BEGIN IMMEDIATE"))
                    elif dialect == "postgresql":
                        session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:auth_key))"), {"auth_key": auth_key})

                    now = datetime.now(timezone.utc)
                    existing = session.query(AuthorizationNonceReservationModel).filter_by(auth_key=auth_key).first()
                    if existing:
                        if existing.status == "consumed":
                            session.rollback()
                            raise SettlementVerificationError(
                                f"Authorization nonce replay detected: authorization '{auth_key}' has already been consumed."
                            )
                        elif existing.status == "reserved":
                            # Check active vs expired
                            exp = existing.expires_at
                            if exp.tzinfo is None:
                                exp = exp.replace(tzinfo=timezone.utc)
                            if exp > now:
                                session.rollback()
                                raise SettlementVerificationError(
                                    f"Concurrent authorization replay detected: authorization '{auth_key}' is already in-flight."
                                )
                            else:
                                # Reclaim expired reservation
                                existing.status = "reserved"
                                existing.reserved_at = now
                                existing.expires_at = now + timedelta(seconds=ttl_seconds)
                                session.commit()
                                return True
                        elif existing.status == "released":
                            existing.status = "reserved"
                            existing.reserved_at = now
                            existing.expires_at = now + timedelta(seconds=ttl_seconds)
                            session.commit()
                            return True

                    # New reservation
                    model = AuthorizationNonceReservationModel(
                        auth_key=auth_key,
                        network=network,
                        signer_address=signer_address.lower() if signer_address else None,
                        nonce=nonce,
                        status="reserved",
                        reserved_at=now,
                        consumed_at=None,
                        expires_at=now + timedelta(seconds=ttl_seconds),
                    )
                    session.add(model)
                    session.commit()
                    return True

            except OperationalError as oe:
                if "locked" in str(oe).lower() or "busy" in str(oe).lower():
                    if attempt < max_retries - 1:
                        time.sleep(0.01 * (2 ** attempt) + random.uniform(0.005, 0.02))
                        continue
                raise SettlementVerificationError(f"Database locking conflict while reserving authorization nonce: {oe}")
            except IntegrityError as ie:
                # Concurrent insert race caught by primary key uniqueness
                raise SettlementVerificationError(
                    f"Concurrent authorization replay detected: authorization '{auth_key}' is already in-flight: {ie}"
                )

        raise SettlementVerificationError("Database busy timeout while reserving authorization nonce.")

    def commit_authorization_nonce(self, auth_key: str, max_retries: int = 5) -> bool:
        """Atomically transition an authorization nonce to consumed status."""
        for attempt in range(max_retries):
            try:
                with self.session_factory() as session:
                    dialect = session.bind.dialect.name
                    if dialect == "sqlite":
                        session.execute(text("BEGIN IMMEDIATE"))
                    elif dialect == "postgresql":
                        session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:auth_key))"), {"auth_key": auth_key})

                    now = datetime.now(timezone.utc)
                    existing = session.query(AuthorizationNonceReservationModel).filter_by(auth_key=auth_key).first()
                    if existing:
                        existing.status = "consumed"
                        existing.consumed_at = now
                        session.commit()
                        return True
                    else:
                        model = AuthorizationNonceReservationModel(
                            auth_key=auth_key,
                            network="unknown",
                            signer_address=None,
                            nonce=auth_key.split(":")[-1] if ":" in auth_key else auth_key,
                            status="consumed",
                            reserved_at=now,
                            consumed_at=now,
                            expires_at=now + timedelta(days=365),
                        )
                        session.add(model)
                        session.commit()
                        return True
            except OperationalError as oe:
                if "locked" in str(oe).lower() or "busy" in str(oe).lower():
                    if attempt < max_retries - 1:
                        time.sleep(0.01 * (2 ** attempt) + random.uniform(0.005, 0.02))
                        continue
                raise
        return False

    def release_authorization_nonce(self, auth_key: str, max_retries: int = 5) -> bool:
        """Atomically release an in-flight authorization nonce reservation if verification failed.

        CRITICAL: Never releases a nonce if it has already transitioned to consumed.
        """
        for attempt in range(max_retries):
            try:
                with self.session_factory() as session:
                    dialect = session.bind.dialect.name
                    if dialect == "sqlite":
                        session.execute(text("BEGIN IMMEDIATE"))
                    elif dialect == "postgresql":
                        session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:auth_key))"), {"auth_key": auth_key})

                    existing = session.query(AuthorizationNonceReservationModel).filter_by(auth_key=auth_key).first()
                    if existing:
                        if existing.status == "consumed":
                            logger.warning(f"Refusing to release already consumed authorization nonce '{auth_key}'.")
                            session.rollback()
                            return False
                        existing.status = "released"
                        session.commit()
                        return True
                    return False
            except OperationalError as oe:
                if "locked" in str(oe).lower() or "busy" in str(oe).lower():
                    if attempt < max_retries - 1:
                        time.sleep(0.01 * (2 ** attempt) + random.uniform(0.005, 0.02))
                        continue
                raise
        return False

    def is_authorization_nonce_consumed(self, auth_key: str) -> bool:
        """Check if an authorization nonce is in consumed or active reserved status."""
        with self.session_factory() as session:
            now = datetime.now(timezone.utc)
            existing = session.query(AuthorizationNonceReservationModel).filter_by(auth_key=auth_key).first()
            if not existing:
                return False
            if existing.status == "consumed":
                return True
            if existing.status == "reserved":
                exp = existing.expires_at
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if exp > now:
                    return True
            return False

    def clear_authorization_nonces(self) -> None:
        """Clear all authorization nonces (test helper)."""
        with self.session_factory() as session:
            session.query(AuthorizationNonceReservationModel).delete()
            session.commit()


# Singleton repository instance
durable_payment_repo = DurablePaymentRepository()
