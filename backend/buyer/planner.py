import json
import re
from typing import Any, Dict, List, Optional
from backend.shared.constants import ServiceCategory, usdc_to_base_units
from backend.buyer.schemas import TaskCreationRequest
from backend.buyer.plan_validator import ExecutionPlan, PlannedCall, PlanValidator, PlanValidationError
from backend.buyer.selector import ServiceSelector
from backend.registry.schemas import ServiceRecord


class TaskPlanner:
    """Decomposes natural language task requests into structured, validated execution DAGs."""

    def __init__(
        self,
        selector: Optional[ServiceSelector] = None,
        validator: Optional[PlanValidator] = None,
    ):
        self.selector = selector or ServiceSelector()
        self.validator = validator or PlanValidator()

    def _validate_call_input_against_capabilities(
        self,
        service: ServiceRecord,
        payload: Dict[str, Any],
    ) -> None:
        """Validate task input against declared service capability constraints before paid execution."""
        if not service or not service.capability_metadata:
            return

        # 1. Validate payload size constraint
        payload_bytes = len(json.dumps(payload).encode("utf-8"))
        if service.capability_metadata.max_payload_bytes is not None:
            if payload_bytes > service.capability_metadata.max_payload_bytes:
                raise PlanValidationError(
                    f"Task input payload for '{service.service_id}' ({payload_bytes} bytes) exceeds "
                    f"declared max_payload_bytes ({service.capability_metadata.max_payload_bytes} bytes)."
                )

        constraints = service.capability_metadata.constraints or {}

        # 2. Scraping validations
        if "url" in payload:
            url = str(payload["url"]).strip()
            max_len = constraints.get("max_url_length", 2048)
            if len(url) > max_len:
                raise PlanValidationError(
                    f"Scraping input URL length ({len(url)}) exceeds service max_url_length ({max_len})."
                )

            allowed_schemes = constraints.get("allowed_schemes", ["http", "https"])
            scheme = url.split("://")[0].lower() if "://" in url else ""
            if scheme not in allowed_schemes:
                raise PlanValidationError(
                    f"Scraping input URL scheme '{scheme}' is not in allowed schemes: {allowed_schemes}."
                )

            blocked_hosts = constraints.get("blocked_hosts", ["localhost", "127.0.0.1", "0.0.0.0"])
            for blocked in blocked_hosts:
                if blocked in url.lower():
                    raise PlanValidationError(
                        f"Scraping input URL contains blocked host destination: '{blocked}'."
                    )

        # 3. Data validations
        if "symbol" in payload:
            symbol = str(payload["symbol"]).strip().upper()
            supported_symbols = constraints.get("supported_symbols")
            if supported_symbols and symbol not in [s.upper() for s in supported_symbols]:
                raise PlanValidationError(
                    f"Data input symbol '{symbol}' is not supported by '{service.service_id}'. "
                    f"Supported: {supported_symbols}."
                )

        # 4. Inference validations
        if "prompt" in payload:
            prompt = str(payload["prompt"])
            max_prompt_len = constraints.get("max_prompt_length", 4000)
            if len(prompt) > max_prompt_len:
                raise PlanValidationError(
                    f"Inference input prompt length ({len(prompt)}) exceeds declared service limit ({max_prompt_len})."
                )
            max_tokens = payload.get("max_tokens")
            max_tokens_limit = constraints.get("max_tokens_limit")
            if max_tokens and max_tokens_limit and max_tokens > max_tokens_limit:
                raise PlanValidationError(
                    f"Inference requested max_tokens ({max_tokens}) exceeds declared service limit ({max_tokens_limit})."
                )

    def create_plan(self, request: TaskCreationRequest) -> ExecutionPlan:
        """Generate a deterministic multi-step plan based on prompt intent and category constraints.

        Translates natural language into a structured execution DAG with explicit dependencies:
        - Scraping and Data steps run independently (in parallel).
        - Inference step depends on upstream Scraping and/or Data steps (sequential dependency).
        """
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
            # Heuristic intent mapping to capabilities
            if any(w in prompt_lower for w in ["scrape", "web", "fetch", "url", "extract", "article", "http", "site"]):
                need_scraping = True
            if any(w in prompt_lower for w in ["crypto", "price", "market", "data", "eth", "btc", "financial", "volume"]):
                need_data = True
            if any(w in prompt_lower for w in ["summarize", "analyze", "ai", "reasoning", "infer", "report", "synthesis", "takeaway"]) or not (need_scraping or need_data):
                need_inference = True

        calls: List[PlannedCall] = []
        reasons_for_selection: Dict[str, str] = {}
        step_id = 1

        # 1. Scraping Step (Parallel candidate in Stage 0)
        scraping_step_id: Optional[int] = None
        if need_scraping:
            primary_svc, fallbacks, reason = self.selector.select_service_with_fallbacks(
                category=ServiceCategory.SCRAPING,
                max_budget_units=budget_units,
                requested_capability="scraping.extract.v1",
                task_intent=request.task,
            )
            if not primary_svc:
                raise PlanValidationError(
                    f"Unable to select an eligible service for Scraping (budget: {budget_units} units). {reason}"
                )

            url_match = re.search(r"[a-zA-Z0-9+.-]+://[^\s]+", request.task or "")
            target_url = url_match.group(0) if url_match else "https://ethereum.org"
            scraping_step_id = step_id

            scraping_payload = {"url": target_url}
            self._validate_call_input_against_capabilities(primary_svc, scraping_payload)

            fb_ids = [f.service_id for f in fallbacks]
            max_svc_price = max([primary_svc.price_atomic] + [f.price_atomic for f in fallbacks])

            calls.append(PlannedCall(
                step_id=scraping_step_id,
                category=ServiceCategory.SCRAPING.value,
                capability="scraping.extract.v1",
                service_id=primary_svc.service_id,
                fallback_service_ids=fb_ids,
                input_payload=scraping_payload,
                estimated_price_units=primary_svc.price_atomic,
                worst_case_price_units=max_svc_price,
                depends_on=[],
                selection_reason=reason,
                allow_fallback=True,
            ))
            reasons_for_selection[primary_svc.service_id] = reason
            step_id += 1

        # 2. Data Step (Parallel candidate in Stage 0)
        data_step_id: Optional[int] = None
        if need_data:
            primary_svc, fallbacks, reason = self.selector.select_service_with_fallbacks(
                category=ServiceCategory.DATA,
                max_budget_units=budget_units,
                requested_capability="data.lookup.v1",
                task_intent=request.task,
            )
            if not primary_svc:
                raise PlanValidationError(
                    f"Unable to select an eligible service for Data (budget: {budget_units} units). {reason}"
                )

            symbol = "ETH"
            if "btc" in prompt_lower or "bitcoin" in prompt_lower:
                symbol = "BTC"
            elif "sol" in prompt_lower or "solana" in prompt_lower:
                symbol = "SOL"
            elif "usdc" in prompt_lower:
                symbol = "USDC"
            else:
                sym_match = re.search(r"\b(?:symbol|ticker|asset|data for|rate of|rate for|price of|price for|quote for|market of)\s+([a-zA-Z0-9_]{2,30})\b", prompt_lower)
                if sym_match:
                    symbol = sym_match.group(1).upper()

            data_step_id = step_id
            data_payload = {"symbol": symbol}
            self._validate_call_input_against_capabilities(primary_svc, data_payload)

            fb_ids = [f.service_id for f in fallbacks]
            max_svc_price = max([primary_svc.price_atomic] + [f.price_atomic for f in fallbacks])

            calls.append(PlannedCall(
                step_id=data_step_id,
                category=ServiceCategory.DATA.value,
                capability="data.lookup.v1",
                service_id=primary_svc.service_id,
                fallback_service_ids=fb_ids,
                input_payload=data_payload,
                estimated_price_units=primary_svc.price_atomic,
                worst_case_price_units=max_svc_price,
                depends_on=[],
                selection_reason=reason,
                allow_fallback=True,
            ))
            reasons_for_selection[primary_svc.service_id] = reason
            step_id += 1

        # 3. Inference Step (Stage 1: depends on Scraping and/or Data)
        if need_inference:
            primary_svc, fallbacks, reason = self.selector.select_service_with_fallbacks(
                category=ServiceCategory.INFERENCE,
                max_budget_units=budget_units,
                requested_capability="inference.summarize.v1",
                task_intent=request.task,
            )
            if not primary_svc:
                raise PlanValidationError(
                    f"Unable to select an eligible service for Inference (budget: {budget_units} units). {reason}"
                )

            deps = []
            if scraping_step_id:
                deps.append(scraping_step_id)
            if data_step_id:
                deps.append(data_step_id)

            inference_payload = {"prompt": request.task, "max_tokens": 200}
            self._validate_call_input_against_capabilities(primary_svc, inference_payload)

            fb_ids = [f.service_id for f in fallbacks]
            max_svc_price = max([primary_svc.price_atomic] + [f.price_atomic for f in fallbacks])

            calls.append(PlannedCall(
                step_id=step_id,
                category=ServiceCategory.INFERENCE.value,
                capability="inference.summarize.v1",
                service_id=primary_svc.service_id,
                fallback_service_ids=fb_ids,
                input_payload=inference_payload,
                estimated_price_units=primary_svc.price_atomic,
                worst_case_price_units=max_svc_price,
                depends_on=deps,
                selection_reason=reason,
                allow_fallback=True,
            ))
            reasons_for_selection[primary_svc.service_id] = reason
            step_id += 1

        expected_cost = sum(c.estimated_price_units for c in calls)
        worst_case_cost = sum(c.worst_case_price_units for c in calls)
        fallback_allowance = worst_case_cost - expected_cost

        plan_explanation = (
            f"Execution DAG created with {len(calls)} step(s). "
            f"Expected cost: {expected_cost} base units. "
            f"Worst-case cost: {worst_case_cost} base units (including fallbacks). "
            f"Allocated budget: {budget_units} base units."
        )

        plan = ExecutionPlan(
            task_prompt=request.task,
            budget_units=budget_units,
            calls=calls,
            worst_case_cost_units=worst_case_cost,
            expected_cost_units=expected_cost,
            fallback_allowances_units=fallback_allowance,
            max_concurrency=request.max_concurrency,
            reasons_for_selection=reasons_for_selection,
            explanation=plan_explanation,
        )

        # Validate deterministically before returning
        self.validator.validate_plan(plan, concurrency_limit=request.max_concurrency)
        return plan

    def plan_task(self, prompt: str, budget_usdc: str) -> Any:
        """Backwards compatibility alias for older test fixtures."""
        from backend.buyer.task_planner import TaskPlanner as LegacyPlanner
        return LegacyPlanner().plan_task(prompt, budget_usdc)
