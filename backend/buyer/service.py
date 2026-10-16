"""Buyer Orchestration Service managing task lifecycle, concurrency, and persistence."""
import asyncio
import json
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
    NETWORK_BASE_SEPOLIA,
    USDC_BASE_SEPOLIA,
    ServiceCategory,
    base_units_to_usdc,
    usdc_to_base_units,
)
from backend.shared.schemas import PaymentRequirement
from backend.payments.budget import BudgetManager
from backend.payments.policy import PaymentPolicyVerifier
from backend.registry.service import RegistryService, registry_service
from backend.buyer.aggregator import ResultAggregator
from backend.buyer.explanation import ExplanationGenerator
from backend.buyer.output_validator import OutputValidator
from backend.buyer.plan_validator import ExecutionPlan, PlannedCall
from backend.buyer.planner import TaskPlanner
from backend.buyer.repository import task_repository, TaskRepository
from backend.buyer.schemas import (
    CallStatus,
    ServiceCallRecord,
    TaskCreationRequest,
    TaskDetailResponse,
    TaskResultResponse,
    TaskStatus,
)


class BuyerService:
    """Manages the full buyer task lifecycle from acceptance to execution and explanation."""

    def __init__(
        self,
        registry: RegistryService = registry_service,
        repository: TaskRepository = task_repository,
    ):
        self.registry = registry
        self.repository = repository
        self.planner = TaskPlanner()
        self.output_validator = OutputValidator()
        self.aggregator = ResultAggregator()
        self.explanation_gen = ExplanationGenerator()
        self.policy_verifier = PaymentPolicyVerifier()

        # In-memory storage indexed by task_id
        self._tasks: Dict[str, TaskDetailResponse] = {}
        self._task_plans: Dict[str, ExecutionPlan] = {}
        self._task_requests: Dict[str, TaskCreationRequest] = {}

    def get_task(self, task_id: str) -> Optional[TaskDetailResponse]:
        """Retrieve task detail from in-memory state or fallback to persisted database record."""
        task = self._tasks.get(task_id)
        if task:
            return task

        # Check database fallback
        db_record = self.repository.get_task(task_id)
        if db_record:
            budget_units = usdc_to_base_units(db_record.budget_usdc)
            cost_units = usdc_to_base_units(db_record.total_cost_usdc or "0.000000")
            remaining_units = max(0, budget_units - cost_units)
            fallback_task = TaskDetailResponse(
                task_id=db_record.task_id,
                status=db_record.status,
                task=db_record.task_prompt,
                budget_usdc=db_record.budget_usdc,
                budget_atomic=budget_units,
                spent_usdc=db_record.total_cost_usdc or "0.000000",
                spent_atomic=cost_units,
                actual_spent_atomic=cost_units,
                remaining_usdc=base_units_to_usdc(remaining_units),
                remaining_atomic=remaining_units,
                max_concurrency=3,
                calls=[],
                created_at=db_record.created_at.isoformat() if db_record.created_at else datetime.now(timezone.utc).isoformat()
            )
            self._tasks[task_id] = fallback_task
            return fallback_task
        return None

    def get_task_calls(self, task_id: str) -> Optional[List[ServiceCallRecord]]:
        task = self.get_task(task_id)
        if not task:
            return None
        return task.calls

    def get_task_result(self, task_id: str) -> Optional[TaskResultResponse]:
        task = self.get_task(task_id)
        if not task:
            return None

        provenance = []
        if task.result and isinstance(task.result, dict):
            provenance = task.result.get("provenance", [])

        cost_explanation = task.cost_explanation or (task.explanation.task_interpretation if task.explanation else "")
        explanation_dict = task.explanation.model_dump() if task.explanation else None

        return TaskResultResponse(
            task_id=task.task_id,
            status=task.status,
            result=task.result,
            final_result=task.final_result or (task.result.get("summary") if task.result else None),
            provenance=provenance,
            cost_explanation=cost_explanation,
            explanation=explanation_dict,
            spent_usdc=task.spent_usdc,
            remaining_usdc=task.remaining_usdc,
            calls=task.calls
        )

    def create_task(self, request: TaskCreationRequest) -> TaskDetailResponse:
        """Step 1 of Lifecycle: Validate & persist task in 'accepted' state without executing payments."""
        task_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        budget_units = usdc_to_base_units(request.budget_usdc)

        # Persist task record in database via Member 4 interface
        self.repository.save_task(
            task_id=task_id,
            task_prompt=request.task,
            budget_usdc=request.budget_usdc,
            status=TaskStatus.ACCEPTED.value
        )

        task_record = TaskDetailResponse(
            task_id=task_id,
            status=TaskStatus.ACCEPTED.value,
            task=request.task,
            budget_usdc=request.budget_usdc,
            budget_atomic=budget_units,
            reserved_usdc="0.000000",
            spent_usdc="0.000000",
            spent_atomic=0,
            actual_spent_atomic=0,
            remaining_usdc=request.budget_usdc,
            remaining_atomic=budget_units,
            max_concurrency=request.max_concurrency,
            calls=[],
            result=None,
            explanation=None,
            created_at=created_at
        )
        self._tasks[task_id] = task_record
        self._task_requests[task_id] = request
        return task_record

    async def execute_task(self, task_id: str) -> TaskDetailResponse:
        """Steps 2-4 of Lifecycle: Planning, Budget Validation, Concurrency Execution, Output Validation."""
        task_record = self.get_task(task_id)
        if not task_record:
            raise ValueError(f"Task with ID '{task_id}' not found.")

        request = self._task_requests.get(task_id)
        if not request:
            request = TaskCreationRequest(
                task=task_record.task,
                budget_usdc=task_record.budget_usdc,
                max_concurrency=task_record.max_concurrency
            )

        budget_units = usdc_to_base_units(request.budget_usdc)
        budget_mgr = BudgetManager(initial_budget_units=budget_units)

        # Transition to PLANNING
        task_record.status = TaskStatus.PLANNING.value
        self.repository.update_task_status(task_id, status=TaskStatus.PLANNING.value)

        # 1. Generate & Deterministically Validate Plan
        try:
            plan = self.planner.create_plan(request)
            self._task_plans[task_id] = plan
            task_record.plan_summary = {
                "worst_case_cost_units": plan.worst_case_cost_units,
                "steps_count": len(plan.calls),
                "services": [c.service_id for c in plan.calls]
            }
        except Exception as e:
            # Plan rejected before execution (e.g. over budget or invalid service)
            task_record.status = TaskStatus.REFUSED.value
            task_record.failure_reason = str(e)
            task_record.result = {"error": str(e)}
            task_record.final_result = f"Task refused: {str(e)}"
            task_record.explanation = self.explanation_gen.generate_explanation(
                task_prompt=request.task,
                budget_usdc=request.budget_usdc,
                calls=[],
                fallbacks=[],
                warnings=[f"Task refused during planning: {str(e)}"]
            )
            task_record.completed_at = datetime.now(timezone.utc).isoformat()
            self.repository.update_task_status(task_id, status=TaskStatus.REFUSED.value, total_cost_usdc="0.000000")
            return task_record

        # Transition to RUNNING
        task_record.status = TaskStatus.RUNNING.value
        self.repository.update_task_status(task_id, status=TaskStatus.RUNNING.value)

        # 2. Multi-call execution with Concurrency Semaphore (>= 3)
        concurrency = max(1, min(request.max_concurrency, 10))
        semaphore = asyncio.Semaphore(concurrency)
        completed_calls: Dict[int, ServiceCallRecord] = {}
        fallbacks: List[str] = []
        warnings: List[str] = []

        # Execute parallel steps first (dependencies == empty), then dependent steps
        independent_steps = [c for c in plan.calls if not c.depends_on]
        dependent_steps = [c for c in plan.calls if c.depends_on]

        async def worker(call_plan: PlannedCall):
            async with semaphore:
                record = await self._execute_call(
                    task_id=task_id,
                    planned=call_plan,
                    budget_mgr=budget_mgr,
                    upstream_calls=completed_calls,
                    fallbacks=fallbacks,
                    warnings=warnings
                )
                completed_calls[call_plan.step_id] = record

        # Run independent calls concurrently
        if independent_steps:
            await asyncio.gather(*(worker(c) for c in independent_steps))

        # Run dependent calls sequentially or as dependencies resolve
        for dep_step in dependent_steps:
            await worker(dep_step)

        # 3. Output Validation, Aggregation, and Explanation
        all_calls = list(completed_calls.values())
        final_result = self.aggregator.aggregate_results(
            task_prompt=request.task,
            calls=all_calls
        )

        total_spent_units = sum(
            usdc_to_base_units(c.amount_paid_usdc)
            for c in all_calls
            if c.status in [CallStatus.SUCCEEDED, CallStatus.PAID_OUTPUT_REJECTED]
        )
        remaining_units = max(0, budget_units - total_spent_units)

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
            task_status = TaskStatus.COMPLETED_WITH_WARNINGS.value
        elif has_succeeded:
            task_status = TaskStatus.COMPLETED.value
        else:
            task_status = TaskStatus.FAILED.value

        task_record.status = task_status
        task_record.calls = all_calls
        task_record.spent_usdc = base_units_to_usdc(total_spent_units)
        task_record.spent_atomic = total_spent_units
        task_record.actual_spent_atomic = total_spent_units
        task_record.remaining_usdc = base_units_to_usdc(remaining_units)
        task_record.remaining_atomic = remaining_units
        task_record.result = final_result
        task_record.final_result = final_result.get("summary", "")
        task_record.explanation = explanation
        task_record.cost_explanation = explanation.task_interpretation
        task_record.completed_at = datetime.now(timezone.utc).isoformat()

        # Update database persistence
        self.repository.update_task_status(
            task_id,
            status=task_status,
            total_cost_usdc=base_units_to_usdc(total_spent_units)
        )

        return task_record

    async def submit_and_execute_task(self, request: TaskCreationRequest) -> TaskDetailResponse:
        """Create task, persist it, and if execute_now is True, run the execution pipeline."""
        task_record = self.create_task(request)
        if request.execute_now:
            return await self.execute_task(task_record.task_id)
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
        """Execute a single paid service call with budget reservation, x402 negotiation, and output validation."""
        service = self.registry.get_service(planned.service_id)
        call_id = str(uuid.uuid4())
        res_id = f"res_{call_id[:8]}"

        if not service:
            return ServiceCallRecord(
                call_id=call_id,
                service_id=planned.service_id,
                category=ServiceCategory(planned.category),
                status=CallStatus.REFUSED,
                listed_price_usdc=base_units_to_usdc(planned.estimated_price_units),
                error=f"Service '{planned.service_id}' not found in registry."
            )

        # 1. Two-phase budget reservation lock
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
                # Step A: Request without payment -> expect HTTP 402 challenge
                resp_402 = await client.post(
                    service.endpoint_url,
                    json=payload,
                    headers={HEADER_IDEMPOTENCY_KEY: idempotency_key}
                )

                if resp_402.status_code == 402:
                    req_header = resp_402.headers.get(HEADER_X402_REQUIREMENT)
                    if not req_header:
                        raise ValueError("Seller returned HTTP 402 without X-402-Requirement header.")

                    req_data = json.loads(req_header)

                    # Step B: Policy verification (price gouging, network, token, recipient)
                    req_obj = PaymentRequirement(**req_data)
                    self.policy_verifier.verify(
                        requirement=req_obj,
                        registered_service=service
                    )

                    # Step C: Prepare signed authorization payload via Member 1 integration
                    payment_payload = {
                        "authorization": {
                            "network": NETWORK_BASE_SEPOLIA,
                            "token": USDC_BASE_SEPOLIA,
                            "amount": str(service.price_atomic),
                            "payTo": service.pay_to,
                            "nonce": req_data.get("nonce", "nonce_default")
                        },
                        "signature": "0x402_authorized_settlement_signature",
                        "buyer_address": "0x1000000000000000000000000000000000000001"
                    }

                    # Step D: Re-request with payment header
                    resp_paid = await client.post(
                        service.endpoint_url,
                        json=payload,
                        headers={
                            HEADER_IDEMPOTENCY_KEY: idempotency_key,
                            HEADER_X402_PAYMENT_PAYLOAD: json.dumps(payment_payload)
                        }
                    )

                    if resp_paid.status_code == 200:
                        paid = True
                        raw_output = resp_paid.json()
                        tx_hash = resp_paid.headers.get(HEADER_X402_SETTLEMENT_PROOF)
                    else:
                        error_msg = f"Seller HTTP {resp_paid.status_code}: {resp_paid.text}"
                elif resp_402.status_code == 200:
                    paid = False
                    raw_output = resp_402.json()
                else:
                    error_msg = f"Unexpected status {resp_402.status_code}: {resp_402.text}"

        except Exception as e:
            error_msg = f"HTTP call failed: {str(e)}"

        latency = (time.perf_counter() - start_time) * 1000.0

        # 4. Settle Budget & Validate Output
        if paid:
            await budget_mgr.commit(res_id, service.price_atomic)
            amount_paid = service.price_usdc

            # Validate output against registered Draft-7 output schema
            is_valid, val_err = self.output_validator.validate_output(raw_output, service.output_schema)
            if not is_valid:
                warnings.append(f"Seller {service.service_id} output validation failed: {val_err}")
                return ServiceCallRecord(
                    call_id=call_id,
                    service_id=service.service_id,
                    category=service.category,
                    status=CallStatus.PAID_OUTPUT_REJECTED,
                    listed_price_usdc=service.price_usdc,
                    amount_paid_usdc=amount_paid,
                    latency_ms=round(latency, 2),
                    transaction_hash=tx_hash,
                    output=raw_output,
                    error=f"Output validation rejected: {val_err}",
                    validation_status="rejected"
                )

            return ServiceCallRecord(
                call_id=call_id,
                service_id=service.service_id,
                category=service.category,
                status=CallStatus.SUCCEEDED,
                listed_price_usdc=service.price_usdc,
                amount_paid_usdc=amount_paid,
                latency_ms=round(latency, 2),
                transaction_hash=tx_hash,
                output=raw_output,
                validation_status="accepted"
            )
        else:
            await budget_mgr.release(res_id)
            fallbacks.append(f"Call to {service.service_id} failed: {error_msg}")
            return ServiceCallRecord(
                call_id=call_id,
                service_id=service.service_id,
                category=service.category,
                status=CallStatus.FAILED_AND_NOT_CHARGED,
                listed_price_usdc=service.price_usdc,
                amount_paid_usdc="0.000000",
                latency_ms=round(latency, 2),
                error=error_msg,
                validation_status="not_applicable"
            )


# Global singleton instance
buyer_service = BuyerService()
