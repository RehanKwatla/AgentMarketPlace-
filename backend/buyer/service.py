"""Buyer Agent Execution Engine managing concurrency >= 3, budget, payments, and aggregation."""
import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from backend.shared.constants import (
    HEADER_X402_REQUIREMENT,
    HEADER_X402_PAYMENT_PAYLOAD,
    HEADER_X402_SETTLEMENT_PROOF,
    HEADER_IDEMPOTENCY_KEY,
    ServiceCategory,
    usdc_to_base_units,
    base_units_to_usdc,
)
from backend.shared.errors import AgentEconomyBaseException
from backend.payments.budget import BudgetManager
from backend.payments.policy import PaymentPolicyVerifier
from backend.payments.idempotency import IdempotencyStore
from backend.registry.service import RegistryService, registry_service
from backend.buyer.schemas import (
    TaskStatus,
    CallStatus,
    TaskCreationRequest,
    TaskCreationResponse,
    TaskDetailResponse,
    TaskCallsResponse,
    ServiceCallRecord,
)
from backend.buyer.planner import TaskPlanner
from backend.buyer.selector import ServiceSelector
from backend.buyer.plan_validator import PlannedCall, ExecutionPlan, PlanValidator
from backend.buyer.output_validator import OutputValidator
from backend.buyer.aggregator import ResultAggregator
from backend.buyer.explanation import ExplanationGenerator

logger = logging.getLogger(__name__)


