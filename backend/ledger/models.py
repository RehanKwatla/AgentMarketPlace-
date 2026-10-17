"""Ledger Data Structures, Concurrency Protection, and Durable Database Repository."""
from datetime import datetime, timezone
import logging
import threading
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, OperationalError

from backend.shared.constants import (
    LedgerStatus,
    NETWORK_BASE_SEPOLIA,
    USDC_BASE_SEPOLIA,
    usdc_to_base_units,
)
from backend.shared.errors import LedgerInconsistencyError
from backend.shared.schemas import LedgerRecordSchema
from backend.database.session import SessionLocal, init_db
from backend.database.models import LedgerRecordModel, SellerReputationModel

logger = logging.getLogger(__name__)


def _model_to_schema(model: LedgerRecordModel) -> LedgerRecordSchema:
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

    price_units = getattr(model, "listed_price_units", None)
    paid_units = getattr(model, "amount_paid_units", None) or getattr(model, "amount_base_units", None)

    return LedgerRecordSchema(
        request_id=model.request_id,
        task_id=model.task_id,
        call_id=getattr(model, "call_id", None),
        payment_id=getattr(model, "payment_id", None),
        timestamp=ts or datetime.now(timezone.utc),
        buyer_id=model.buyer_id,
        seller_id=model.seller_id,
        service_id=model.service_id,
        listed_price=model.listed_price,
        amount_paid=model.amount_paid,
        listed_price_units=price_units,
        amount_paid_units=paid_units,
        amount_base_units=getattr(model, "amount_base_units", 0) or paid_units or 0,
        tx_hash=model.tx_hash,
        settlement_proof=getattr(model, "settlement_proof", None),
        network=getattr(model, "network", None) or NETWORK_BASE_SEPOLIA,
        token=getattr(model, "token", None) or USDC_BASE_SEPOLIA,
        token_address=getattr(model, "token_address", None),
        status=status_enum,
        latency_ms=model.latency_ms,
        error_reason=model.error_reason,
    )


