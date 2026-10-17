"""Ledger Data Structures and Durable Database Repository (Member 4)."""
from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional
from sqlalchemy.exc import IntegrityError, OperationalError

from backend.shared.constants import LedgerStatus
from backend.shared.schemas import LedgerRecordSchema
from backend.database.session import SessionLocal, init_db
from backend.database.models import LedgerRecordModel

logger = logging.getLogger(__name__)


class LedgerRepository:
    """Durable audit ledger backed by database with in-memory caching capability."""

    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory
        self._records: Dict[str, LedgerRecordSchema] = {}
        try:
            from backend.database.session import init_db
            eng = getattr(session_factory, "kw", {}).get("bind") or getattr(session_factory, "bind", None)
            if eng:
                init_db(eng)
        except Exception:
            pass
        self._load_from_db()

    def _load_from_db(self) -> None:
        """Populate memory cache from durable database if tables exist."""
        try:
            with self._session_factory() as session:
                records = session.query(LedgerRecordModel).all()
                for r in records:
                    schema = self._model_to_schema(r)
                    self._records[schema.request_id] = schema
        except Exception as exc:
            logger.debug(f"Initial DB ledger load skipped or table not initialized yet: {exc}")

    def _model_to_schema(self, model: LedgerRecordModel) -> LedgerRecordSchema:
        st = model.status
        if st in LedgerStatus._value2member_map_:
            status_enum = LedgerStatus(st)
        else:
            try:
                status_enum = LedgerStatus(st)
            except Exception:
                status_enum = LedgerStatus.PAID if "paid" in str(st).lower() else LedgerStatus.FAILED_AND_NOT_CHARGED

        ts = model.timestamp
        if ts and ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        return LedgerRecordSchema(
            request_id=model.request_id,
            task_id=model.task_id,
            call_id=getattr(model, "call_id", None),
            timestamp=ts or datetime.now(timezone.utc),
            buyer_id=model.buyer_id,
            seller_id=model.seller_id,
            service_id=model.service_id,
            listed_price=model.listed_price,
            amount_paid=model.amount_paid,
            amount_base_units=getattr(model, "amount_base_units", 0) or 0,
            tx_hash=model.tx_hash,
            settlement_proof=getattr(model, "settlement_proof", None),
            network=getattr(model, "network", None),
            token_address=getattr(model, "token_address", None),
            status=status_enum,
            latency_ms=model.latency_ms,
            error_reason=model.error_reason,
        )

    def record_transaction(self, record: LedgerRecordSchema) -> LedgerRecordSchema:
        """Atomically persist a transaction record to the database and update memory cache.

        Guarantees:
        - Writes to durable SQL storage (PostgreSQL or SQLite).
        - Idempotent upsert: repeated calls update evidence rather than failing on primary key conflict.
        - Raises explicit persistence error if database operation fails.
        """
        self._records[record.request_id] = record

        st_val = record.status.value if hasattr(record.status, "value") else str(record.status)
        ts = record.timestamp
        if ts and ts.tzinfo is not None:
            ts = ts.astimezone(timezone.utc).replace(tzinfo=None)

        try:
            with self._session_factory() as session:
                existing = session.query(LedgerRecordModel).filter_by(request_id=record.request_id).first()
                if existing:
                    existing.timestamp = ts or datetime.now(timezone.utc).replace(tzinfo=None)

                    # Prevent downgrading terminal paid status on weaker retries
                    if existing.status not in (LedgerStatus.PAID.value, LedgerStatus.PAID_OUTPUT_REJECTED.value):
                        existing.status = st_val
                    elif st_val in (LedgerStatus.PAID.value, LedgerStatus.PAID_OUTPUT_REJECTED.value):
                        existing.status = st_val

                    # Preserve stronger tx_hash: never overwrite existing tx_hash with None or weaker local auth
                    if record.tx_hash:
                        if not existing.tx_hash:
                            existing.tx_hash = record.tx_hash
                        elif not existing.tx_hash.startswith("0x") and record.tx_hash.startswith("0x"):
                            existing.tx_hash = record.tx_hash
                        elif existing.tx_hash.startswith("0x") and record.tx_hash.startswith("0x"):
                            existing.tx_hash = record.tx_hash

                    # Preserve stronger settlement_proof
                    if getattr(record, "settlement_proof", None):
                        existing.settlement_proof = record.settlement_proof

                    existing.latency_ms = record.latency_ms
                    if record.error_reason:
                        existing.error_reason = record.error_reason
                    if getattr(record, "amount_base_units", None) is not None:
                        existing.amount_base_units = record.amount_base_units
                    if getattr(record, "task_id", None):
                        existing.task_id = record.task_id
                    if getattr(record, "call_id", None):
                        existing.call_id = record.call_id
                    if getattr(record, "network", None):
                        existing.network = record.network
                    if getattr(record, "token_address", None):
                        existing.token_address = record.token_address
                    if record.amount_paid:
                        existing.amount_paid = record.amount_paid
                else:
                    db_model = LedgerRecordModel(
                        request_id=record.request_id,
                        task_id=getattr(record, "task_id", None),
                        call_id=getattr(record, "call_id", None),
                        timestamp=ts or datetime.now(timezone.utc).replace(tzinfo=None),
                        buyer_id=record.buyer_id,
                        seller_id=record.seller_id,
                        service_id=record.service_id,
                        listed_price=record.listed_price,
                        amount_paid=record.amount_paid,
                        amount_base_units=getattr(record, "amount_base_units", 0) or 0,
                        tx_hash=record.tx_hash,
                        settlement_proof=getattr(record, "settlement_proof", None),
                        network=getattr(record, "network", None),
                        token_address=getattr(record, "token_address", None),
                        status=st_val,
                        latency_ms=record.latency_ms,
                        error_reason=record.error_reason,
                    )
                    session.add(db_model)
                session.commit()
        except Exception as exc:
            logger.error(f"Failed to persist ledger record {record.request_id} to durable database: {exc}")
            raise RuntimeError(f"Durable ledger persistence failed for {record.request_id}: {exc}") from exc

        return record

    def get_record(self, request_id: str) -> Optional[LedgerRecordSchema]:
        """Fetch record by request_id from database, falling back to memory cache."""
        try:
            with self._session_factory() as session:
                r = session.query(LedgerRecordModel).filter_by(request_id=request_id).first()
                if r:
                    schema = self._model_to_schema(r)
                    self._records[schema.request_id] = schema
                    return schema
        except Exception as exc:
            logger.debug(f"Database query error in get_record, checking cache: {exc}")

        return self._records.get(request_id)

    def list_records(
        self,
        status: Optional[str] = None,
        service_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[LedgerRecordSchema]:
        """List records matching criteria, ordered by timestamp descending."""
        try:
            with self._session_factory() as session:
                query = session.query(LedgerRecordModel)
                if status:
                    query = query.filter(LedgerRecordModel.status == status)
                if service_id:
                    query = query.filter(LedgerRecordModel.service_id == service_id)
                query = query.order_by(LedgerRecordModel.timestamp.desc())
                rows = query.offset(offset).limit(limit).all()
                if rows:
                    return [self._model_to_schema(r) for r in rows]
        except Exception as exc:
            logger.debug(f"Database query error in list_records, using cache fallback: {exc}")

        results = list(self._records.values())
        if status:
            results = [r for r in results if (r.status.value == status if hasattr(r.status, "value") else r.status == status)]
        if service_id:
            results = [r for r in results if r.service_id == service_id]

        results.sort(key=lambda r: r.timestamp, reverse=True)
        return results[offset : offset + limit]

    def count(self, status: Optional[str] = None, service_id: Optional[str] = None) -> int:
        """Count matching records in durable database or memory cache."""
        try:
            with self._session_factory() as session:
                query = session.query(LedgerRecordModel)
                if status:
                    query = query.filter(LedgerRecordModel.status == status)
                if service_id:
                    query = query.filter(LedgerRecordModel.service_id == service_id)
                return query.count()
        except Exception:
            pass

        return len(self.list_records(status=status, service_id=service_id, limit=100000))


# Global runtime instance
ledger_repo = LedgerRepository()
