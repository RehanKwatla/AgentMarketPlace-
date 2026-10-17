"""Buyer Task Persistence Repository using Member 4's agreed TaskRecordModel."""
from datetime import datetime, timezone
from typing import Optional
from backend.database.session import SessionLocal
from backend.database.models import TaskRecordModel
from backend.shared.errors import AgentEconomyBaseException


class PersistenceError(AgentEconomyBaseException):
    def __init__(self, message: str):
        super().__init__(message, error_code="PERSISTENCE_ERROR")


class TaskRepository:
    """Manages database persistence for high-level buyer tasks."""

    def __init__(self):
        self._simulate_failure: bool = False

    def set_simulate_failure(self, simulate: bool) -> None:
        """Testing hook to verify persistence failure handling."""
        self._simulate_failure = simulate

    def save_task(
        self,
        task_id: str,
        task_prompt: str,
        budget_usdc: str,
        status: str = "accepted"
    ) -> TaskRecordModel:
        """Create and persist a task record in the database."""
        if self._simulate_failure:
            raise PersistenceError("Simulated database persistence failure during task creation.")

        try:
            with SessionLocal() as session:
                record = TaskRecordModel(
                    task_id=task_id,
                    task_prompt=task_prompt,
                    budget_usdc=budget_usdc,
                    total_cost_usdc="0.000000",
                    status=status,
                    created_at=datetime.now(timezone.utc)
                )
                session.add(record)
                session.commit()
                session.refresh(record)
                return record
        except PersistenceError:
            raise
        except Exception as e:
            raise PersistenceError(f"Database error persisting task '{task_id}': {e}")

    def update_task_status(
        self,
        task_id: str,
        status: str,
        total_cost_usdc: Optional[str] = None,
        failure_reason: Optional[str] = None,
        final_result: Optional[str] = None,
    ) -> None:
        """Update status, final cost, failure reason, and final result for a persisted task."""
        if self._simulate_failure:
            raise PersistenceError("Simulated database persistence failure during status update.")

        try:
            with SessionLocal() as session:
                record = session.query(TaskRecordModel).filter(TaskRecordModel.task_id == task_id).first()
                if record:
                    record.status = status
                    if total_cost_usdc is not None:
                        record.total_cost_usdc = total_cost_usdc
                    if failure_reason is not None:
                        record.failure_reason = failure_reason
                    if final_result is not None:
                        record.final_result = final_result
                    session.commit()
        except PersistenceError:
            raise
        except Exception as e:
            raise PersistenceError(f"Database error updating task '{task_id}': {e}")

    def get_task(self, task_id: str) -> Optional[TaskRecordModel]:
        """Query a task from the database by ID."""
        try:
            with SessionLocal() as session:
                record = session.query(TaskRecordModel).filter(TaskRecordModel.task_id == task_id).first()
                if record:
                    # Detach / extract fields before session closes
                    session.expunge(record)
                return record
        except Exception:
            return None

    def list_tasks(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> list[TaskRecordModel]:
        """List tasks with optional status filter and pagination."""
        try:
            with SessionLocal() as session:
                query = session.query(TaskRecordModel)
                if status:
                    query = query.filter(TaskRecordModel.status == status)
                query = query.order_by(TaskRecordModel.created_at.desc())
                records = query.offset(offset).limit(limit).all()
                for r in records:
                    session.expunge(r)
                return records
        except Exception:
            return []

    def record_call_to_ledger(
        self,
        task_id: str,
        request_id: str,
        service_id: str,
        listed_price: str,
        amount_paid: str,
        status: str,
        tx_hash: Optional[str] = None,
        latency_ms: float = 0.0,
        error_reason: Optional[str] = None,
        buyer_id: str = "buyer_orchestrator",
        seller_id: Optional[str] = None
    ) -> None:

        """Persist individual call audit records into Member 4's ledger repository and database."""
        # 1. Update Member 4 in-memory / query repository
        from backend.ledger.models import ledger_repo
        from backend.shared.schemas import LedgerRecordSchema
        from backend.shared.constants import LedgerStatus

        # Map to LedgerStatus
        status_clean = str(status).lower()
        if "paid output rejected" in status_clean:
            ls = LedgerStatus.PAID_OUTPUT_REJECTED
        elif "paid" in status_clean or "succeeded" in status_clean:
            ls = LedgerStatus.PAID
        elif "refused" in status_clean:
            ls = LedgerStatus.REFUSED
        else:
            ls = LedgerStatus.FAILED_AND_NOT_CHARGED

        record_schema = LedgerRecordSchema(
            request_id=request_id,
            timestamp=datetime.now(timezone.utc),
            buyer_id=buyer_id,
            seller_id=seller_id or service_id,
            service_id=service_id,
            listed_price=listed_price,
            amount_paid=amount_paid,
            tx_hash=tx_hash,
            status=ls,
            latency_ms=latency_ms,
            error_reason=error_reason
        )
        ledger_repo.record_transaction(record_schema)
        try:
            from backend.ledger.reputation import ReputationCalculator
            ReputationCalculator(ledger_repo).update_for_service(service_id)
        except Exception:
            pass

        # 2. Persist to Member 4's SQLAlchemy LedgerRecordModel if available
        try:
            from backend.database.models import LedgerRecordModel
            with SessionLocal() as session:
                db_record = LedgerRecordModel(
                    request_id=request_id,
                    task_id=task_id,
                    timestamp=datetime.now(timezone.utc),
                    buyer_id=buyer_id,
                    seller_id=seller_id or service_id,
                    service_id=service_id,
                    listed_price=listed_price,
                    amount_paid=amount_paid,
                    tx_hash=tx_hash,
                    status=str(status),
                    latency_ms=latency_ms,
                    error_reason=error_reason
                )
                session.add(db_record)
                session.commit()
        except Exception:
            # Continue safely if database is in memory or table already written
            pass


# Global singleton instance
task_repository = TaskRepository()
