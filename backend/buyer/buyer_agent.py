"""[DEFINED WORKFLOW COORDINATOR] Autonomous Buyer Agent."""
import time
import uuid
from typing import List
from backend.shared.constants import (
    LedgerStatus,
    base_units_to_usdc,
    usdc_to_base_units,
)
from backend.shared.schemas import ExecutionStep, TaskRequest, TaskResponse
from backend.buyer.task_planner import TaskPlanner
from backend.buyer.service_selector import ServiceSelector
from backend.buyer.result_aggregator import ResultAggregator
from backend.payments.budget import BudgetManager
from backend.registry.service_catalog import catalog


class BuyerAgent:
    """Coordinates task decomposition, budget reservation, service execution, and result aggregation."""

    def __init__(
        self,
        planner: TaskPlanner = None,
        selector: ServiceSelector = None,
        aggregator: ResultAggregator = None,
    ):
        self.planner = planner or TaskPlanner()
        self.selector = selector or ServiceSelector()
        self.aggregator = aggregator or ResultAggregator()

    async def execute_task(self, request: TaskRequest) -> TaskResponse:
        """Run end-to-end buyer workflow."""
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        budget_units = usdc_to_base_units(request.budget_usdc)
        budget_mgr = BudgetManager(initial_budget_units=budget_units)

        # 1. Decompose task into planned steps
        plan = self.planner.plan_task(request.task, request.budget_usdc)

        # 2. Check if planned cost exceeds initial task budget
        if plan.estimated_total_units > budget_units:
            return TaskResponse(
                task_id=task_id,
                status="refused",
                budget_allocated_usdc=request.budget_usdc,
                total_cost_usdc="0.000000",
                cost_explanation="Estimated task cost exceeds allocated budget.",
                selected_services=[],
                executions=[],
                final_result="Task refused: Insufficient budget allocated.",
                errors_and_fallbacks=[f"Required {plan.estimated_total_units} units, but budget was {budget_units} units."]
            )

        executions: List[ExecutionStep] = []
        fallbacks: List[str] = []

        for step in plan.steps:
            service = catalog.get_service(step.service_id)
            if not service:
                fallbacks.append(f"Service '{step.service_id}' not found.")
                continue

            # Atomically reserve budget
            res_id = f"res_{uuid.uuid4().hex[:8]}"
            await budget_mgr.reserve(res_id, service.price_base_units)

            start_t = time.perf_counter()
            # In full Member 1/3 integration, this invokes HTTP 402 handshake.
            # Here we provide a baseline execution step.
            latency = (time.perf_counter() - start_t) * 1000.0

            await budget_mgr.commit(res_id, service.price_base_units)

            executions.append(ExecutionStep(
                step=step.step_number,
                service_id=service.service_id,
                request_id=f"req_{uuid.uuid4().hex[:8]}",
                price_paid_usdc=service.price_usdc,
                tx_hash=None,  # Real tx hash injected upon live on-chain settlement
                status=LedgerStatus.PAID,
                latency_ms=round(latency, 2),
                output={"status": "step_executed", "service": service.name}
            ))

        return self.aggregator.aggregate(
            task_id=task_id,
            budget_allocated_usdc=request.budget_usdc,
            executions=executions,
            fallbacks=fallbacks
        )
