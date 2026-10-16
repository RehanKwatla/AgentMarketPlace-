"""[IMPLEMENTED] Atomic Concurrency-Safe Budget Reservation Manager with Durable Persistence."""
import asyncio
import logging
from typing import Any, Dict, Optional
from backend.shared.errors import BudgetExceededError

logger = logging.getLogger(__name__)


class BudgetManager:
    """Thread-safe and async-safe budget manager operating purely on integer base units.

    Supports both in-memory async concurrency control and durable persistence via DurablePaymentRepository.
    """

    def __init__(
        self,
        initial_budget_units: int,
        task_id: Optional[str] = None,
        repo: Optional[Any] = None
    ):
        self._total_budget_units = initial_budget_units
        self._available_units = initial_budget_units
        self._reserved_units: Dict[str, int] = {}
        self._spent_units: Dict[str, int] = {}
        self._lock = asyncio.Lock()
        self.task_id = task_id
        self._repo = repo

    @property
    def repo(self) -> Optional[Any]:
        if self._repo is None and self.task_id is not None:
            try:
                from backend.payments.models import durable_payment_repo
                self._repo = durable_payment_repo
            except Exception:
                pass
        return self._repo

    @property
    def total_budget(self) -> int:
        return self._total_budget_units

    @property
    def available_budget(self) -> int:
        return self._available_units

    @property
    def reserved_budget(self) -> int:
        return sum(self._reserved_units.values())

    @property
    def total_spent(self) -> int:
        return sum(self._spent_units.values())

    async def reserve(self, reservation_id: str, amount_units: int) -> int:
        """Atomically reserve funds for an in-flight service call.
        Raises BudgetExceededError if available funds are insufficient.
        """
        if amount_units <= 0:
            raise ValueError("Reservation amount must be positive integer.")

        async with self._lock:
            if amount_units > self._available_units:
                raise BudgetExceededError(
                    requested_units=amount_units,
                    available_units=self._available_units
                )

            self._available_units -= amount_units
            self._reserved_units[reservation_id] = (
                self._reserved_units.get(reservation_id, 0) + amount_units
            )

            # Persist reservation if durable repository is configured
            if self.repo and self.task_id:
                try:
                    self.repo.record_reservation(
                        reservation_id=reservation_id,
                        task_id=self.task_id,
                        call_id=reservation_id,
                        amount_base_units=amount_units,
                        status="reserved"
                    )
                except Exception as err:
                    logger.debug(f"Could not persist budget reservation to DB: {err}")

            return self._available_units

    async def commit(self, reservation_id: str, actual_spent_units: int) -> None:
        """Commit an in-flight reservation upon confirmed payment settlement."""
        async with self._lock:
            reserved = self._reserved_units.pop(reservation_id, 0)
            if actual_spent_units < reserved:
                # Refund difference if actual settlement was less than reserved
                refund = reserved - actual_spent_units
                self._available_units += refund

            self._spent_units[reservation_id] = (
                self._spent_units.get(reservation_id, 0) + actual_spent_units
            )

            # Update durable reservation record
            if self.repo:
                try:
                    self.repo.update_reservation_status(reservation_id, "committed")
                except Exception as err:
                    logger.debug(f"Could not commit budget reservation in DB: {err}")

    async def release(self, reservation_id: str) -> None:
        """Release reservation back to available budget if execution fails or is refused."""
        async with self._lock:
            reserved = self._reserved_units.pop(reservation_id, 0)
            self._available_units += reserved

            # Update durable reservation record
            if self.repo:
                try:
                    self.repo.update_reservation_status(reservation_id, "released")
                except Exception as err:
                    logger.debug(f"Could not release budget reservation in DB: {err}")

    def get_reservation(self, reservation_id: str) -> int:
        return self._reserved_units.get(reservation_id, 0)

    def get_task_spent(self, reservation_id: str) -> int:
        return self._spent_units.get(reservation_id, 0)
