"""[IMPLEMENTED FOUNDATION] Task Decomposition & Execution Planner."""
from dataclasses import dataclass
from typing import Any, Dict, List
from backend.shared.constants import ServiceCategory, usdc_to_base_units


@dataclass
class PlannedStep:
    step_number: int
    category: ServiceCategory
    service_id: str
    estimated_cost_usdc: str
    input_payload: Dict[str, Any]


@dataclass
class TaskPlan:
    task_prompt: str
    total_budget_usdc: str
    steps: List[PlannedStep]
    estimated_total_units: int


class TaskPlanner:
    """Decomposes high-level natural language tasks into actionable microservice steps."""

    def plan_task(self, prompt: str, budget_usdc: str) -> TaskPlan:
        """Analyze prompt keywords and map to required seller services."""
        prompt_lower = prompt.lower()
        steps: List[PlannedStep] = []
        step_counter = 1

        # Heuristic keyword mapping for hackathon tasks
        if any(w in prompt_lower for w in ["market", "price", "eth", "btc", "financial", "volume"]):
            steps.append(PlannedStep(
                step_number=step_counter,
                category=ServiceCategory.DATA,
                service_id="data_001",
                estimated_cost_usdc="0.002",
                input_payload={"symbol": "ETH"}
            ))
            step_counter += 1

        if any(w in prompt_lower for w in ["scrape", "web", "article", "url", "extract"]):
            steps.append(PlannedStep(
                step_number=step_counter,
                category=ServiceCategory.SCRAPING,
                service_id="scraping_001",
                estimated_cost_usdc="0.003",
                input_payload={"url": "https://ethereum.org"}
            ))
            step_counter += 1

        # Always include inference/summary if requested or as aggregation step
        if any(w in prompt_lower for w in ["summarize", "analyze", "infer", "synthesize", "takeaway"]) or not steps:
            steps.append(PlannedStep(
                step_number=step_counter,
                category=ServiceCategory.INFERENCE,
                service_id="inference_001",
                estimated_cost_usdc="0.004",
                input_payload={"prompt": prompt, "max_tokens": 150}
            ))
            step_counter += 1

        total_units = sum(usdc_to_base_units(s.estimated_cost_usdc) for s in steps)
        return TaskPlan(
            task_prompt=prompt,
            total_budget_usdc=budget_usdc,
            steps=steps,
            estimated_total_units=total_units
        )
