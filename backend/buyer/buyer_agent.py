"""Phase 3 Multi-Hop Tool-Calling Autonomous Buyer Agent.

Interfaces directly with Member 1's BuyerPaymentClientInterface and handles
official x402 headers (X-402-Requirement, X-402-Payment-Payload, X-402-Settlement-Proof)
for multi-hop tool-calling flows across Data, Scraping, and Inference services.
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
    ):
        self.registry = registry
        self.repository = repository
        self.policy_verifier = PaymentPolicyVerifier()
        self.settlement_verifier = SettlementVerifier(rpc_url="")

        # Member 1 BuyerPaymentClientInterface compliance
        self.payment_client: BuyerPaymentClientInterface = payment_client or BuyerPaymentClient(
            policy_verifier=self.policy_verifier,
            settlement_verifier=self.settlement_verifier,
        )

        self.planner = planner or TaskPlanner()
        self.plan_validator = PlanValidator(registry=self.registry)
        self.output_validator = OutputValidator()
        self.aggregator = ResultAggregator()
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
        # Convert TaskRequest to TaskCreationRequest
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
        """Direct invocation of a single registered seller tool through the official x402 lifecycle.

        Handles:
          1. Initial request -> seller emits HTTP 402 with X-402-Requirement.
          2. Policy verification via Member 1 verifier.
          3. Payment authorization creation via BuyerPaymentClientInterface.
          4. Re-request with X-402-Payment-Payload and Idempotency-Key.
          5. Settlement verification via BuyerPaymentClientInterface from X-402-Settlement-Proof.
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

            executions.append(
                ExecutionStep(
                    step=c.step_id,
                    service_id=c.service_id,
                    request_id=c.call_id,
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
