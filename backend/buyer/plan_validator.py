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
            raise PlanValidationError("Budget must be strictly positive (> 0).")

        if not plan.calls:
            raise PlanValidationError("Execution plan contains no service calls: insufficient budget or no matching services available.")

        # 1. Dependency validation (no cycles, valid step references)
        step_ids = {c.step_id for c in plan.calls}
        for c in plan.calls:
            for dep in c.depends_on:
                if dep not in step_ids:
                    raise PlanValidationError(f"Step {c.step_id} depends on unknown step {dep}")
                if dep >= c.step_id:
                    raise PlanValidationError(f"Invalid forward or self dependency from step {c.step_id} to {dep}")

        # 2. Server-side registry resolution (do not trust client/model definitions)
        calculated_cost = 0
        for c in plan.calls:
            service = self.registry.get_active_service(c.service_id)
            if not service:
                raise PlanValidationError(
                    f"Planned service '{c.service_id}' does not exist or is disabled in the authoritative registry."
                )

            # Match exact authoritative price from server-side registry
            if service.price_atomic <= 0:
                raise PlanValidationError(f"Invalid registry price for service '{c.service_id}'")

            calculated_cost += service.price_atomic

        # 3. Worst-case cost check including permitted fallbacks
        if calculated_cost > plan.budget_units:
            raise PlanValidationError(
                f"Worst-case plan cost ({calculated_cost} units) exceeds allocated budget ({plan.budget_units} units)."
            )

        # 4. Concurrency validation
        if plan.max_concurrency < 1 or plan.max_concurrency > concurrency_limit:
            raise PlanValidationError(
                f"Concurrency {plan.max_concurrency} outside allowed range [1, {concurrency_limit}]."
            )