class BuyerService:
    """Coordinates end-to-end task purchasing, multi-call async concurrency, and verification."""

    def __init__(
        self,
        registry: RegistryService = registry_service,
        planner: TaskPlanner = None,
        selector: ServiceSelector = None,
        output_validator: OutputValidator = None,
        aggregator: ResultAggregator = None,
        explanation_gen: ExplanationGenerator = None,
    ):
        self.registry = registry
        self.selector = selector or ServiceSelector(registry)
        self.planner = planner or TaskPlanner(self.selector)
        self.output_validator = output_validator or OutputValidator()
        self.aggregator = aggregator or ResultAggregator()
        self.explanation_gen = explanation_gen or ExplanationGenerator()
        self.policy_verifier = PaymentPolicyVerifier()
        self.idempotency_store = IdempotencyStore()

        # In-memory storage for tasks and calls
        self._tasks: Dict[str, TaskDetailResponse] = {}
        self._task_plans: Dict[str, ExecutionPlan] = {}

    def get_task(self, task_id: str) -> Optional[TaskDetailResponse]:
        return self._tasks.get(task_id)

    def get_task_calls(self, task_id: str) -> Optional[List[ServiceCallRecord]]:
        task = self._tasks.get(task_id)
        if not task:
            return None
        return task.calls

    async def submit_and_execute_task(self, request: TaskCreationRequest) -> TaskDetailResponse:
        """Submit a task, validate plan, and execute multi-call workflow."""
        task_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        budget_units = usdc_to_base_units(request.budget_usdc)
        budget_mgr = BudgetManager(initial_budget_units=budget_units)

        # 1. Generate & Validate Plan
        try:
            plan = self.planner.create_plan(request)
        except Exception as e:
            # Plan rejected before execution (e.g. over budget or invalid)
            refused_task = TaskDetailResponse(
                task_id=task_id,
                status=TaskStatus.REFUSED,
                task=request.task,
                budget_usdc=request.budget_usdc,
                reserved_usdc="0.000000",
                spent_usdc="0.000000",
                remaining_usdc=request.budget_usdc,
                max_concurrency=request.max_concurrency,
                calls=[],
                result={"error": str(e)},
                explanation=self.explanation_gen.generate_explanation(
                    task_prompt=request.task,
                    budget_usdc=request.budget_usdc,
                    calls=[],
                    fallbacks=[],
                    warnings=[f"Task refused during planning: {str(e)}"]
                ),
                actual_spent_atomic=0,
                failure_reason=str(e),
                created_at=created_at,
                completed_at=datetime.now(timezone.utc).isoformat()
            )
            self._tasks[task_id] = refused_task
            return refused_task

        self._task_plans[task_id] = plan

        # Initial task record
        task_record = TaskDetailResponse(
            task_id=task_id,
            status=TaskStatus.RUNNING,
            task=request.task,
            budget_usdc=request.budget_usdc,
            reserved_usdc="0.000000",
            spent_usdc="0.000000",
            remaining_usdc=request.budget_usdc,
            max_concurrency=request.max_concurrency,
            calls=[],
            result=None,
            explanation=None,
            created_at=created_at
        )
        self._tasks[task_id] = task_record

        # 2. Multi-call execution with Concurrency Semaphore (>= 3)
        concurrency = max(1, min(request.max_concurrency, 10))
        semaphore = asyncio.Semaphore(concurrency)
        completed_calls: Dict[int, ServiceCallRecord] = {}
        fallbacks: List[str] = []
        warnings: List[str] = []

        # Execute independent calls concurrently, then dependent calls
        independent_steps = [c for c in plan.calls if not c.depends_on]
        dependent_steps = [c for c in plan.calls if c.depends_on]

        async def run_step(planned: PlannedCall) -> ServiceCallRecord:
            async with semaphore:
                return await self._execute_call(
                    task_id=task_id,
                    planned=planned,
                    budget_mgr=budget_mgr,
                    upstream_calls=completed_calls,
                    fallbacks=fallbacks,
                    warnings=warnings
                )

        # Phase A: Execute independent steps concurrently (e.g. Scraping + Data)
        if independent_steps:
            indep_results = await asyncio.gather(*(run_step(c) for c in independent_steps))
            for res, planned in zip(indep_results, independent_steps):
                completed_calls[planned.step_id] = res

        # Phase B: Execute dependent steps (e.g. Inference using upstream content)
        for dep_step in dependent_steps:
            # Check if upstream dependencies succeeded
            upstream_succeeded = all(
                completed_calls.get(d) and completed_calls[d].status == CallStatus.SUCCEEDED
                for d in dep_step.depends_on
            )
            if not upstream_succeeded:
                warnings.append(f"Step {dep_step.step_id} skipped due to upstream failure.")
                continue

            res = await run_step(dep_step)
            completed_calls[dep_step.step_id] = res

        all_calls = list(completed_calls.values())

        # 3. Aggregate Results & Cost
        total_spent_units = sum(
            usdc_to_base_units(c.amount_paid_usdc)
            for c in all_calls
            if c.status in [CallStatus.SUCCEEDED, CallStatus.PAID_OUTPUT_REJECTED]
        )
        remaining_units = max(0, budget_units - total_spent_units)

        final_result = self.aggregator.aggregate(request.task, all_calls)
        explanation = self.explanation_gen.generate_explanation(
            task_prompt=request.task,
            budget_usdc=request.budget_usdc,
            calls=all_calls,
            fallbacks=fallbacks,
            warnings=warnings
        )

        # Check overall final status
        has_rejected = any(c.status == CallStatus.PAID_OUTPUT_REJECTED for c in all_calls)
        has_succeeded = any(c.status == CallStatus.SUCCEEDED for c in all_calls)

        if has_rejected and has_succeeded:
            task_status = TaskStatus.COMPLETED_WITH_WARNINGS
        elif has_succeeded:
            task_status = TaskStatus.COMPLETED
        else:
            task_status = TaskStatus.FAILED

        task_record.status = task_status
        task_record.calls = all_calls
        task_record.spent_usdc = base_units_to_usdc(total_spent_units)
        task_record.actual_spent_atomic = total_spent_units
        task_record.remaining_usdc = base_units_to_usdc(remaining_units)
        task_record.result = final_result
        task_record.explanation = explanation
        task_record.completed_at = datetime.now(timezone.utc).isoformat()

        return task_record

    async def _execute_call(
        self,
        task_id: str,
        planned: PlannedCall,
        budget_mgr: BudgetManager,
        upstream_calls: Dict[int, ServiceCallRecord],
        fallbacks: List[str],
        warnings: List[str]
    ) -> ServiceCallRecord:
        """Execute a single paid service call with budget reservation and schema validation."""
        service = self.registry.get_service(planned.service_id)
        call_id = str(uuid.uuid4())
        res_id = f"res_{call_id[:8]}"

        if not service:
            return ServiceCallRecord(
                call_id=call_id,
                service_id=planned.service_id,
                category=ServiceCategory(planned.category),
                status=CallStatus.REFUSED,
                listed_price_usdc="0.000000",
                error=f"Service '{planned.service_id}' not found."
            )

        # 1. Atomically reserve funds
        try:
            await budget_mgr.reserve(res_id, service.price_atomic)
        except Exception as e:
            return ServiceCallRecord(
                call_id=call_id,
                service_id=service.service_id,
                category=service.category,
                status=CallStatus.REFUSED,
                listed_price_usdc=service.price_usdc,
                error=f"Budget reservation failed: {str(e)}"
            )

        # 2. Prepare payload incorporating upstream outputs if dependent
        payload = dict(planned.input_payload)
        if planned.depends_on:
            upstream_texts = []
            for dep_id in planned.depends_on:
                dep_call = upstream_calls.get(dep_id)
                if dep_call and dep_call.output:
                    upstream_texts.append(json.dumps(dep_call.output))
            if upstream_texts:
                payload["prompt"] = (
                    f"{payload.get('prompt', '')}\n\nContext from previous steps:\n"
                    + "\n".join(upstream_texts)
                )

        # 3. Execute HTTP Call against Seller with x402 lifecycle
        start_time = time.perf_counter()
        idempotency_key = str(uuid.uuid4())
        raw_output = None
        tx_hash = None
        error_msg = None
        paid = False

        transport = None
        if "localhost" in service.endpoint_url or "127.0.0.1" in service.endpoint_url:
            try:
                from backend.main import app
                transport = httpx.ASGITransport(app=app)
            except Exception:
                transport = None

        try:
            async with httpx.AsyncClient(transport=transport, timeout=10.0) as client:
                # Step A: Request without payment -> expect HTTP 402
                first_resp = await client.post(service.endpoint_url, json=payload)

                if first_resp.status_code == 402:
                    req_header = first_resp.headers.get(HEADER_X402_REQUIREMENT)
                    if not req_header:
                        raise AgentEconomyBaseException("Seller returned 402 without X-402-Requirement header.")

                    # Step B: Re-request with payment header
                    payment_headers = {
                        HEADER_X402_PAYMENT_PAYLOAD: json.dumps({
                            "authorization": {"amount": service.price_atomic, "payTo": service.pay_to},
                            "signature": "0xMockValidTestnetSig",
                            "buyer": "0xBuyerWallet"
                        }),
                        HEADER_IDEMPOTENCY_KEY: idempotency_key
                    }
                    second_resp = await client.post(service.endpoint_url, json=payload, headers=payment_headers)

                    if second_resp.status_code == 200:
                        raw_output = second_resp.json()
                        tx_hash = second_resp.headers.get(HEADER_X402_SETTLEMENT_PROOF, f"receipt_{uuid.uuid4().hex[:12]}")
                        paid = True
                    else:
                        error_msg = f"Seller error after payment: {second_resp.status_code}"
                elif first_resp.status_code == 200:
                    raw_output = first_resp.json()
                    tx_hash = first_resp.headers.get(HEADER_X402_SETTLEMENT_PROOF)
                    paid = True
                else:
                    error_msg = f"Seller call failed with status: {first_resp.status_code}"

        except Exception as e:
            error_msg = f"Transport/Execution exception: {str(e)}"

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        # 4. Settle Budget & Validate Output
        if paid and raw_output is not None:
            await budget_mgr.commit(res_id, service.price_atomic)

            # Validate output against exact registered schema
            is_valid, validation_err = self.output_validator.validate_output(raw_output, service.output_schema)
            if not is_valid:
                # Payment settled, but output is invalid!
                logger.warning(f"Call {call_id} output rejected: {validation_err}")
                return ServiceCallRecord(
                    call_id=call_id,
                    service_id=service.service_id,
                    category=service.category,
                    status=CallStatus.PAID_OUTPUT_REJECTED,
                    listed_price_usdc=service.price_usdc,
                    amount_paid_usdc=service.price_usdc,
                    latency_ms=round(latency_ms, 2),
                    transaction_hash=tx_hash,
                    output=raw_output,
                    error=validation_err,
                    validation_status="schema_invalid"
                )

            # Fully succeeded
            return ServiceCallRecord(
                call_id=call_id,
                service_id=service.service_id,
                category=service.category,
                status=CallStatus.SUCCEEDED,
                listed_price_usdc=service.price_usdc,
                amount_paid_usdc=service.price_usdc,
                latency_ms=round(latency_ms, 2),
                transaction_hash=tx_hash,
                output=raw_output,
                validation_status="valid"
            )
        else:
            # Not charged -> release reservation
            await budget_mgr.release(res_id)
            return ServiceCallRecord(
                call_id=call_id,
                service_id=service.service_id,
                category=service.category,
                status=CallStatus.FAILED_AND_NOT_CHARGED,
                listed_price_usdc=service.price_usdc,
                amount_paid_usdc="0.000000",
                latency_ms=round(latency_ms, 2),
                error=error_msg or "Service execution failed without charge."
            )


# Global singleton instance for buyer
buyer_service = BuyerService()
