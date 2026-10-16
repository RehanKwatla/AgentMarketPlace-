"""[DEFINED WORKFLOW COORDINATOR] Autonomous Buyer Agent."""
import time
import uuid
from typing import Any, List, Optional
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
        payment_service: Any = None,
    ):
        self.planner = planner or TaskPlanner()
        self.selector = selector or ServiceSelector()
        self.aggregator = aggregator or ResultAggregator()
        self.payment_service = payment_service

    async def execute_task(self, request: TaskRequest) -> TaskResponse:
        """Run end-to-end buyer workflow through the payment engine."""
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

        # Resolve PaymentService (injected or default singleton)
        pay_svc = self.payment_service
        if pay_svc is None:
            from backend.payments.service import payment_service
            pay_svc = payment_service

        for step in plan.steps:
            service = catalog.get_service(step.service_id)
            if not service:
                fallbacks.append(f"Service '{step.service_id}' not found.")
                continue

            call_id = f"step_{step.step_number}"
            idempotency_key = f"idemp_{task_id}_{step.step_number}_{service.service_id}"
            step_payload = getattr(step, "input_payload", {}) or {}

            # Execute paid service call through Member 1 Payment Engine
            start_t = time.perf_counter()
            paid_result = await pay_svc.execute_paid_call(
                task_id=task_id,
                call_id=call_id,
                service_id=service.service_id,
                input_payload=step_payload,
                idempotency_key=idempotency_key,
                task_budget_manager=budget_mgr,
            )
            latency = (time.perf_counter() - start_t) * 1000.0

            # Map PaymentStatus to LedgerStatus
            from backend.payments.schemas import PaymentStatus
            if paid_result.status == PaymentStatus.PAID:
                step_status = LedgerStatus.PAID
            elif paid_result.status == PaymentStatus.PAID_OUTPUT_REJECTED:
                step_status = LedgerStatus.PAID_OUTPUT_REJECTED
            elif paid_result.status == PaymentStatus.REFUSED:
                step_status = LedgerStatus.REFUSED
            else:
                step_status = LedgerStatus.FAILED_AND_NOT_CHARGED

            step_output = paid_result.seller_output or {
                "status": paid_result.status.value,
                "error": paid_result.error_message or "Service call failed"
            }

            executions.append(ExecutionStep(
                step=step.step_number,
                service_id=service.service_id,
                request_id=paid_result.request_id,
                price_paid_usdc=paid_result.amount_usdc,
                tx_hash=paid_result.tx_hash,
                status=step_status,
                latency_ms=round(paid_result.latency_ms or latency, 2),
                output=step_output,
            ))

        return self.aggregator.aggregate(
            task_id=task_id,
            budget_allocated_usdc=request.budget_usdc,
            executions=executions,
            fallbacks=fallbacks
        )
