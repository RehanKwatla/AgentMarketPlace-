"""Buyer Orchestration Service managing task lifecycle, concurrency, Member 1 payments, and Member 4 persistence."""
import asyncio
import dataclasses
import json
import time
import uuid
import logging
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
    LedgerStatus,
    ServiceCategory,
    base_units_to_usdc,
    usdc_to_base_units,
)
from backend.shared.schemas import PaymentRequirement
from backend.payments.budget import BudgetManager
from backend.payments.policy import PaymentPolicyVerifier
from backend.payments.settlement import SettlementVerifier
from backend.payments.interfaces import BuyerPaymentClientInterface
from backend.registry.service import RegistryService, registry_service
from backend.buyer.aggregator import ResultAggregator
from backend.buyer.explanation import ExplanationGenerator
from backend.buyer.output_validator import OutputValidator
from backend.buyer.payment_client import BuyerPaymentClient
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

logger = logging.getLogger("buyer.service")


class BuyerService:
    """Manages the full buyer task lifecycle from acceptance to execution, Member 1 payment, and Member 4 ledger."""

    def __init__(
        self,
        registry: RegistryService = registry_service,
        repository: TaskRepository = task_repository,
        payment_client: Optional[BuyerPaymentClientInterface] = None,
        policy_verifier: Optional[PaymentPolicyVerifier] = None,
        settlement_verifier: Optional[SettlementVerifier] = None,
    ):
        self.registry = registry
        self.repository = repository
        self.policy_verifier = policy_verifier or PaymentPolicyVerifier()
        self.settlement_verifier = settlement_verifier or SettlementVerifier(rpc_url="", test_mode=True)
        self.payment_client = payment_client or BuyerPaymentClient(
            policy_verifier=self.policy_verifier,
            settlement_verifier=self.settlement_verifier,
        )
        self.planner = TaskPlanner()
        self.output_validator = OutputValidator()
        self.aggregator = ResultAggregator()
        self.explanation_gen = ExplanationGenerator()

        # In-memory storage indexed by task_id
        self._tasks: Dict[str, TaskDetailResponse] = {}
        self._task_plans: Dict[str, ExecutionPlan] = {}
        self._task_requests: Dict[str, TaskCreationRequest] = {}
        self._tasks_by_idempotency: Dict[str, str] = {}

    def get_task_by_idempotency_key(self, idempotency_key: str) -> Optional[TaskDetailResponse]:
        """Look up task by client idempotency key from memory or database."""
        if not idempotency_key:
            return None
        tid = self._tasks_by_idempotency.get(idempotency_key)
        if tid:
            return self.get_task(tid)
        db_rec = self.repository.get_task_by_idempotency_key(idempotency_key)
        if db_rec:
            return self.get_task(db_rec.task_id)
        return None

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
                failure_reason=getattr(db_record, "failure_reason", None),
                failure_code=getattr(db_record, "failure_code", None),
                failure_stage=getattr(db_record, "failure_stage", None),
                final_result=getattr(db_record, "final_result", None),
                idempotency_key=getattr(db_record, "idempotency_key", None),
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

        # Build provenance list from individual call records
        provenance = []
        for call in task.calls:
            provenance.append({
                "call_id": call.call_id,
                "service_id": call.service_id,
                "category": call.category.value if hasattr(call.category, "value") else str(call.category),
                "status": call.status.value if hasattr(call.status, "value") else str(call.status),
                "listed_price_usdc": call.listed_price_usdc,
                "amount_paid_usdc": call.amount_paid_usdc,
                "latency_ms": call.latency_ms,
                "tx_hash": call.transaction_hash,
                "validation_status": call.validation_status,
                "source_metadata": call.source_metadata,
                "timestamp": call.completed_at or call.created_at,
            })

        return TaskResultResponse(
            task_id=task.task_id,
            status=task.status,
            result=task.result,
            final_result=task.final_result,
            provenance=provenance,
            cost_explanation=task.cost_explanation,
            explanation=task.explanation.model_dump() if task.explanation else None,
            spent_usdc=task.spent_usdc,
            remaining_usdc=task.remaining_usdc,
            idempotency_key=task.idempotency_key,
            is_settlement_confirmed=task.is_settlement_confirmed,
            failure_code=task.failure_code,
            failure_stage=task.failure_stage,
            failure_reason=task.failure_reason,
            calls=task.calls
        )

    def list_tasks(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[TaskDetailResponse]:
        """List tasks ordered by creation time, merging memory cache and durable database records."""
        db_records = self.repository.list_tasks(status=status, limit=limit, offset=offset)
        seen_ids = set()
        results: List[TaskDetailResponse] = []

        for rec in db_records:
            t = self.get_task(rec.task_id)
            if t:
                results.append(t)
                seen_ids.add(rec.task_id)

        for tid, task in self._tasks.items():
            if tid not in seen_ids:
                if status is None or task.status == status:
                    results.append(task)
                    seen_ids.add(tid)

        results.sort(key=lambda x: x.created_at, reverse=True)
        return results[offset : offset + limit]

    def create_task(self, request: TaskCreationRequest) -> TaskDetailResponse:
        """Step 1 of Lifecycle: Validate & persist task in 'accepted' state without executing payments."""
        if request.idempotency_key:
            existing = self.get_task_by_idempotency_key(request.idempotency_key)
            if existing:
                return existing

        task_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        budget_units = usdc_to_base_units(request.budget_usdc)

        # Persist task record in database via Member 4 interface
        self.repository.save_task(
            task_id=task_id,
            task_prompt=request.task,
            budget_usdc=request.budget_usdc,
            status=TaskStatus.ACCEPTED.value,
            idempotency_key=request.idempotency_key
        )

        task_record = TaskDetailResponse(
            task_id=task_id,
            idempotency_key=request.idempotency_key,
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
        if request.idempotency_key:
            self._tasks_by_idempotency[request.idempotency_key] = task_id
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
        budget_mgr = BudgetManager(initial_budget_units=budget_units, task_id=task_id)

        # Transition to PLANNING
        task_record.status = TaskStatus.PLANNING.value
        self.repository.update_task_status(task_id, status=TaskStatus.PLANNING.value)

        # 1. Generate & Deterministically Validate Plan
        try:
            plan = self.planner.create_plan(request)
            self._task_plans[task_id] = plan
            task_record.plan_summary = plan.to_dict()
        except Exception as e:
            # Plan rejected before execution (e.g. over budget, cycle, or invalid service)
            task_record.status = TaskStatus.REFUSED.value
            task_record.failure_reason = str(e)
            task_record.failure_code = "INSUFFICIENT_BUDGET" if "budget" in str(e).lower() else "PLANNING_ERROR"
            task_record.failure_stage = "planning"
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
            self.repository.update_task_status(
                task_id,
                status=TaskStatus.REFUSED.value,
                total_cost_usdc="0.000000",
                failure_reason=task_record.failure_reason,
                final_result=task_record.final_result,
                failure_code=task_record.failure_code,
                failure_stage=task_record.failure_stage
            )
            return task_record

        # Transition to RUNNING
        task_record.status = TaskStatus.RUNNING.value
        self.repository.update_task_status(task_id, status=TaskStatus.RUNNING.value)

        # 2. Multi-call execution with Concurrency Semaphore (>= 3)
        concurrency = max(3, min(request.max_concurrency, 10))
        semaphore = asyncio.Semaphore(concurrency)
        completed_calls: Dict[int, ServiceCallRecord] = {}
        fallbacks: List[str] = []
        warnings: List[str] = []

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

        # Execute DAG stage by stage ensuring parallel execution where dependencies permit
        calls_by_id = {c.step_id: c for c in plan.calls}
        stages = plan.execution_stages or [[c.step_id for c in plan.calls]]

        for stage in stages:
            stage_calls = [calls_by_id[sid] for sid in stage if sid in calls_by_id]
            if stage_calls:
                await asyncio.gather(*(worker(c) for c in stage_calls))

        # 3. Output Validation, Aggregation, and Explanation
        all_calls = list(completed_calls.values())
        final_result = self.aggregator.aggregate_results(
            task_prompt=request.task,
            calls=all_calls
        )

        explanation = self.explanation_gen.generate_explanation(
            task_prompt=request.task,
            budget_usdc=request.budget_usdc,
            calls=all_calls,
            fallbacks=fallbacks,
            warnings=warnings,
            planned_calls=plan.calls
        )

        total_spent_usdc = explanation.verified_total_spend_usdc
        total_spent_units = usdc_to_base_units(total_spent_usdc)
        remaining_usdc = explanation.remaining_budget_usdc
        remaining_units = usdc_to_base_units(remaining_usdc)

        # Check overall final status
        has_pending_recon = any(c.status == CallStatus.PENDING_RECONCILIATION for c in all_calls)
        has_rejected = any(c.status == CallStatus.PAID_OUTPUT_REJECTED for c in all_calls)
        has_succeeded = any(c.status == CallStatus.SUCCEEDED for c in all_calls)
        has_refused = any(c.status == CallStatus.REFUSED for c in all_calls)

        task_failure_code = None
        task_failure_stage = None

        if has_pending_recon:
            task_status = TaskStatus.PENDING_RECONCILIATION.value
            task_failure_code = "SETTLEMENT_PENDING_RECONCILIATION"
            task_failure_stage = "settlement_verification"
        elif has_rejected and has_succeeded:
            task_status = TaskStatus.COMPLETED_WITH_WARNINGS.value
            task_failure_code = "OUTPUT_VALIDATION_FAILED"
            task_failure_stage = "output_validation"
        elif has_succeeded:
            task_status = TaskStatus.COMPLETED.value
        elif has_refused:
            task_status = TaskStatus.REFUSED.value
            task_failure_code = "TASK_REFUSED"
            task_failure_stage = "planning"
        else:
            task_status = TaskStatus.FAILED.value
            task_failure_code = "TASK_EXECUTION_FAILED"
            task_failure_stage = "seller_execution"

        is_settlement_confirmed = any(c.is_settlement_confirmed for c in all_calls)

        if task_status == TaskStatus.FAILED.value and not task_record.failure_reason:
            failed_reasons = [f"{c.service_id}: {c.error}" for c in all_calls if c.error]
            if failed_reasons:
                task_record.failure_reason = "Task execution failed: " + "; ".join(failed_reasons)
            elif warnings:
                task_record.failure_reason = "Task execution failed: " + "; ".join(warnings)
            else:
                task_record.failure_reason = "Task execution failed: No service calls succeeded."
        elif task_status == TaskStatus.REFUSED.value and not task_record.failure_reason:
            refused_reasons = [f"{c.service_id}: {c.error}" for c in all_calls if c.status == CallStatus.REFUSED and c.error]
            if refused_reasons:
                task_record.failure_reason = "Task refused: " + "; ".join(refused_reasons)
            elif warnings:
                task_record.failure_reason = "Task refused: " + "; ".join(warnings)
            else:
                task_record.failure_reason = "Task refused: Insufficient budget or incompatible services."
        elif task_status == TaskStatus.COMPLETED_WITH_WARNINGS.value and not task_record.failure_reason:
            warn_reasons = [f"{c.service_id}: {c.error}" for c in all_calls if c.error] + warnings
            if warn_reasons:
                task_record.failure_reason = "Completed with warnings: " + "; ".join(warn_reasons)

        task_record.status = task_status
        task_record.failure_code = task_failure_code
        task_record.failure_stage = task_failure_stage
        task_record.is_settlement_confirmed = is_settlement_confirmed
        task_record.calls = all_calls
        task_record.spent_usdc = total_spent_usdc
        task_record.spent_atomic = total_spent_units
        task_record.actual_spent_atomic = total_spent_units
        task_record.remaining_usdc = remaining_usdc
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
            total_cost_usdc=base_units_to_usdc(total_spent_units),
            failure_reason=task_record.failure_reason,
            final_result=task_record.final_result,
            failure_code=task_failure_code,
            failure_stage=task_failure_stage
        )

        return task_record

    async def submit_and_execute_task(
        self,
        request: TaskCreationRequest,
        background: bool = False
    ) -> TaskDetailResponse:
        """Create task, persist it, and if execute_now is True, run the execution pipeline."""
        if request.idempotency_key:
            existing = self.get_task_by_idempotency_key(request.idempotency_key)
            if existing:
                if existing.status in [
                    TaskStatus.RUNNING.value,
                    TaskStatus.COMPLETED.value,
                    TaskStatus.COMPLETED_WITH_WARNINGS.value,
                    TaskStatus.REFUSED.value,
                    TaskStatus.FAILED.value,
                    TaskStatus.PENDING_RECONCILIATION.value,
                ]:
                    return existing
                if request.execute_now:
                    return await self.execute_task(existing.task_id)
                return existing

        task_record = self.create_task(request)
        if request.execute_now:
            if background or getattr(request, "background", False):
                asyncio.create_task(self.execute_task(task_record.task_id))
                return task_record
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
        """Execute a single paid service call with Member 1 payment engine and Member 4 persistence."""
        service = self.registry.get_service(planned.service_id)
        # Deterministic stable call ID and idempotency key
        call_id = f"call_{task_id[:8]}_step{planned.step_id}_{planned.service_id}"
        idempotency_key = f"idem_{task_id}_{planned.step_id}_{planned.service_id}"
        res_id = f"res_{task_id[:8]}_{planned.step_id}"

        if not service:
            err = f"Service '{planned.service_id}' not found in registry."
            self.repository.record_call_to_ledger(
                task_id=task_id,
                request_id=call_id,
                service_id=planned.service_id,
                listed_price=base_units_to_usdc(planned.estimated_price_units),
                amount_paid="0.000000",
                status=LedgerStatus.REFUSED.value,
                error_reason=err
            )
            return ServiceCallRecord(
                call_id=call_id,
                service_id=planned.service_id,
                category=ServiceCategory(planned.category),
                step_id=planned.step_id,
                depends_on=planned.depends_on,
                status=CallStatus.REFUSED,
                listed_price_usdc=base_units_to_usdc(planned.estimated_price_units),
                error_code="SERVICE_NOT_FOUND",
                failure_stage="service_lookup",
                user_message="Requested service not found in registry.",
                ledger_reference=call_id,
                is_settlement_confirmed=False,
                error=err
            )

        # 1. Dependency-aware execution gate: Check that all upstream dependencies succeeded with valid output
        if planned.depends_on:
            unmet_deps = []
            for dep_id in planned.depends_on:
                dep_call = upstream_calls.get(dep_id)
                if not dep_call or dep_call.status != CallStatus.SUCCEEDED or not dep_call.output:
                    dep_status = dep_call.status.value if dep_call else "missing"
                    unmet_deps.append(f"step {dep_id} (status: {dep_status})")

            if unmet_deps:
                err = f"Upstream dependency failed or unfulfilled: {', '.join(unmet_deps)}. Dependent call skipped."
                warnings.append(err)
                record = ServiceCallRecord(
                    call_id=call_id,
                    service_id=service.service_id,
                    category=service.category,
                    step_id=planned.step_id,
                    depends_on=planned.depends_on,
                    status=CallStatus.FAILED_AND_NOT_CHARGED,
                    listed_price_usdc=service.price_usdc,
                    amount_paid_usdc="0.000000",
                    error_code="DEPENDENCY_FAILED",
                    failure_stage="dependency_check",
                    user_message="Prior required service call failed or produced invalid output.",
                    ledger_reference=call_id,
                    network=service.network,
                    is_settlement_confirmed=False,
                    error=err,
                    validation_status="not_applicable"
                )
                self.repository.record_call_to_ledger(
                    task_id=task_id,
                    request_id=call_id,
                    service_id=service.service_id,
                    listed_price=service.price_usdc,
                    amount_paid="0.000000",
                    status=LedgerStatus.FAILED_AND_NOT_CHARGED.value,
                    error_reason=err
                )
                return record

        # 2. Recheck remaining budget in atomic BudgetManager before attempting reservation
        if budget_mgr.available_budget < service.price_atomic:
            err = f"Budget exhausted: required {service.price_atomic} base units, but only {budget_mgr.available_budget} available."
            warnings.append(err)
            self.repository.record_call_to_ledger(
                task_id=task_id,
                request_id=call_id,
                service_id=service.service_id,
                listed_price=service.price_usdc,
                amount_paid="0.000000",
                status=LedgerStatus.REFUSED.value,
                error_reason=err
            )
            return ServiceCallRecord(
                call_id=call_id,
                service_id=service.service_id,
                category=service.category,
                step_id=planned.step_id,
                depends_on=planned.depends_on,
                status=CallStatus.REFUSED,
                listed_price_usdc=service.price_usdc,
                error_code="INSUFFICIENT_BUDGET",
                failure_stage="budget_reservation",
                user_message="Remaining task budget is insufficient for this service call.",
                ledger_reference=call_id,
                network=service.network,
                is_settlement_confirmed=False,
                error=err
            )

        # 3. Two-phase atomic budget reservation using Member 1 BudgetManager
        try:
            await budget_mgr.reserve(res_id, service.price_atomic)
        except Exception as e:
            err = f"Budget reservation failed: {str(e)}"
            self.repository.record_call_to_ledger(
                task_id=task_id,
                request_id=call_id,
                service_id=service.service_id,
                listed_price=service.price_usdc,
                amount_paid="0.000000",
                status=LedgerStatus.REFUSED.value,
                error_reason=err
            )
            return ServiceCallRecord(
                call_id=call_id,
                service_id=service.service_id,
                category=service.category,
                step_id=planned.step_id,
                depends_on=planned.depends_on,
                status=CallStatus.REFUSED,
                listed_price_usdc=service.price_usdc,
                error_code="INSUFFICIENT_BUDGET",
                failure_stage="budget_reservation",
                user_message="Failed to reserve budget for this service call.",
                ledger_reference=call_id,
                network=service.network,
                is_settlement_confirmed=False,
                error=err
            )

        # 4. Pass each seller only the validated inputs it requires according to Member 2 schemas
        if service.category == ServiceCategory.DATA:
            payload = {"symbol": planned.input_payload.get("symbol", "ETH")}
        elif service.category == ServiceCategory.SCRAPING:
            payload = {"url": planned.input_payload.get("url", "https://ethereum.org")}
        elif service.category == ServiceCategory.INFERENCE:
            context_blocks = []
            for dep_id in planned.depends_on:
                dep_call = upstream_calls.get(dep_id)
                if dep_call and dep_call.output:
                    out = dep_call.output
                    if dep_call.category == ServiceCategory.DATA:
                        context_blocks.append(
                            f"Market Data ({out.get('symbol', 'N/A')}): Price ${out.get('price', 'N/A')}, 24h Volume {out.get('volume_24h', 'N/A')}"
                        )
                    elif dep_call.category == ServiceCategory.SCRAPING:
                        title = out.get("title", out.get("url", "Webpage"))
                        content = out.get("content", "")
                        context_blocks.append(
                            f"Scraped Article from {out.get('url', 'N/A')} ({title}):\n{content}"
                        )
                    elif dep_call.category == ServiceCategory.INFERENCE:
                        context_blocks.append(f"Prior Inference Output: {out.get('response', '')}")

            base_prompt = planned.input_payload.get("prompt", "")
            if context_blocks:
                joined_context = "\n\n".join(context_blocks)
                synthesized_prompt = f"{base_prompt}\n\nInputs from upstream steps:\n{joined_context}\n\nPlease synthesize an analytical summary."
            else:
                synthesized_prompt = base_prompt

            payload = {
                "prompt": synthesized_prompt,
                "max_tokens": planned.input_payload.get("max_tokens", 200),
                "temperature": planned.input_payload.get("temperature", 0.7)
            }
        else:
            payload = dict(planned.input_payload)

        # 5. Execute HTTP Call against Seller with x402 lifecycle
        start_time = time.perf_counter()
        raw_output = None
        tx_hash = None
        error_msg = None
        call_error_code: Optional[str] = None
        call_failure_stage: Optional[str] = None
        call_user_message: Optional[str] = None
        payment_attempt_id: Optional[str] = None
        paid = False
        payment_dispatched = False
        uncertain_payment = False
        policy_violation = False

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
                    # Step A: Parse requirement from official standard headers or custom compatibility headers
                    req_obj = None
                    try:
                        from backend.payments.x402_adapter import x402_adapter
                        req_obj = x402_adapter.parse_challenge_from_headers(resp_402.headers)
                    except Exception:
                        req_obj = None

                    if req_obj is None:
                        req_header = resp_402.headers.get(HEADER_X402_REQUIREMENT)
                        if not req_header:
                            call_error_code = "PAYMENT_CHALLENGE_FAILED"
                            call_failure_stage = "seller_challenge"
                            call_user_message = "Seller returned HTTP 402 without a valid payment requirement."
                            logger.warning("Call %s: invalid 402 requirement header from seller: %s", call_id, resp_402.headers)
                            raise ValueError(call_user_message)
                        req_data = json.loads(req_header)
                        req_obj = PaymentRequirement(**req_data)

                    # Step B: Policy verification via Member 1 PolicyVerifier
                    try:
                        self.policy_verifier.verify(
                            requirement=req_obj,
                            registered_service=service
                        )
                    except Exception as pe:
                        policy_violation = True
                        call_error_code = "POLICY_VIOLATION"
                        call_failure_stage = "policy_verification"
                        call_user_message = f"Payment terms violate service registry policy: {str(pe)}"
                        logger.warning("Call %s policy verification failed: %s", call_id, str(pe))
                        raise pe

                    # Step C: Prepare signed authorization payload via Member 1 PaymentClient
                    payment_attempt_id = f"pay_att_{idempotency_key}"
                    try:
                        payment_payload = await self.payment_client.create_payment_payload(
                            requirement=req_obj,
                            idempotency_key=idempotency_key
                        )
                    except Exception as pay_err:
                        is_insufficient = "insufficient" in str(pay_err).lower() or "balance" in str(pay_err).lower()
                        call_error_code = "INSUFFICIENT_FUNDS" if is_insufficient else "PAYMENT_AUTHORIZATION_FAILED"
                        call_failure_stage = "payment_authorization"
                        call_user_message = "Buyer balance insufficient to authorize payment." if is_insufficient else "Payment authorization generation failed."
                        logger.error("Call %s payment authorization failed: %s", call_id, str(pay_err))
                        raise pay_err

                    payment_dispatched = True

                    # Step D: Re-request with dual compatibility payment headers
                    outbound_headers = {
                        HEADER_IDEMPOTENCY_KEY: idempotency_key,
                        HEADER_X402_PAYMENT_PAYLOAD: json.dumps(payment_payload.model_dump())
                    }
                    try:
                        from backend.payments.x402_adapter import x402_adapter
                        extra_headers = x402_adapter.build_payment_headers(
                            payment_payload=payment_payload.model_dump(),
                            requirement=req_obj,
                            idempotency_key=idempotency_key
                        )
                        outbound_headers.update(extra_headers)
                    except Exception:
                        pass

                    resp_paid = await client.post(
                        service.endpoint_url,
                        json=payload,
                        headers=outbound_headers
                    )

                    content_type = ""
                    if resp_paid.status_code == 200:
                        content_type = resp_paid.headers.get("content-type", "application/json")
                        proof_header = None
                        try:
                            from backend.payments.x402_adapter import x402_adapter
                            proof_header = x402_adapter.extract_settlement_proof(resp_paid.headers)
                        except Exception:
                            proof_header = None
                        if not proof_header:
                            proof_header = resp_paid.headers.get(HEADER_X402_SETTLEMENT_PROOF)
                        # Step E: Verify settlement proof via Member 1 SettlementVerifier
                        receipt = await self.payment_client.verify_settlement(proof_header)
                        if receipt and (receipt.tx_hash or receipt.facilitator_receipt_id):
                            paid = True
                            tx_hash = receipt.tx_hash or receipt.facilitator_receipt_id
                            try:
                                raw_output = resp_paid.json()
                            except Exception as je:
                                raw_output = resp_paid.text
                                error_msg = f"Malformed JSON: {str(je)}"
                                logger.warning("Call %s malformed JSON from seller: %s", call_id, str(je))
                        else:
                            # HTTP 200 returned but settlement proof is missing or unverified -> UNCERTAIN SETTLEMENT
                            uncertain_payment = True
                            call_error_code = "SETTLEMENT_PENDING_RECONCILIATION"
                            call_failure_stage = "settlement_verification"
                            call_user_message = "Seller returned HTTP 200 but settlement proof is missing or unconfirmed."
                            error_msg = call_user_message
                            logger.warning("Call %s settlement unverified. proof_header: %s", call_id, proof_header)
                            try:
                                raw_output = resp_paid.json()
                            except Exception:
                                raw_output = resp_paid.text
                    elif resp_paid.status_code in [502, 503, 504]:
                        uncertain_payment = True
                        call_error_code = "SETTLEMENT_PENDING_RECONCILIATION"
                        call_failure_stage = "seller_execution"
                        call_user_message = f"Gateway error HTTP {resp_paid.status_code} received after payment dispatch."
                        error_msg = f"Gateway error HTTP {resp_paid.status_code} after payment dispatched: {resp_paid.text}"
                        logger.error("Call %s gateway error post-payment: %s", call_id, resp_paid.text)
                    else:
                        call_error_code = "SELLER_EXECUTION_ERROR"
                        call_failure_stage = "seller_execution"
                        call_user_message = f"Seller returned execution error HTTP {resp_paid.status_code}."
                        error_msg = f"Seller HTTP {resp_paid.status_code}: {resp_paid.text}"
                        logger.error("Call %s seller error post-payment: HTTP %s: %s", call_id, resp_paid.status_code, resp_paid.text)

                elif resp_402.status_code == 200:
                    paid = False
                    raw_output = resp_402.json()
                else:
                    call_error_code = "SELLER_EXECUTION_ERROR"
                    call_failure_stage = "seller_challenge"
                    call_user_message = f"Seller returned unexpected status HTTP {resp_402.status_code} before payment challenge."
                    error_msg = f"Unexpected status {resp_402.status_code}: {resp_402.text}"
                    logger.error("Call %s unexpected initial status: %s", call_id, resp_402.text)

        except asyncio.CancelledError:
            if payment_dispatched and not paid:
                uncertain_payment = True
                call_error_code = "SETTLEMENT_PENDING_RECONCILIATION"
                call_failure_stage = "task_cancelled"
                call_user_message = "Call cancelled while payment was dispatched."
                error_msg = call_user_message
                logger.warning("Call %s cancelled after payment dispatched", call_id)
            else:
                await budget_mgr.release(res_id)
                error_msg = "Call cancelled before payment challenge completion."
                record = ServiceCallRecord(
                    call_id=call_id,
                    service_id=service.service_id,
                    category=service.category,
                    step_id=planned.step_id,
                    depends_on=planned.depends_on,
                    status=CallStatus.FAILED_AND_NOT_CHARGED,
                    listed_price_usdc=service.price_usdc,
                    amount_paid_usdc="0.000000",
                    error_code="TASK_CANCELLED",
                    failure_stage="task_cancelled",
                    user_message="Call cancelled prior to payment.",
                    ledger_reference=call_id,
                    network=service.network,
                    is_settlement_confirmed=False,
                    error=error_msg,
                    validation_status="not_applicable",
                    completed_at=datetime.now(timezone.utc).isoformat()
                )
                self.repository.record_call_to_ledger(
                    task_id=task_id,
                    request_id=call_id,
                    service_id=service.service_id,
                    listed_price=service.price_usdc,
                    amount_paid="0.000000",
                    status=LedgerStatus.FAILED_AND_NOT_CHARGED.value,
                    error_reason=error_msg
                )
                raise
        except httpx.TimeoutException as te:
            if payment_dispatched:
                uncertain_payment = True
                call_error_code = "SETTLEMENT_PENDING_RECONCILIATION"
                call_failure_stage = "seller_execution"
                call_user_message = "Network timeout after payment dispatch; status uncertain."
                error_msg = f"Network timeout after payment dispatched: {str(te)}"
                logger.error("Call %s network timeout after payment dispatch: %s", call_id, str(te))
            else:
                call_error_code = "SELLER_UNAVAILABLE"
                call_failure_stage = "seller_challenge"
                call_user_message = "Network timeout before payment challenge."
                error_msg = f"Network timeout before payment challenge: {str(te)}"
                logger.error("Call %s network timeout before payment challenge: %s", call_id, str(te))
        except Exception as e:
            if payment_dispatched and not paid:
                uncertain_payment = True
                call_error_code = call_error_code or "SETTLEMENT_PENDING_RECONCILIATION"
                call_failure_stage = call_failure_stage or "seller_execution"
                call_user_message = call_user_message or "Unexpected exception after payment dispatch."
                error_msg = f"Exception after payment dispatched: {str(e)}"
                logger.error("Call %s exception after payment dispatch: %s", call_id, str(e), exc_info=True)
            else:
                call_error_code = call_error_code or "GENERIC_ERROR"
                call_failure_stage = call_failure_stage or "seller_challenge"
                call_user_message = call_user_message or "Service invocation failed."
                error_msg = f"HTTP call failed: {str(e)}"
                logger.error("Call %s HTTP call failed before payment: %s", call_id, str(e))

        latency = (time.perf_counter() - start_time) * 1000.0
        completed_time = datetime.now(timezone.utc).isoformat()
        schema_ver = getattr(service, "registry_version", "1.0.0")
        source_meta = {
            "endpoint_url": service.endpoint_url,
            "network": service.network,
            "seller_pay_to": service.pay_to,
            "category": service.category.value,
            "source_timestamp": completed_time,
            "data_freshness_seconds": round(latency / 1000.0, 3),
        }

        # 6. Settle Budget & Output Validation
        if paid:
            await budget_mgr.commit(res_id, service.price_atomic)
            amount_paid = service.price_usdc

            # Validate output against registered Draft-7 output schema
            is_valid, val_err = self.output_validator.validate_output(
                raw_output, service.output_schema, content_type=content_type
            )
            if not is_valid:
                warnings.append(f"Seller {service.service_id} output validation failed: {val_err}")
                record = ServiceCallRecord(
                    call_id=call_id,
                    service_id=service.service_id,
                    category=service.category,
                    step_id=planned.step_id,
                    depends_on=planned.depends_on,
                    status=CallStatus.PAID_OUTPUT_REJECTED,
                    listed_price_usdc=service.price_usdc,
                    amount_paid_usdc=amount_paid,
                    latency_ms=round(latency, 2),
                    transaction_hash=tx_hash,
                    payment_reference=tx_hash,
                    payment_attempt_id=payment_attempt_id,
                    ledger_reference=call_id,
                    network=service.network,
                    is_settlement_confirmed=True,
                    error_code="OUTPUT_VALIDATION_FAILED",
                    failure_stage="output_validation",
                    user_message="Service payment settled, but provider response failed output schema validation.",
                    schema_version=schema_ver,
                    output=raw_output if isinstance(raw_output, dict) else {"raw": str(raw_output)},
                    error=f"Output validation rejected: {val_err}",
                    validation_status="rejected",
                    validation_details={"schema_type": "Draft-7", "is_valid": False, "error": val_err},
                    source_metadata=source_meta,
                    completed_at=completed_time
                )
                self.repository.record_call_to_ledger(
                    task_id=task_id,
                    request_id=call_id,
                    service_id=service.service_id,
                    listed_price=service.price_usdc,
                    amount_paid=amount_paid,
                    status=LedgerStatus.PAID_OUTPUT_REJECTED.value,
                    tx_hash=tx_hash,
                    latency_ms=round(latency, 2),
                    error_reason=record.error
                )
                return record

            record = ServiceCallRecord(
                call_id=call_id,
                service_id=service.service_id,
                category=service.category,
                step_id=planned.step_id,
                depends_on=planned.depends_on,
                status=CallStatus.SUCCEEDED,
                listed_price_usdc=service.price_usdc,
                amount_paid_usdc=amount_paid,
                latency_ms=round(latency, 2),
                transaction_hash=tx_hash,
                payment_reference=tx_hash,
                payment_attempt_id=payment_attempt_id,
                ledger_reference=call_id,
                network=service.network,
                is_settlement_confirmed=True,
                schema_version=schema_ver,
                output=raw_output,
                validation_status="accepted",
                validation_details={"schema_type": "Draft-7", "is_valid": True, "error": None},
                source_metadata=source_meta,
                completed_at=completed_time
            )
            self.repository.record_call_to_ledger(
                task_id=task_id,
                request_id=call_id,
                service_id=service.service_id,
                listed_price=service.price_usdc,
                amount_paid=amount_paid,
                status=LedgerStatus.PAID.value,
                tx_hash=tx_hash,
                latency_ms=round(latency, 2)
            )
            return record

        elif uncertain_payment:
            # UNCERTAIN PAYMENT: Do NOT release reservation! Do NOT retry blindly! Do NOT run fallbacks!
            warnings.append(f"Call to {service.service_id} has uncertain settlement: {error_msg}. Awaiting reconciliation.")
            record = ServiceCallRecord(
                call_id=call_id,
                service_id=service.service_id,
                category=service.category,
                step_id=planned.step_id,
                depends_on=planned.depends_on,
                status=CallStatus.PENDING_RECONCILIATION,
                listed_price_usdc=service.price_usdc,
                amount_paid_usdc="0.000000",
                latency_ms=round(latency, 2),
                payment_attempt_id=payment_attempt_id,
                ledger_reference=call_id,
                network=service.network,
                is_settlement_confirmed=False,
                transaction_hash=None,
                error_code=call_error_code or "SETTLEMENT_PENDING_RECONCILIATION",
                failure_stage=call_failure_stage or "settlement_verification",
                user_message=call_user_message or "Payment was dispatched but blockchain settlement cannot be verified. Marked for reconciliation.",
                error=f"Uncertain payment settlement: {error_msg}",
                validation_status="pending_reconciliation",
                source_metadata=source_meta,
                completed_at=completed_time
            )
            self.repository.record_call_to_ledger(
                task_id=task_id,
                request_id=call_id,
                service_id=service.service_id,
                listed_price=service.price_usdc,
                amount_paid="0.000000",
                status="pending reconciliation",
                error_reason=f"UNCERTAIN_SETTLEMENT: {error_msg}"
            )
            return record

        else:
            # Definite non-payment failure: release budget reservation
            await budget_mgr.release(res_id)

            # Check if an eligible fallback exists and can be afforded within remaining budget
            if planned.allow_fallback and planned.fallback_service_ids:
                for fb_id in planned.fallback_service_ids:
                    fb_svc = self.registry.get_service(fb_id)
                    if not fb_svc or not fb_svc.is_active:
                        continue
                    # Recheck remaining budget before scheduling fallback!
                    if budget_mgr.available_budget < fb_svc.price_atomic:
                        warnings.append(
                            f"Fallback to {fb_id} rejected: price {fb_svc.price_atomic} exceeds remaining budget {budget_mgr.available_budget}."
                        )
                        continue

                    # Execute fallback
                    fallbacks.append(f"Service {service.service_id} failed ({error_msg}); running fallback {fb_id}")
                    if hasattr(planned, "model_copy"):
                        fb_plan = planned.model_copy(update={
                            "service_id": fb_id,
                            "allow_fallback": False,
                            "fallback_service_ids": []
                        })
                    elif dataclasses.is_dataclass(planned):
                        fb_plan = dataclasses.replace(
                            planned,
                            service_id=fb_id,
                            allow_fallback=False,
                            fallback_service_ids=[]
                        )
                    else:
                        fb_plan = planned
                    fb_record = await self._execute_call(
                        task_id=task_id,
                        planned=fb_plan,
                        budget_mgr=budget_mgr,
                        upstream_calls=upstream_calls,
                        fallbacks=fallbacks,
                        warnings=warnings
                    )
                    return fb_record

            fallbacks.append(f"Call to {service.service_id} failed: {error_msg}")
            assigned_status = CallStatus.REFUSED if policy_violation else CallStatus.FAILED_AND_NOT_CHARGED
            assigned_ledger_status = LedgerStatus.REFUSED if policy_violation else LedgerStatus.FAILED_AND_NOT_CHARGED
            record = ServiceCallRecord(
                call_id=call_id,
                service_id=service.service_id,
                category=service.category,
                step_id=planned.step_id,
                depends_on=planned.depends_on,
                status=assigned_status,
                listed_price_usdc=service.price_usdc,
                amount_paid_usdc="0.000000",
                latency_ms=round(latency, 2),
                payment_attempt_id=payment_attempt_id if payment_attempt_id else None,
                ledger_reference=call_id,
                network=service.network if service else None,
                is_settlement_confirmed=False,
                transaction_hash=None,
                error_code=call_error_code or ("POLICY_VIOLATION" if policy_violation else "SELLER_EXECUTION_ERROR"),
                failure_stage=call_failure_stage or ("policy_verification" if policy_violation else "seller_execution"),
                user_message=call_user_message or ("Service payment policy violation." if policy_violation else "Service call failed without charge."),
                error=error_msg,
                validation_status="not_applicable",
                source_metadata=source_meta,
                completed_at=completed_time
            )
            self.repository.record_call_to_ledger(
                task_id=task_id,
                request_id=call_id,
                service_id=service.service_id,
                listed_price=service.price_usdc,
                amount_paid="0.000000",
                status=assigned_ledger_status.value,
                latency_ms=round(latency, 2),
                error_reason=error_msg
            )
            return record


# Global singleton instance
buyer_service = BuyerService()
