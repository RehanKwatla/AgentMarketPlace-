"""Phase 3 Multi-Hop Tool-Calling Autonomous Buyer Agent.

Interfaces directly with Member 1's BuyerPaymentClientInterface and handles
application compatibility headers (X-402-Requirement, X-402-Payment-Payload, X-402-Settlement-Proof)
alongside standard x402 wire protocol headers for multi-hop tool-calling flows across Data, Scraping, and Inference services.
"""
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from backend.shared.constants import (
    HEADER_IDEMPOTENCY_KEY,
    HEADER_X402_PAYMENT_PAYLOAD,
    HEADER_X402_REQUIREMENT,
    HEADER_X402_SETTLEMENT_PROOF,
    LedgerStatus,
    ServiceCategory,
    base_units_to_usdc,
    usdc_to_base_units,
)
from backend.shared.schemas import (
    ExecutionStep,
    PaymentRequirement,
    TaskRequest,
    TaskResponse,
)
from backend.payments.budget import BudgetManager
from backend.payments.interfaces import BuyerPaymentClientInterface
from backend.payments.policy import PaymentPolicyVerifier
from backend.payments.settlement import SettlementVerifier
from backend.registry.schemas import ServiceRecord
from backend.registry.service import RegistryService, registry_service
from backend.buyer.aggregator import ResultAggregator
from backend.buyer.explanation import ExplanationGenerator
from backend.buyer.output_validator import OutputValidator
from backend.buyer.payment_client import BuyerPaymentClient
from backend.buyer.plan_validator import ExecutionPlan, PlannedCall, PlanValidator
from backend.buyer.planner import TaskPlanner
from backend.buyer.repository import TaskRepository, task_repository
from backend.buyer.schemas import (
    CallStatus,
    ServiceCallRecord,
    TaskCreationRequest,
    TaskDetailResponse,
    TaskStatus,
)
from backend.buyer.service import BuyerService

logger = logging.getLogger("BuyerAgent")


