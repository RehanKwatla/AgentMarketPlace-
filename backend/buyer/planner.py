"""Deterministic-first Planner creating validated dependency DAGs for tasks."""
import re
from typing import List, Optional
from backend.shared.constants import ServiceCategory, usdc_to_base_units
from backend.buyer.schemas import TaskCreationRequest
from backend.buyer.selector import ServiceSelector
from backend.buyer.plan_validator import PlannedCall, ExecutionPlan, PlanValidator


class TaskPlanner:
    """Decomposes natural language goals into deterministic execution plans."""

    def __init__(
        self,
        selector: ServiceSelector = None,
        validator: PlanValidator = None
    ):
        self.selector = selector or ServiceSelector()
        self.validator = validator or PlanValidator()

    def create_plan(self, request: TaskCreationRequest) -> ExecutionPlan:
        """Construct a validated multi-service execution plan."""
        budget_units = usdc_to_base_units(request.budget_usdc)
        prompt_lower = request.task.lower()
        calls: List[PlannedCall] = []
        step_id = 1

        need_data = bool(
            request.require_all_categories
            or (request.preferred_categories and ServiceCategory.DATA in request.preferred_categories)
            or any(k in prompt_lower for k in ["market", "price", "eth", "btc", "financial", "crypto", "data", "symbol"])
        )

        need_scraping = bool(
            request.require_all_categories
            or (request.preferred_categories and ServiceCategory.SCRAPING in request.preferred_categories)
            or any(k in prompt_lower for k in ["scrape", "web", "article", "page", "url", "extract", "content", "news"])
        )

        need_inference = bool(
            request.require_all_categories
            or (request.preferred_categories and ServiceCategory.INFERENCE in request.preferred_categories)
            or any(k in prompt_lower for k in ["summarize", "analyze", "infer", "findings", "takeaways", "overview"])
            or not (need_data or need_scraping)  # Fallback to inference if generic
        )

        # 1. Scraping Step
        scraping_step_id: Optional[int] = None
        if need_scraping:
            service = self.selector.select_service_for_category(
                category=ServiceCategory.SCRAPING,
                max_budget_units=budget_units
            )
            if service:
                # Extract URL if present, otherwise default to relevant public page
                url_match = re.search(r"https?://[^\s]+", request.task)
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

        # 2. Data Step (Can run concurrently with Scraping)
        data_step_id: Optional[int] = None
        if need_data:
            service = self.selector.select_service_for_category(
                category=ServiceCategory.DATA,
                max_budget_units=budget_units
            )
            if service:
                # Extract symbol if mentioned
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

        # 3. Inference / Summarization Step (Depends on upstream data & scraping)
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

        # Validate plan deterministically
        self.validator.validate_plan(plan, concurrency_limit=request.max_concurrency)
        return plan
