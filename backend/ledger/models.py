"""Ledger Data Structures, Concurrency Protection, and Persistent Repository."""
import logging
import threading
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from backend.shared.constants import (
    LedgerStatus,
    NETWORK_BASE_SEPOLIA,
    USDC_BASE_SEPOLIA,
    usdc_to_base_units,
)
from backend.shared.errors import LedgerInconsistencyError
from backend.shared.schemas import LedgerRecordSchema
from backend.database.session import SessionLocal
from backend.database.models import LedgerRecordModel

logger = logging.getLogger(__name__)


def _model_to_schema(model: LedgerRecordModel) -> LedgerRecordSchema:
    status_str = model.status
    try:
        status_enum = LedgerStatus(status_str)
    except Exception:
        status_enum = LedgerStatus.PAID if "paid" in status_str else LedgerStatus.FAILED_AND_NOT_CHARGED
    return LedgerRecordSchema(
        request_id=model.request_id,
        task_id=model.task_id,
        payment_id=model.payment_id,
        timestamp=model.timestamp,
        buyer_id=model.buyer_id,
        seller_id=model.seller_id,
        service_id=model.service_id,
        listed_price=model.listed_price,
        amount_paid=model.amount_paid,
        listed_price_units=model.listed_price_units,
        amount_paid_units=model.amount_paid_units,
        network=model.network or NETWORK_BASE_SEPOLIA,
        token=model.token or USDC_BASE_SEPOLIA,
        tx_hash=model.tx_hash,
        status=status_enum,
        latency_ms=model.latency_ms,
        error_reason=model.error_reason,
    )


