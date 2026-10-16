"""Tests for Atomic Integer Budget Reservations and Concurrency Safety."""
import asyncio
import pytest
from backend.shared.constants import usdc_to_base_units, base_units_to_usdc
from backend.shared.errors import BudgetExceededError
from backend.payments.budget import BudgetManager


def test_integer_base_unit_conversions():
    assert usdc_to_base_units("0.001") == 1000
    assert usdc_to_base_units("0.002") == 2000
    assert usdc_to_base_units("1.000000") == 1000000
    assert usdc_to_base_units("0.000001") == 1

    assert base_units_to_usdc(1000) == "0.001000"
    assert base_units_to_usdc(2000) == "0.002000"
    assert base_units_to_usdc(1000000) == "1.000000"


@pytest.mark.asyncio
async def test_budget_reservation_and_commit():
    manager = BudgetManager(initial_budget_units=10000)
    assert manager.available_budget == 10000

    # Reserve 3000 units
    avail = await manager.reserve("res_1", 3000)
    assert avail == 7000
    assert manager.available_budget == 7000

    # Commit 3000 units
    await manager.commit("res_1", 3000)
    assert manager.available_budget == 7000
    assert manager.get_task_spent("res_1") == 3000


@pytest.mark.asyncio
async def test_budget_overdraw_prevention():
    manager = BudgetManager(initial_budget_units=5000)
    # Attempt to reserve 6000 units
    with pytest.raises(BudgetExceededError):
        await manager.reserve("res_overdraw", 6000)
    # Available budget remains untouched
    assert manager.available_budget == 5000


@pytest.mark.asyncio
async def test_budget_release_refund():
    manager = BudgetManager(initial_budget_units=5000)
    await manager.reserve("res_fail", 2000)
    assert manager.available_budget == 3000

    # Service call failed or refused -> release reservation
    await manager.release("res_fail")
    assert manager.available_budget == 5000


@pytest.mark.asyncio
async def test_concurrent_budget_reservations():
    """Verify that multiple concurrent tasks cannot overdraw available budget."""
    total_budget = 10000
    manager = BudgetManager(initial_budget_units=total_budget)
    num_concurrent_tasks = 10
    cost_per_task = 2000  # Only 5 tasks can succeed

    success_count = 0
    failure_count = 0

    async def worker(worker_id: int):
        nonlocal success_count, failure_count
        try:
            await manager.reserve(f"worker_{worker_id}", cost_per_task)
            await asyncio.sleep(0.01)
            await manager.commit(f"worker_{worker_id}", cost_per_task)
            success_count += 1
        except BudgetExceededError:
            failure_count += 1

    tasks = [worker(i) for i in range(num_concurrent_tasks)]
    await asyncio.gather(*tasks)

    assert success_count == 5
    assert failure_count == 5
    assert manager.available_budget == 0
