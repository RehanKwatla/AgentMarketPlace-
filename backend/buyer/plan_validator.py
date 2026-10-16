"""Deterministic Plan Validator enforcing budget, schema compatibility, dependencies, and concurrency."""
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Set
from jsonschema import Draft7Validator
from backend.shared.constants import NETWORK_BASE_SEPOLIA, USDC_BASE_SEPOLIA
from backend.shared.errors import AgentEconomyBaseException
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
    depends_on: List[int] = field(default_factory=list)
    capability: str = ""
    fallback_service_ids: List[str] = field(default_factory=list)
    fallback_allowance_units: int = 0
    worst_case_price_units: int = 0
    selection_reason: str = ""
    allow_fallback: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionPlan:
    task_prompt: str
    budget_units: int
    calls: List[PlannedCall]
    worst_case_cost_units: int
    max_concurrency: int
    expected_cost_units: int = 0
    fallback_allowances_units: int = 0
    dependency_graph: Dict[int, List[int]] = field(default_factory=dict)
    execution_stages: List[List[int]] = field(default_factory=list)
    reasons_for_selection: Dict[str, str] = field(default_factory=dict)
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_prompt": self.task_prompt,
            "budget_units": self.budget_units,
            "calls": [c.to_dict() for c in self.calls],
            "worst_case_cost_units": self.worst_case_cost_units,
            "expected_cost_units": self.expected_cost_units,
            "fallback_allowances_units": self.fallback_allowances_units,
            "max_concurrency": self.max_concurrency,
            "dependency_graph": self.dependency_graph,
            "execution_stages": self.execution_stages,
            "reasons_for_selection": self.reasons_for_selection,
            "explanation": self.explanation,
        }


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
            raise PlanValidationError(
                "Execution plan contains no service calls: insufficient budget or no matching services available."
            )

        # 1. Step ID validation & duplicate detection
        step_ids: Set[int] = set()
        seen_calls: Set[str] = set()
        for c in plan.calls:
            if c.step_id <= 0:
                raise PlanValidationError(f"Invalid step ID {c.step_id}: must be positive integer.")
            if c.step_id in step_ids:
                raise PlanValidationError(f"Duplicate step ID {c.step_id} in execution plan.")
            step_ids.add(c.step_id)

            # Check for duplicate redundant identical calls
            import json
            call_sig = f"{c.service_id}:{json.dumps(c.input_payload, sort_keys=True)}"
            if call_sig in seen_calls and not c.depends_on:
                raise PlanValidationError(
                    f"Duplicate identical call to service '{c.service_id}' detected without dependency rationale."
                )
            seen_calls.add(call_sig)

        # 2. Dependency graph validation (unknown dependencies, self-deps, and cycles)
        graph: Dict[int, List[int]] = {}
        for c in plan.calls:
            for dep in c.depends_on:
                if dep not in step_ids:
                    raise PlanValidationError(f"Step {c.step_id} depends on unknown step {dep}")
                if dep == c.step_id:
                    raise PlanValidationError(f"Step {c.step_id} has invalid self-dependency on itself")
            graph[c.step_id] = list(c.depends_on)

        # Cycle detection using DFS with 3-color marking (0=white/unvisited, 1=grey/visiting, 2=black/visited)
        visited_state: Dict[int, int] = {sid: 0 for sid in step_ids}

        def dfs_cycle(node: int, path: List[int]):
            visited_state[node] = 1
            for parent in graph[node]:
                if visited_state[parent] == 1:
                    cycle_nodes = path + [parent]
                    raise PlanValidationError(
                        f"Cycle detected in execution plan dependencies: {' -> '.join(map(str, cycle_nodes))}"
                    )
                if visited_state[parent] == 0:
                    dfs_cycle(parent, path + [parent])
            visited_state[node] = 2

        for sid in step_ids:
            if visited_state[sid] == 0:
                dfs_cycle(sid, [sid])

        # 3. Server-side registry resolution (do not trust client/model definitions)
        calculated_expected_cost = 0
        calculated_worst_case_cost = 0

        for c in plan.calls:
            service = self.registry.get_active_service(c.service_id)
            if not service:
                raise PlanValidationError(
                    f"Planned service '{c.service_id}' does not exist or is disabled in the authoritative registry."
                )

            # Hard safety validations from server-side registry
            if service.network != NETWORK_BASE_SEPOLIA:
                raise PlanValidationError(
                    f"Service '{c.service_id}' violates network policy: {service.network} != {NETWORK_BASE_SEPOLIA}"
                )

            token = getattr(service, "token", None) or getattr(service, "asset_address", None)
            if not token or token.lower() != USDC_BASE_SEPOLIA.lower():
                raise PlanValidationError(
                    f"Service '{c.service_id}' violates token policy: {token} != {USDC_BASE_SEPOLIA}"
                )

            pay_to = getattr(service, "pay_to", None) or getattr(service, "pay_to_address", None)
            if not pay_to or not pay_to.startswith("0x") or len(pay_to) != 42:
                raise PlanValidationError(
                    f"Service '{c.service_id}' has invalid pay_to address: {pay_to}"
                )

            if service.price_atomic <= 0:
                raise PlanValidationError(f"Invalid registry price for service '{c.service_id}'")

            # Check client price tampering
            if c.estimated_price_units != service.price_atomic:
                # Override to authoritative server-side price
                c.estimated_price_units = service.price_atomic

            # Validate input payload schema against authoritative registry input_schema
            if service.input_schema and isinstance(service.input_schema, dict):
                validator = Draft7Validator(service.input_schema)
                errors = list(validator.iter_errors(c.input_payload))
                if errors:
                    err_msg = "; ".join(e.message for e in errors)
                    raise PlanValidationError(
                        f"Input payload for step {c.step_id} ({c.service_id}) does not conform to registered input schema: {err_msg}"
                    )

            # Validate fallback services
            step_worst_case = service.price_atomic
            if c.fallback_service_ids:
                for fb_id in c.fallback_service_ids:
                    fb_service = self.registry.get_active_service(fb_id)
                    if not fb_service:
                        raise PlanValidationError(
                            f"Fallback service '{fb_id}' does not exist or is disabled in the authoritative registry."
                        )
                    if fb_service.price_atomic > step_worst_case:
                        step_worst_case = fb_service.price_atomic

            step_worst_case += c.fallback_allowance_units
            c.worst_case_price_units = step_worst_case

            calculated_expected_cost += service.price_atomic
            calculated_worst_case_cost += step_worst_case

        # Update authoritative cost totals
        plan.expected_cost_units = calculated_expected_cost
        plan.worst_case_cost_units = calculated_worst_case_cost
        plan.fallback_allowances_units = calculated_worst_case_cost - calculated_expected_cost

        # 4. Worst-case cost check including permitted fallbacks
        if calculated_expected_cost > plan.budget_units:
            raise PlanValidationError(
                f"Expected plan cost ({calculated_expected_cost} units) exceeds allocated budget ({plan.budget_units} units)."
            )

        if calculated_worst_case_cost > plan.budget_units:
            raise PlanValidationError(
                f"Worst-case plan cost ({calculated_worst_case_cost} units) exceeds allocated budget ({plan.budget_units} units)."
            )

        # 5. Concurrency validation & topological stage layering
        if plan.max_concurrency < 1 or plan.max_concurrency > concurrency_limit:
            raise PlanValidationError(
                f"Concurrency {plan.max_concurrency} outside allowed range [1, {concurrency_limit}]."
            )

        # Compute topological execution stages (Kahn-style level by level)
        # in_degrees: count of dependencies for each step
        in_degrees = {c.step_id: len(c.depends_on) for c in plan.calls}
        # forward adjacency: node -> list of nodes that depend on it
        children: Dict[int, List[int]] = {sid: [] for sid in step_ids}
        for c in plan.calls:
            for dep in c.depends_on:
                children[dep].append(c.step_id)

        stages: List[List[int]] = []
        current_layer = [sid for sid, deg in in_degrees.items() if deg == 0]

        remaining_nodes = len(step_ids)
        while current_layer:
            current_layer.sort()
            if len(current_layer) > plan.max_concurrency:
                raise PlanValidationError(
                    f"Execution stage contains {len(current_layer)} parallel steps, exceeding max concurrency limit {plan.max_concurrency}."
                )
            stages.append(current_layer)
            remaining_nodes -= len(current_layer)

            next_layer = []
            for node in current_layer:
                for child in children[node]:
                    in_degrees[child] -= 1
                    if in_degrees[child] == 0:
                        next_layer.append(child)
            current_layer = next_layer

        if remaining_nodes > 0:
            raise PlanValidationError("Cyclic dependency encountered during stage ordering.")

        plan.execution_stages = stages
        plan.dependency_graph = {c.step_id: list(c.depends_on) for c in plan.calls}
