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
    ) -> Tuple[bool, Optional[str]]:
        """Apply hard eligibility gates before ranking.

        A candidate must:
        1. Exist in the trusted registry and be enabled/active.
        2. Have valid metadata (name, endpoint, valid 42-char hex pay_to address, positive price).
        3. Match requested category and/or capability.
        4. Satisfy network (Base Sepolia) and token (USDC) policy constraints.
        5. Have valid input and output JSON schemas.
        6. Not exceed the available budget ceiling.
        """
        if not service:
            return False, "Service record is null"

        if not service.enabled or not service.is_active:
            return False, f"Service '{service.service_id}' is disabled or inactive"

        if not service.service_id or not service.name:
            return False, "Missing service identification metadata"

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
            matched_cap = (
                service.capability == requested_capability
                or requested_capability in (service.capabilities or [])
            )
            if not matched_cap:
                return False, f"Capability mismatch: requested '{requested_capability}'"

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
        ranked = []
        for s in eligible_candidates:
            # 1. Relevance: base 1.0, boosted if intent matches description or name
            relevance = 1.0
            if task_intent and s.description:
                words = [w.lower() for w in task_intent.split() if len(w) > 3]
                matches = sum(1 for w in words if w in s.description.lower() or w in s.name.lower())
                relevance += min(0.5, matches * 0.1)

            # 2. Listed service price (lower price -> higher utility)
            price_score = 10000.0 / (s.price_atomic + 1)

            # 3. Reputation (0 - 100 scale, default neutral 50.0)
            rep_score = s.reputation.reputation_score if s.reputation else 50.0

            # 4. Latency (lower latency -> higher utility, default 500ms)
            lat = s.reputation.median_latency_ms if (s.reputation and s.reputation.median_latency_ms > 0) else 500.0
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
    ) -> Optional[ServiceRecord]:
        """Select the highest scoring eligible candidate within budget."""
        primary, _, _ = self.select_service_with_fallbacks(
            category=category,
            max_budget_units=max_budget_units,
            exclude_service_ids=exclude_service_ids,
            requested_capability=requested_capability,
            task_intent=task_intent,
        )
        return primary

    def select_service_with_fallbacks(
        self,
        category: ServiceCategory,
        max_budget_units: int,
        exclude_service_ids: Optional[List[str]] = None,
        requested_capability: Optional[str] = None,
        task_intent: Optional[str] = None,
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
