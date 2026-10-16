"""[IMPLEMENTED FOUNDATION] Atomic Concurrency-Safe Budget Reservation Manager."""
import asyncio
from typing import Dict
from backend.shared.errors import BudgetExceededError


class BudgetManager:
    """Thread-safe and async-safe budget manager operating purely on integer base units."""

    def __init__(self, initial_budget_units: int):
        self._total_budget_units = initial_budget_units
        self._available_units = initial_budget_units
        self._reserved_units: Dict[str, int] = {}
        self._spent_units: Dict[str, int] = {}
        self._lock = asyncio.Lock()

    @property
    def total_budget(self) -> int:
        return self._total_budget_units

    @property
    def available_budget(self) -> int:
        return self._available_units

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

    async def release(self, reservation_id: str) -> None:
        """Release reservation back to available budget if execution fails or is refused."""
        async with self._lock:
            reserved = self._reserved_units.pop(reservation_id, 0)
            self._available_units += reserved

    def get_task_spent(self, reservation_id: str) -> int:
        return self._spent_units.get(reservation_id, 0)