class LedgerRepository:
    """Thread-safe and concurrency-safe audit ledger with database persistence."""

    def __init__(self):
        self._records: Dict[str, LedgerRecordSchema] = {}
        self._lock = threading.RLock()

    def record_transaction(self, record: LedgerRecordSchema) -> LedgerRecordSchema:
        """Atomically record a transaction with idempotency and consistency validation.
        
        If a record already exists with the same request_id:
        - Verifies that critical fields (service_id, buyer_id, seller_id, amount, tx_hash) match.
        - If inconsistent, raises LedgerInconsistencyError.
        - If consistent, safely returns the existing canonical record (or updates with confirmed settlement).
        If no record exists:
        - Persists to the database and syncs in-memory storage.
        """
        with self._lock:
            db: Optional[Session] = None
            try:
                db = SessionLocal()
                existing_model = db.query(LedgerRecordModel).filter(
                    LedgerRecordModel.request_id == record.request_id
                ).first()

                if existing_model:
                    # Consistency check against existing record
                    if existing_model.service_id != record.service_id:
                        raise LedgerInconsistencyError(
                            f"Service ID mismatch for request_id '{record.request_id}': "
                            f"incoming '{record.service_id}' != existing '{existing_model.service_id}'"
                        )
                    if existing_model.buyer_id != record.buyer_id:
                        raise LedgerInconsistencyError(
                            f"Buyer ID mismatch for request_id '{record.request_id}': "
                            f"incoming '{record.buyer_id}' != existing '{existing_model.buyer_id}'"
                        )
                    if existing_model.seller_id != record.seller_id:
                        raise LedgerInconsistencyError(
                            f"Seller ID mismatch for request_id '{record.request_id}': "
                            f"incoming '{record.seller_id}' != existing '{existing_model.seller_id}'"
                        )

                    incoming_units = record.amount_paid_units or usdc_to_base_units(record.amount_paid)
                    existing_units = existing_model.amount_paid_units or usdc_to_base_units(existing_model.amount_paid)
                    if incoming_units != existing_units:
                        raise LedgerInconsistencyError(
                            f"Amount mismatch for request_id '{record.request_id}': "
                            f"incoming {incoming_units} units != existing {existing_units} units"
                        )

                    if existing_model.tx_hash and record.tx_hash and existing_model.tx_hash != record.tx_hash:
                        raise LedgerInconsistencyError(
                            f"Transaction hash conflict for request_id '{record.request_id}': "
                            f"incoming '{record.tx_hash}' != existing '{existing_model.tx_hash}'"
                        )

                    # Consistent duplicate. If incoming has confirmed tx_hash or PAID status, update existing
                    updated = False
                    if record.tx_hash and not existing_model.tx_hash:
                        existing_model.tx_hash = record.tx_hash
                        updated = True
                    status_str = record.status.value if hasattr(record.status, "value") else str(record.status)
                    if record.status == LedgerStatus.PAID and existing_model.status != status_str:
                        existing_model.status = status_str
                        updated = True
                    if updated:
                        db.commit()
                        db.refresh(existing_model)

                    canonical = _model_to_schema(existing_model)
                    self._records[canonical.request_id] = canonical
                    return canonical

                # Record does not exist: persist to DB
                status_str = record.status.value if hasattr(record.status, "value") else str(record.status)
                price_units = record.listed_price_units or usdc_to_base_units(record.listed_price)
                paid_units = record.amount_paid_units or usdc_to_base_units(record.amount_paid)

                db_model = LedgerRecordModel(
                    request_id=record.request_id,
                    task_id=record.task_id,
                    payment_id=record.payment_id,
                    timestamp=record.timestamp,
                    buyer_id=record.buyer_id,
                    seller_id=record.seller_id,
                    service_id=record.service_id,
                    listed_price=record.listed_price,
                    amount_paid=record.amount_paid,
                    listed_price_units=price_units,
                    amount_paid_units=paid_units,
                    network=record.network or NETWORK_BASE_SEPOLIA,
                    token=record.token or USDC_BASE_SEPOLIA,
                    tx_hash=record.tx_hash,
                    status=status_str,
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
            except Exception as e:
                logger.warning(f"Database operation encountered issue, maintaining in-memory consistency: {e}")
                # Check in-memory fallback
                if record.request_id in self._records:
                    existing = self._records[record.request_id]
                    if existing.service_id != record.service_id or existing.amount_paid != record.amount_paid:
                        raise LedgerInconsistencyError(
                            f"Inconsistent in-memory ledger data for request_id '{record.request_id}'"
                        )
                    return existing
                self._records[record.request_id] = record
                return record
            finally:
                if db:
                    db.close()

    def get_record(self, request_id: str) -> Optional[LedgerRecordSchema]:
        """Fetch record by request_id from database or in-memory fallback."""
        with self._lock:
            db: Optional[Session] = None
            try:
                db = SessionLocal()
                model = db.query(LedgerRecordModel).filter(
                    LedgerRecordModel.request_id == request_id
                ).first()
                if model:
                    schema = _model_to_schema(model)
                    self._records[schema.request_id] = schema
                    return schema
            except Exception:
                pass
            finally:
                if db:
                    db.close()

            return self._records.get(request_id)

    def list_records(
        self,
        status: Optional[str] = None,
        service_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[LedgerRecordSchema]:
        """List ledger records with optional status and service filtering."""
        with self._lock:
            db: Optional[Session] = None
            try:
                db = SessionLocal()
                query = db.query(LedgerRecordModel)
                if status:
                    query = query.filter(LedgerRecordModel.status == status)
                if service_id:
                    query = query.filter(LedgerRecordModel.service_id == service_id)
                query = query.order_by(LedgerRecordModel.timestamp.desc())
                models = query.offset(offset).limit(limit).all()
                if models:
                    schemas = [_model_to_schema(m) for m in models]
                    for s in schemas:
                        self._records[s.request_id] = s
                    return schemas
            except Exception:
                pass
            finally:
                if db:
                    db.close()

            # In-memory fallback
            results = list(self._records.values())
            if status:
                results = [r for r in results if (r.status.value == status if hasattr(r.status, "value") else str(r.status) == status)]
            if service_id:
                results = [r for r in results if r.service_id == service_id]
            results.sort(key=lambda r: r.timestamp, reverse=True)
            return results[offset : offset + limit]

    def count(self, status: Optional[str] = None, service_id: Optional[str] = None) -> int:
        """Count total ledger records matching filters."""
        with self._lock:
            db: Optional[Session] = None
            try:
                db = SessionLocal()
                query = db.query(LedgerRecordModel)
                if status:
                    query = query.filter(LedgerRecordModel.status == status)
                if service_id:
                    query = query.filter(LedgerRecordModel.service_id == service_id)
                return query.count()
            except Exception:
                pass
            finally:
                if db:
                    db.close()

            return len(self.list_records(status=status, service_id=service_id, limit=100000))

    def clear(self) -> None:
        """Helper to clear records (used in isolated test setups)."""
        with self._lock:
            self._records.clear()
            db: Optional[Session] = None
            try:
                db = SessionLocal()
                from backend.database.models import SellerReputationModel
                db.query(LedgerRecordModel).delete()
                db.query(SellerReputationModel).delete()
                db.commit()
            except Exception:
                pass
            finally:
                if db:
                    db.close()



# Global runtime instance
ledger_repo = LedgerRepository()