class BuyerAgent:
    """Coordinates multi-hop tool-calling workflows, official x402 payments, and atomic budget enforcement."""

    def __init__(
        self,
        payment_client: Optional[BuyerPaymentClientInterface] = None,
        registry: RegistryService = registry_service,
        repository: TaskRepository = task_repository,
        planner: Optional[TaskPlanner] = None,
        service: Optional[BuyerService] = None,
        selector: Optional[Any] = None,
        aggregator: Optional[ResultAggregator] = None,
        payment_service: Optional[Any] = None,
    ):
        self.registry = registry
        self.repository = repository
        self.policy_verifier = PaymentPolicyVerifier()
        self.settlement_verifier = SettlementVerifier(rpc_url="")
        self.payment_service = payment_service

        # Member 1 BuyerPaymentClientInterface compliance
        self.payment_client: BuyerPaymentClientInterface = payment_client or BuyerPaymentClient(
            policy_verifier=self.policy_verifier,
            settlement_verifier=self.settlement_verifier,
        )

        self.planner = planner or TaskPlanner()
        self.selector = selector
        self.plan_validator = PlanValidator(registry=self.registry)
        self.output_validator = OutputValidator()
        self.aggregator = aggregator or ResultAggregator()
        self.explanation_gen = ExplanationGenerator(registry=self.registry)

        # Core orchestration service backing multi-hop DAG execution
        self.service = service or BuyerService(
            registry=self.registry,
            repository=self.repository,
            payment_client=self.payment_client,
            policy_verifier=self.policy_verifier,
            settlement_verifier=self.settlement_verifier,
        )

    async def execute_task(self, request: TaskRequest) -> TaskResponse:
        """Execute task request with end-to-end multi-hop tool chaining and official x402 payment lifecycle."""
        if self.payment_service is not None:
            task_id = f"task_{uuid.uuid4().hex[:12]}"
            budget_units = usdc_to_base_units(request.budget_usdc)
            budget_mgr = self.payment_service.get_or_create_task_budget(task_id, budget_units)

            # 1. Decompose task into planned steps
            plan = self.planner.create_plan(TaskCreationRequest(task=request.task, budget_usdc=request.budget_usdc))

            executions: List[ExecutionStep] = []
            fallbacks: List[str] = []

            for step in plan.calls:
                service = self.registry.get_service(step.service_id)
                if not service:
                    fallbacks.append(f"Service '{step.service_id}' not found.")
                    continue

                call_id = f"step_{step.step_id}"
                idempotency_key = f"idemp_{task_id}_{step.step_id}_{service.service_id}"
                step_payload = getattr(step, "input_payload", {}) or {}

                start_t = time.perf_counter()
                paid_result = await self.payment_service.execute_paid_call(
                    task_id=task_id,
                    call_id=call_id,
                    service_id=service.service_id,
                    input_payload=step_payload,
                    idempotency_key=idempotency_key,
                    task_budget_manager=budget_mgr,
                )
                latency = (time.perf_counter() - start_t) * 1000.0

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
                    step=step.step_id,
                    service_id=service.service_id,
                    request_id=paid_result.request_id,
                    price_paid_usdc=paid_result.amount_usdc,
                    tx_hash=paid_result.tx_hash,
                    status=step_status,
                    latency_ms=round(paid_result.latency_ms or latency, 2),
                    output=step_output,
                ))

            selected = [e.service_id for e in executions]
            return TaskResponse(
                task_id=task_id,
                status="completed",
                budget_allocated_usdc=request.budget_usdc,
                total_cost_usdc=base_units_to_usdc(sum(usdc_to_base_units(e.price_paid_usdc) for e in executions)),
                cost_explanation="Execution completed via isolated payment service",
                selected_services=selected,
                executions=executions,
                final_result="Task executed successfully",
                errors_and_fallbacks=fallbacks,
            )

        # Full Phase 3 Multi-hop DAG execution
        creation_req = TaskCreationRequest(
            task=request.task,
            budget_usdc=request.budget_usdc,
            max_concurrency=3,
            execute_now=False,
        )

        # Phase 1: Planning & acceptance (strictly before payment)
        task_detail = self.service.create_task(creation_req)
        task_id = task_detail.task_id

        # Phase 2: Orchestrated multi-hop execution
        executed_detail = await self.service.execute_task(task_id)

        # Map to canonical TaskResponse
        return self._map_detail_to_task_response(executed_detail, request.budget_usdc)

    async def execute_multi_hop_flow(
        self,
        task: str,
        budget_usdc: str,
    ) -> TaskResponse:
        """Helper to run a multi-hop tool-calling flow (e.g. Data -> Scraping -> Inference)."""
        request = TaskRequest(task=task, budget_usdc=budget_usdc)
        return await self.execute_task(request)

    async def call_tool_direct(
        self,
        service_id: str,
        input_payload: Dict[str, Any],
        budget_mgr: BudgetManager,
        task_id: Optional[str] = None,
        step_id: int = 1,
    ) -> ServiceCallRecord:
        """Direct invocation of a single registered seller tool through the x402 lifecycle.

        Handles:
          1. Initial request -> seller emits HTTP 402 challenge (PAYMENT-REQUIRED or X-402-Requirement).
          2. Policy verification via Member 1 verifier.
          3. Payment authorization creation via BuyerPaymentClientInterface.
          4. Re-request with payment authorization headers (PAYMENT-SIGNATURE / X-402-Payment-Payload) and Idempotency-Key.
          5. Settlement verification via BuyerPaymentClientInterface from settlement proof headers (PAYMENT-RESPONSE / X-402-Settlement-Proof).
          6. Draft-7 output schema validation.
          7. Atomic budget commit/release.
        """
        task_id = task_id or f"direct_{uuid.uuid4().hex[:8]}"
        planned = PlannedCall(
            step_id=step_id,
            category="",
            service_id=service_id,
            input_payload=input_payload,
            estimated_price_units=0,
            depends_on=[],
        )
        # Use underlying robust execution engine
        return await self.service._execute_call(
            task_id=task_id,
            planned=planned,
            budget_mgr=budget_mgr,
            upstream_calls={},
            fallbacks=[],
            warnings=[],
        )

    def _map_detail_to_task_response(
        self,
        detail: TaskDetailResponse,
        budget_allocated_usdc: str,
    ) -> TaskResponse:
        """Map internal TaskDetailResponse to the official shared TaskResponse schema."""
        executions: List[ExecutionStep] = []
        selected_services: List[str] = []

        for c in detail.calls:
            selected_services.append(c.service_id)

            # Map internal CallStatus to shared LedgerStatus
            if c.status == CallStatus.SUCCEEDED:
                step_status = LedgerStatus.PAID
            elif c.status == CallStatus.PAID_OUTPUT_REJECTED:
                step_status = LedgerStatus.PAID_OUTPUT_REJECTED
            elif c.status == CallStatus.REFUSED:
                step_status = LedgerStatus.REFUSED
            else:
                step_status = LedgerStatus.FAILED_AND_NOT_CHARGED

            req_id = c.call_id if c.call_id.startswith("req_") else f"req_{c.call_id}"

            executions.append(
                ExecutionStep(
                    step=c.step_id,
                    service_id=c.service_id,
                    request_id=req_id,
                    price_paid_usdc=c.amount_paid_usdc,
                    tx_hash=c.transaction_hash,
                    status=step_status,
                    latency_ms=c.latency_ms,
                    output=c.output,
                    error=c.error,
                )
            )

        # Build errors and fallbacks list
        errors_and_fallbacks: List[str] = []
        if detail.failure_reason:
            errors_and_fallbacks.append(detail.failure_reason)
        if detail.explanation:
            if detail.explanation.warnings:
                errors_and_fallbacks.extend(detail.explanation.warnings)
            if detail.explanation.fallback_attempts:
                errors_and_fallbacks.extend(detail.explanation.fallback_attempts)

        return TaskResponse(
            task_id=detail.task_id,
            status=detail.status,
            budget_allocated_usdc=budget_allocated_usdc,
            total_cost_usdc=detail.spent_usdc,
            cost_explanation=detail.cost_explanation or "Execution cost summary",
            selected_services=selected_services,
            executions=executions,
            final_result=detail.final_result or detail.result,
            errors_and_fallbacks=errors_and_fallbacks,
        )
