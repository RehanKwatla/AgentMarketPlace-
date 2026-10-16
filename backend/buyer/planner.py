"""Deterministic-First Task Planner creating validated execution DAGs."""
import re
from typing import List, Optional
from backend.shared.constants import ServiceCategory, usdc_to_base_units
from backend.buyer.schemas import TaskCreationRequest
from backend.buyer.plan_validator import ExecutionPlan, PlannedCall, PlanValidator
from backend.buyer.selector import ServiceSelector


class TaskPlanner:
    """Decomposes natural language task requests into structured, validated execution DAGs."""

    def __init__(
        self,
        selector: Optional[ServiceSelector] = None,
        validator: Optional[PlanValidator] = None
    ):
        self.selector = selector or ServiceSelector()
        self.validator = validator or PlanValidator()

    def create_plan(self, request: TaskCreationRequest) -> ExecutionPlan:
        """Generate a deterministic multi-step plan based on prompt intent and category constraints."""
        budget_units = usdc_to_base_units(request.budget_usdc)
        prompt_lower = (request.task or "").lower()

        need_scraping = False
        need_data = False
        need_inference = True

        # Check explicit preferred categories
        if request.preferred_categories:
            need_scraping = ServiceCategory.SCRAPING in request.preferred_categories
            need_data = ServiceCategory.DATA in request.preferred_categories
            need_inference = ServiceCategory.INFERENCE in request.preferred_categories
        else:
            # Heuristic intent mapping
            if any(w in prompt_lower for w in ["scrape", "web", "fetch", "url", "extract", "article", "http"]):
                need_scraping = True
            if any(w in prompt_lower for w in ["crypto", "price", "market", "data", "eth", "btc", "financial"]):
                need_data = True
            if any(w in prompt_lower for w in ["summarize", "analyze", "ai", "reasoning", "infer", "report"]) or not (need_scraping or need_data):
                need_inference = True

        calls: List[PlannedCall] = []
        step_id = 1

        # 1. Scraping Step
        scraping_step_id: Optional[int] = None
        if need_scraping:
            service = self.selector.select_service_for_category(
                category=ServiceCategory.SCRAPING,
                max_budget_units=budget_units
            )
            if service:
                url_match = re.search(r"https?://[^\s]+", request.task or "")
                target_url = url_match.group(0) if url_match else "https://ethereum.org"
                scraping_step_id = step_id
                calls.append(PlannedCall(
                    step_id=scraping_step_id,
                    category=ServiceCategory.SCRAPING.value,
                    service_id=service.service_id,
                    input_payload={"url": target_url},
                    estimated_price_units=service.price_atomic,
                    depends_on=[]
                ))
                step_id += 1

        # 2. Data Step (Can execute concurrently with Scraping)
        data_step_id: Optional[int] = None
        if need_data:
            service = self.selector.select_service_for_category(
                category=ServiceCategory.DATA,
                max_budget_units=budget_units
            )
            if service:
                symbol = "ETH"
                if "btc" in prompt_lower or "bitcoin" in prompt_lower:
                    symbol = "BTC"
                data_step_id = step_id
                calls.append(PlannedCall(
                    step_id=data_step_id,
                    category=ServiceCategory.DATA.value,
                    service_id=service.service_id,
                    input_payload={"symbol": symbol},
                    estimated_price_units=service.price_atomic,
                    depends_on=[]
                ))
                step_id += 1

        # 3. Inference Step (Depends on upstream context from Scraping and/or Data)
        if need_inference:
            service = self.selector.select_service_for_category(
                category=ServiceCategory.INFERENCE,
                max_budget_units=budget_units
            )
            if service:
                deps = []
                if scraping_step_id:
                    deps.append(scraping_step_id)
                if data_step_id:
                    deps.append(data_step_id)

                calls.append(PlannedCall(
                    step_id=step_id,
                    category=ServiceCategory.INFERENCE.value,
                    service_id=service.service_id,
                    input_payload={"prompt": request.task, "max_tokens": 200},
                    estimated_price_units=service.price_atomic,
                    depends_on=deps
                ))
                step_id += 1

        worst_case_cost = sum(c.estimated_price_units for c in calls)

        plan = ExecutionPlan(
            task_prompt=request.task,
            budget_units=budget_units,
            calls=calls,
            worst_case_cost_units=worst_case_cost,
            max_concurrency=request.max_concurrency
        )

        # Validate deterministically before returning
        self.validator.validate_plan(plan, concurrency_limit=request.max_concurrency)
        return plan
