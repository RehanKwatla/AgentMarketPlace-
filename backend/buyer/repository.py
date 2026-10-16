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
        total_cost_usdc: Optional[str] = None
    ) -> None:
        """Update status and final cost for a persisted task."""
        if self._simulate_failure:
            raise PersistenceError("Simulated database persistence failure during status update.")

        try:
            with SessionLocal() as session:
                record = session.query(TaskRecordModel).filter(TaskRecordModel.task_id == task_id).first()
                if record:
                    record.status = status
                    if total_cost_usdc is not None:
                        record.total_cost_usdc = total_cost_usdc
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


# Global singleton instance
task_repository = TaskRepository()
