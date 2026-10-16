"""Deterministic Plan Validator enforcing budget, schema compatibility, and dependencies."""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from backend.shared.errors import AgentEconomyBaseException
from backend.registry.schemas import ServiceRecord
from backend.registry.service import RegistryService, registry_service


class PlanValidationError(AgentEconomyBaseException):
    def __init__(self, message: str):
        super().__init__(message, error_code="PLAN_VALIDATION_ERROR")


@dataclass
class PlannedCall:
    step_id: int
    category: str
    service_id: str
    input_payload: Dict[str, Any]
    estimated_price_units: int
    depends_on: List[int]
    allow_fallback: bool = True


@dataclass
class ExecutionPlan:
    task_prompt: str
    budget_units: int
    calls: List[PlannedCall]
    worst_case_cost_units: int
    max_concurrency: int


class PlanValidator:
    """Validates an execution plan deterministically before any payment or call is made."""

    def __init__(self, registry: RegistryService = registry_service):
        self.registry = registry

    def validate_plan(
        self,
        plan: ExecutionPlan,
        concurrency_limit: int = 3,
    ) -> None:
        """Validate execution plan against server-side registry and budget rules."""
        if plan.budget_units <= 0:
            raise PlanValidationError("Budget must be strictly positive.")

        if not plan.calls:
            raise PlanValidationError("Execution plan contains no service calls: insufficient budget or no matching services available.")

        # 1. Dependency validation (no cycles, valid step references)
        step_ids = {c.step_id for c in plan.calls}
        for c in plan.calls:
            for dep in c.depends_on:
                if dep not in step_ids:
                    raise PlanValidationError(f"Step {c.step_id} depends on unknown step {dep}")
                if dep >= c.step_id:
                    raise PlanValidationError(f"Invalid forward dependency from step {c.step_id} to {dep}")

        # 2. Server-side service eligibility & price verification
        total_base_cost = 0
        for c in plan.calls:
            service = self.registry.get_service(c.service_id)
            if not service:
                raise PlanValidationError(f"Proposed service '{c.service_id}' does not exist in registry.")
            if not service.enabled or not service.is_active:
                raise PlanValidationError(f"Proposed service '{c.service_id}' is disabled or inactive.")

            # Always override any model-provided price with server-side registry price!
            c.estimated_price_units = service.price_atomic
            total_base_cost += service.price_atomic

        # 3. Budget Check (Base cost cannot exceed allocated budget)
        if total_base_cost > plan.budget_units:
            raise PlanValidationError(
                f"Plan cost exceeds budget: Required {total_base_cost} base units, "
                f"but budget is only {plan.budget_units} base units."
            )

        # 4. Concurrency bounds check
        if plan.max_concurrency < 1:
            raise PlanValidationError("max_concurrency must be at least 1.")
        if plan.max_concurrency > 10:
            raise PlanValidationError("max_concurrency exceeds server limit of 10.")
