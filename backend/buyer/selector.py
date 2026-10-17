"""Service Selector enforcing hard eligibility checks before ranking candidates by utility."""
from typing import Any, Dict, List, Optional, Tuple
from jsonschema import Draft7Validator
from backend.shared.constants import (
    NETWORK_BASE_SEPOLIA,
    USDC_BASE_SEPOLIA,
    ServiceCategory,
)
from backend.registry.schemas import ServiceRecord
from backend.registry.service import RegistryService, registry_service


class ServiceSelector:
    """Selects optimal active seller microservices using hard eligibility gates and multi-attribute utility."""

    def __init__(self, registry: RegistryService = registry_service):
        self.registry = registry

    def check_eligibility(
        self,
        service: ServiceRecord,
        requested_category: Optional[ServiceCategory] = None,
        requested_capability: Optional[str] = None,
        max_budget_units: Optional[int] = None,
        required_tags: Optional[List[str]] = None,
        max_latency_ms: Optional[int] = None,
        payload_bytes: Optional[int] = None,
        required_format: Optional[str] = None,
        execution_constraints: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Apply hard eligibility gates before ranking.

        A candidate must:
        1. Exist in the trusted registry and be enabled/active.
        2. Have valid metadata (name, endpoint, valid 42-char hex pay_to address, positive price).
        3. Match requested category and/or capability / tags.
        4. Satisfy declared execution constraints (SLA latency, payload limits, formats).
        5. Satisfy network (Base Sepolia) and token (USDC) policy constraints.
        6. Have valid input and output JSON schemas.
        7. Not exceed the available budget ceiling.
        """
        if not service:
            return False, "Service record is null"

        if not service.enabled or not service.is_active:
            return False, f"Service '{service.service_id}' is disabled or inactive"

        if not service.service_id or not service.name:
            return False, "Missing service identification metadata"

        constraints = service.capability_metadata.constraints if service.capability_metadata else {}
        if constraints.get("local_reference") is True:
            return False, (
                f"Service '{service.service_id}' is an informational local reference profile, "
                "not an independently executable seller endpoint"
            )

        if not service.endpoint_url or not (
            service.endpoint_url.startswith("http://") or service.endpoint_url.startswith("https://")
        ):
            return False, f"Invalid endpoint URL: {service.endpoint_url}"

        # Check pay_to address
        pay_to = getattr(service, "pay_to", None)
        pay_to_addr = getattr(service, "pay_to_address", None)
        for addr in [pay_to, pay_to_addr]:
            if addr is not None:
                if not str(addr).startswith("0x") or len(str(addr)) != 42:
                    return False, f"Invalid pay_to address: {addr}"
        if not pay_to and not pay_to_addr:
            return False, "Missing pay_to address"

        if service.price_atomic <= 0:
            return False, f"Invalid price atomic units: {service.price_atomic}"

        # Network and payment policy constraints
        if service.network != NETWORK_BASE_SEPOLIA:
            return False, f"Network mismatch: {service.network} != {NETWORK_BASE_SEPOLIA}"

        token = getattr(service, "token", None)
        asset_addr = getattr(service, "asset_address", None)
        for t in [token, asset_addr]:
            if t is not None:
                if str(t).lower() != USDC_BASE_SEPOLIA.lower():
                    return False, f"Token mismatch: {t} != {USDC_BASE_SEPOLIA}"
        if not token and not asset_addr:
            return False, "Missing token address"

        # Category compatibility
        if requested_category:
            cat_val = requested_category.value if isinstance(requested_category, ServiceCategory) else str(requested_category)
            if service.category.lower() != cat_val.lower():
                return False, f"Category mismatch: {service.category} != {cat_val}"

        # Capability compatibility
        if requested_capability:
            service_caps = set(service.capabilities or [])
            if service.capability:
                service_caps.add(service.capability)
            if service.capability_metadata and service.capability_metadata.tags:
                service_caps.update(service.capability_metadata.tags)
            matched_cap = (
                requested_capability in service_caps
                or any(requested_capability in c for c in service_caps)
            )
            if not matched_cap:
                return False, f"Capability mismatch: requested '{requested_capability}'"

        # Required tags matching
        if required_tags:
            service_tags = set(service.capabilities or [])
            if service.capability:
                service_tags.add(service.capability)
            if service.capability_metadata and service.capability_metadata.tags:
                service_tags.update(service.capability_metadata.tags)
            missing = [t for t in required_tags if t not in service_tags]
            if missing:
                return False, f"Missing required capability tag(s): {', '.join(missing)}"

        # Latency SLA constraint
        if max_latency_ms is not None:
            if service.capability_metadata and service.capability_metadata.sla_latency_p95_ms is not None:
                if service.capability_metadata.sla_latency_p95_ms > max_latency_ms:
                    return False, f"Service SLA latency ({service.capability_metadata.sla_latency_p95_ms}ms) exceeds requested max ({max_latency_ms}ms)"

        # Payload size constraint
        if payload_bytes is not None:
            if service.capability_metadata and service.capability_metadata.max_payload_bytes is not None:
                if payload_bytes > service.capability_metadata.max_payload_bytes:
                    return False, f"Payload size ({payload_bytes} bytes) exceeds service max_payload_bytes ({service.capability_metadata.max_payload_bytes} bytes)"

        # Supported format constraint
        if required_format is not None:
            if service.capability_metadata and service.capability_metadata.supported_formats:
                if required_format not in service.capability_metadata.supported_formats:
                    return False, f"Format '{required_format}' not in supported formats: {service.capability_metadata.supported_formats}"

        # Declared custom execution constraints
        if execution_constraints and service.capability_metadata and service.capability_metadata.constraints:
            for k, v in execution_constraints.items():
                if k in service.capability_metadata.constraints:
                    declared_val = service.capability_metadata.constraints[k]
                    if isinstance(declared_val, list) and v not in declared_val:
                        return False, f"Execution constraint failed for '{k}': '{v}' not in declared {declared_val}"

        # Schema validity checks
        if service.input_schema and isinstance(service.input_schema, dict):
            try:
                Draft7Validator.check_schema(service.input_schema)
            except Exception as e:
                return False, f"Invalid input schema: {e}"

        if service.output_schema and isinstance(service.output_schema, dict):
            try:
                Draft7Validator.check_schema(service.output_schema)
            except Exception as e:
                return False, f"Invalid output schema: {e}"

        # Budget constraint
        if max_budget_units is not None and service.price_atomic > max_budget_units:
            return False, f"Price ({service.price_atomic} units) exceeds budget ({max_budget_units} units)"

        return True, None

    def rank_candidates(
        self,
        eligible_candidates: List[ServiceRecord],
        task_intent: Optional[str] = None,
    ) -> List[Tuple[ServiceRecord, float, str]]:
        """Rank eligible candidates using multi-attribute utility: relevance, price, reputation, and latency.

        Hard eligibility MUST already be verified. A high ranking never overrides an eligibility failure.
        """
        # Apply the same deterministic, ledger-backed ranking shown by the
        # registry recommendation API after this selector's hard gates pass.
        if eligible_candidates:
            try:
                from backend.registry.recommendation import RecommendationEngine, RecommendationRequest
                recommendation = RecommendationEngine(registry=self.registry).evaluate_and_rank(
                    RecommendationRequest(
                        task_prompt=task_intent or "",
                        category=eligible_candidates[0].category,
                    )
                )
                positions = {item["service_id"]: item for item in recommendation["recommendations"]}
                ranked_by_recommendation = []
                for service in eligible_candidates:
                    item = positions.get(service.service_id)
                    if item is None:
                        continue
                    factor_scores = item["factor_scores"]
                    reason = (
                        f"Selected {service.service_id} by registry recommendation "
                        f"(score={item['weighted_score']:.3f}; capability={factor_scores['capability_match']:.2f}, "
                        f"observed output validity={factor_scores['output_validity']:.2f}, "
                        f"observed reliability={factor_scores['reliability']:.2f}, "
                        f"price={service.price_atomic} base units)."
                    )
                    ranked_by_recommendation.append((service, item["weighted_score"] * 100.0, reason))
                if ranked_by_recommendation:
                    ranked_by_recommendation.sort(key=lambda row: (-row[1], row[0].price_atomic, row[0].service_id))
                    return ranked_by_recommendation
            except Exception:
                # Preserve existing selector behavior if telemetry is unavailable;
                # hard eligibility checks have already completed above.
                pass

        ranked = []
        for s in eligible_candidates:
            # 1. Relevance: base 1.0, boosted if intent matches description, name, or capability tags
            relevance = 1.0
            if task_intent:
                words = [w.lower() for w in task_intent.split() if len(w) > 3]
                searchable_text = f"{s.name} {s.description}".lower()
                if s.capability_metadata and s.capability_metadata.tags:
                    searchable_text += " " + " ".join(s.capability_metadata.tags).lower()
                matches = sum(1 for w in words if w in searchable_text)
                relevance += min(0.5, matches * 0.1)

            # 2. Listed service price (lower price -> higher utility)
            price_score = 10000.0 / (s.price_atomic + 1)

            # 3. Reputation (0 - 100 scale, default neutral 50.0)
            rep_score = s.reputation.reputation_score if s.reputation else 50.0

            # 4. Latency (lower latency -> higher utility, default 500ms)
            lat = s.reputation.median_latency_ms if (s.reputation and s.reputation.median_latency_ms > 0) else 500.0
            if s.capability_metadata and s.capability_metadata.sla_latency_p95_ms:
                lat = min(lat, float(s.capability_metadata.sla_latency_p95_ms))
            latency_score = 1000.0 / (lat + 1)

            # Composite utility weighting:
            # - Relevance: 30%
            # - Reputation: 35%
            # - Price: 25%
            # - Latency: 10%
            utility = (relevance * 30.0) + (rep_score * 0.35) + (price_score * 0.25) + (latency_score * 0.10)

            reason = (
                f"Selected {s.service_id} (utility={utility:.2f}): "
                f"Price={s.price_atomic} base units, "
                f"Reputation={rep_score:.1f}/100, "
                f"Latency={lat:.0f}ms, "
                f"Relevance={relevance:.2f}"
            )
            ranked.append((s, utility, reason))

        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked

    def select_service_for_category(
        self,
        category: ServiceCategory,
        max_budget_units: int,
        exclude_service_ids: Optional[List[str]] = None,
        requested_capability: Optional[str] = None,
        task_intent: Optional[str] = None,
        required_tags: Optional[List[str]] = None,
        max_latency_ms: Optional[int] = None,
        payload_bytes: Optional[int] = None,
        required_format: Optional[str] = None,
        execution_constraints: Optional[Dict[str, Any]] = None,
    ) -> Optional[ServiceRecord]:
        """Select the highest scoring eligible candidate within budget."""
        primary, _, _ = self.select_service_with_fallbacks(
            category=category,
            max_budget_units=max_budget_units,
            exclude_service_ids=exclude_service_ids,
            requested_capability=requested_capability,
            task_intent=task_intent,
            required_tags=required_tags,
            max_latency_ms=max_latency_ms,
            payload_bytes=payload_bytes,
            required_format=required_format,
            execution_constraints=execution_constraints,
        )
        return primary

    def select_service_with_fallbacks(
        self,
        category: ServiceCategory,
        max_budget_units: int,
        exclude_service_ids: Optional[List[str]] = None,
        requested_capability: Optional[str] = None,
        task_intent: Optional[str] = None,
        required_tags: Optional[List[str]] = None,
        max_latency_ms: Optional[int] = None,
        payload_bytes: Optional[int] = None,
        required_format: Optional[str] = None,
        execution_constraints: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[ServiceRecord], List[ServiceRecord], str]:
        """Select primary candidate and fallback options that pass hard eligibility checks."""
        exclude = set(exclude_service_ids or [])
        res = self.registry.list_services(
            category=category.value if isinstance(category, ServiceCategory) else str(category),
            active=True,
        )

        eligible: List[ServiceRecord] = []
        for candidate in res.items:
            if candidate.service_id in exclude:
                continue

            is_ok, reason = self.check_eligibility(
                service=candidate,
                requested_category=category,
                requested_capability=requested_capability,
                max_budget_units=max_budget_units,
                required_tags=required_tags,
                max_latency_ms=max_latency_ms,
                payload_bytes=payload_bytes,
                required_format=required_format,
                execution_constraints=execution_constraints,
            )
            if is_ok:
                eligible.append(candidate)

        if not eligible:
            return None, [], f"No eligible services found for category '{category}' within budget {max_budget_units} units."

        ranked = self.rank_candidates(eligible, task_intent=task_intent)
        primary_record, _, primary_reason = ranked[0]
        fallbacks = [r[0] for r in ranked[1:]]

        return primary_record, fallbacks, primary_reason

    def select_best_service(
        self,
        category: ServiceCategory,
        max_budget_units: int,
        exclude_service_ids: Optional[List[str]] = None,
    ) -> Optional[ServiceRecord]:
        """Backwards compatibility alias for older test fixtures."""
        return self.select_service_for_category(category, max_budget_units, exclude_service_ids)