class LedgerRepository:
    """Thread-safe, concurrency-safe durable audit ledger backed by database with in-memory caching."""

    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory
        self._records: Dict[str, LedgerRecordSchema] = {}
        self._lock = threading.RLock()
        try:
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
                    schema = _model_to_schema(r)
                    self._records[schema.request_id] = schema
        except Exception as exc:
            logger.debug(f"Initial DB ledger load skipped or table not initialized yet: {exc}")

    def record_transaction(self, record: LedgerRecordSchema) -> LedgerRecordSchema:
        """Atomically record a transaction with idempotency and consistency validation."""
        with self._lock:
            # Check in-memory first for consistency
            if record.request_id in self._records:
                existing_mem = self._records[record.request_id]
                if existing_mem.service_id != record.service_id:
                    raise LedgerInconsistencyError(
                        f"Service ID mismatch for request_id '{record.request_id}': "
                        f"incoming '{record.service_id}' != existing '{existing_mem.service_id}'"
                    )
                if existing_mem.buyer_id != record.buyer_id:
                    raise LedgerInconsistencyError(
                        f"Buyer ID mismatch for request_id '{record.request_id}': "
                        f"incoming '{record.buyer_id}' != existing '{existing_mem.buyer_id}'"
                    )
                if existing_mem.seller_id != record.seller_id:
                    raise LedgerInconsistencyError(
                        f"Seller ID mismatch for request_id '{record.request_id}': "
                        f"incoming '{record.seller_id}' != existing '{existing_mem.seller_id}'"
                    )
                incoming_units = record.amount_paid_units or usdc_to_base_units(record.amount_paid)
                existing_units = existing_mem.amount_paid_units or usdc_to_base_units(existing_mem.amount_paid)
                if incoming_units != existing_units:
                    raise LedgerInconsistencyError(
                        f"Amount mismatch for request_id '{record.request_id}': "
                        f"incoming {incoming_units} units != existing {existing_units} units"
                    )
                if existing_mem.tx_hash and record.tx_hash and existing_mem.tx_hash.startswith("0x") and record.tx_hash.startswith("0x") and existing_mem.tx_hash.lower() != record.tx_hash.lower():
                    raise LedgerInconsistencyError(
                        f"Transaction hash conflict for request_id '{record.request_id}': "
                        f"incoming '{record.tx_hash}' != existing '{existing_mem.tx_hash}'"
                    )

            st_val = record.status.value if hasattr(record.status, "value") else str(record.status)
            ts = record.timestamp
            if ts and ts.tzinfo is not None:
                ts = ts.astimezone(timezone.utc).replace(tzinfo=None)

            price_units = record.listed_price_units or usdc_to_base_units(record.listed_price)
            paid_units = record.amount_paid_units or usdc_to_base_units(record.amount_paid)

            db: Optional[Session] = None
            try:
                db = self._session_factory()
                existing = db.query(LedgerRecordModel).filter_by(request_id=record.request_id).first()
                if existing:
                    # Consistency check against existing DB record
                    if existing.service_id != record.service_id:
                        raise LedgerInconsistencyError(
                            f"Service ID mismatch for request_id '{record.request_id}': "
                            f"incoming '{record.service_id}' != existing '{existing.service_id}'"
                        )
                    if existing.buyer_id != record.buyer_id:
                        raise LedgerInconsistencyError(
                            f"Buyer ID mismatch for request_id '{record.request_id}': "
                            f"incoming '{record.buyer_id}' != existing '{existing.buyer_id}'"
                        )
                    if existing.seller_id != record.seller_id:
                        raise LedgerInconsistencyError(
                            f"Seller ID mismatch for request_id '{record.request_id}': "
                            f"incoming '{record.seller_id}' != existing '{existing.seller_id}'"
                        )
                    existing_db_units = existing.amount_paid_units or usdc_to_base_units(existing.amount_paid)
                    if paid_units != existing_db_units:
                        raise LedgerInconsistencyError(
                            f"Amount mismatch for request_id '{record.request_id}': "
                            f"incoming {paid_units} units != existing {existing_db_units} units"
                        )
                    if existing.tx_hash and record.tx_hash and existing.tx_hash.startswith("0x") and record.tx_hash.startswith("0x") and existing.tx_hash.lower() != record.tx_hash.lower():
                        raise LedgerInconsistencyError(
                            f"Transaction hash conflict for request_id '{record.request_id}': "
                            f"incoming '{record.tx_hash}' != existing '{existing.tx_hash}'"
                        )

                    existing.timestamp = ts or datetime.now(timezone.utc).replace(tzinfo=None)

                    # Prevent downgrading terminal paid status on weaker retries
                    if existing.status not in (LedgerStatus.PAID.value, LedgerStatus.PAID_OUTPUT_REJECTED.value):
                        existing.status = st_val
                    elif st_val in (LedgerStatus.PAID.value, LedgerStatus.PAID_OUTPUT_REJECTED.value):
                        existing.status = st_val

                    # Preserve stronger tx_hash
                    if record.tx_hash:
                        if not existing.tx_hash:
                            existing.tx_hash = record.tx_hash
                        elif not existing.tx_hash.startswith("0x") and record.tx_hash.startswith("0x"):
                            existing.tx_hash = record.tx_hash
                        elif existing.tx_hash.startswith("0x") and record.tx_hash.startswith("0x"):
                            existing.tx_hash = record.tx_hash

                    if getattr(record, "settlement_proof", None):
                        existing.settlement_proof = record.settlement_proof

                    existing.latency_ms = record.latency_ms
                    if record.error_reason:
                        existing.error_reason = record.error_reason
                    if getattr(record, "task_id", None):
                        existing.task_id = record.task_id
                    if getattr(record, "call_id", None):
                        existing.call_id = record.call_id
                    if getattr(record, "payment_id", None):
                        existing.payment_id = record.payment_id
                    if getattr(record, "network", None):
                        existing.network = record.network
                    if getattr(record, "token", None):
                        existing.token = record.token
                    if getattr(record, "token_address", None):
                        existing.token_address = record.token_address
                    if record.amount_paid:
                        existing.amount_paid = record.amount_paid
                    existing.listed_price_units = price_units
                    existing.amount_paid_units = paid_units
                    existing.amount_base_units = getattr(record, "amount_base_units", 0) or paid_units or 0

                    db.commit()
                    db.refresh(existing)
                    canonical = _model_to_schema(existing)
                    self._records[canonical.request_id] = canonical
                    return canonical
                else:
                    db_model = LedgerRecordModel(
                        request_id=record.request_id,
                        task_id=getattr(record, "task_id", None),
                        call_id=getattr(record, "call_id", None),
                        payment_id=getattr(record, "payment_id", None),
                        timestamp=ts or datetime.now(timezone.utc).replace(tzinfo=None),
                        buyer_id=record.buyer_id,
                        seller_id=record.seller_id,
                        service_id=record.service_id,
                        listed_price=record.listed_price,
                        amount_paid=record.amount_paid,
                        listed_price_units=price_units,
                        amount_paid_units=paid_units,
                        amount_base_units=getattr(record, "amount_base_units", 0) or paid_units or 0,
                        tx_hash=record.tx_hash,
                        settlement_proof=getattr(record, "settlement_proof", None),
                        network=getattr(record, "network", None) or NETWORK_BASE_SEPOLIA,
                        token=getattr(record, "token", None) or USDC_BASE_SEPOLIA,
                        token_address=getattr(record, "token_address", None),
                        status=st_val,
                        latency_ms=record.latency_ms,
                        error_reason=record.error_reason,
                    )
                    db.add(db_model)
                    db.commit()
                    db.refresh(db_model)
                    canonical = _model_to_schema(db_model)
                    self._records[canonical.request_id] = canonical
                    return canonical
            except LedgerInconsistencyError:
                raise
            except Exception as exc:
                logger.error(f"Failed to persist ledger record {record.request_id} to durable database: {exc}")
                raise RuntimeError(f"Durable ledger persistence failed for {record.request_id}: {exc}") from exc
            finally:
                if db:
                    db.close()

    def get_record(self, request_id: str) -> Optional[LedgerRecordSchema]:
        """Fetch record by request_id from database or in-memory fallback."""
        with self._lock:
            try:
                with self._session_factory() as session:
                    model = session.query(LedgerRecordModel).filter_by(request_id=request_id).first()
                    if model:
                        schema = _model_to_schema(model)
                        self._records[schema.request_id] = schema
                        return schema
            except Exception as exc:
                logger.debug(f"Database query error in get_record, checking cache: {exc}")

            return self._records.get(request_id)

    def list_records(
        self,
        status: Optional[str] = None,
        service_id: Optional[str] = None,
        task_id: Optional[str] = None,
        tx_hash: Optional[str] = None,
        buyer_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[LedgerRecordSchema]:
        """List records matching criteria, ordered by timestamp descending."""
        with self._lock:
            try:
                with self._session_factory() as session:
                    query = session.query(LedgerRecordModel)
                    if status:
                        query = query.filter(LedgerRecordModel.status == status)
                    if service_id:
                        query = query.filter(LedgerRecordModel.service_id == service_id)
                    if task_id:
                        query = query.filter(LedgerRecordModel.task_id == task_id)
                    if tx_hash:
                        query = query.filter(LedgerRecordModel.tx_hash == tx_hash)
                    if buyer_id:
                        query = query.filter(LedgerRecordModel.buyer_id == buyer_id)
                    query = query.order_by(LedgerRecordModel.timestamp.desc())
                    rows = query.offset(offset).limit(limit).all()
                    if rows:
                        schemas = [_model_to_schema(r) for r in rows]
                        for s in schemas:
                            self._records[s.request_id] = s
                        return schemas
            except Exception as exc:
                logger.debug(f"Database query error in list_records, using cache fallback: {exc}")

            results = list(self._records.values())
            if status:
                results = [r for r in results if (r.status.value == status if hasattr(r.status, "value") else str(r.status) == status)]
            if service_id:
                results = [r for r in results if r.service_id == service_id]
            if task_id:
                results = [r for r in results if getattr(r, "task_id", None) == task_id]
            if tx_hash:
                results = [r for r in results if getattr(r, "tx_hash", None) == tx_hash]
            if buyer_id:
                results = [r for r in results if r.buyer_id == buyer_id]
            results.sort(key=lambda r: r.timestamp, reverse=True)
            return results[offset : offset + limit]

    def count(
        self,
        status: Optional[str] = None,
        service_id: Optional[str] = None,
        task_id: Optional[str] = None,
        tx_hash: Optional[str] = None,
        buyer_id: Optional[str] = None,
    ) -> int:
        """Count matching records in durable database or memory cache."""
        with self._lock:
            try:
                with self._session_factory() as session:
                    query = session.query(LedgerRecordModel)
                    if status:
                        query = query.filter(LedgerRecordModel.status == status)
                    if service_id:
                        query = query.filter(LedgerRecordModel.service_id == service_id)
                    if task_id:
                        query = query.filter(LedgerRecordModel.task_id == task_id)
                    if tx_hash:
                        query = query.filter(LedgerRecordModel.tx_hash == tx_hash)
                    if buyer_id:
                        query = query.filter(LedgerRecordModel.buyer_id == buyer_id)
                    return query.count()
            except Exception:
                pass

            return len(self.list_records(status=status, service_id=service_id, task_id=task_id, tx_hash=tx_hash, buyer_id=buyer_id, limit=100000))

    def clear(self) -> None:
        """Helper to clear records (used in isolated test setups)."""
        with self._lock:
            self._records.clear()
            try:
                with self._session_factory() as session:
                    session.query(LedgerRecordModel).delete()
                    try:
                        session.query(SellerReputationModel).delete()
                    except Exception:
                        pass
                    session.commit()
            except Exception:
                pass


# Global runtime instance
ledger_repo = LedgerRepository()
