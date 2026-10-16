"""Service Selector taking relevance, schema compatibility, price, latency, and reputation into account."""
from typing import List, Optional
from backend.shared.constants import ServiceCategory, usdc_to_base_units
from backend.registry.schemas import ServiceRecord
from backend.registry.service import RegistryService, registry_service


class ServiceSelector:
    """Selects optimal seller microservices based on multi-factor scoring and reputation."""

    def __init__(self, registry: RegistryService = registry_service):
        self.registry = registry

    def select_service_for_category(
        self,
        category: ServiceCategory,
        max_budget_units: int,
        exclude_service_ids: Optional[List[str]] = None,
        require_schema_fields: Optional[List[str]] = None,
    ) -> Optional[ServiceRecord]:
        """Select highest-reputation eligible service for category within budget."""
        response = self.registry.list_services(category=category.value, active=True, limit=50)
        candidates = response.items

        # Exclude already attempted or failed service IDs
        if exclude_service_ids:
            candidates = [c for c in candidates if c.service_id not in exclude_service_ids]

        # Filter strictly within budget
        affordable = [c for c in candidates if c.price_atomic <= max_budget_units]
        if not affordable:
            return None

        # Filter schema compatibility if required
        if require_schema_fields:
            compatible = []
            for c in affordable:
                input_props = c.input_schema.get("properties", {})
                if all(f in input_props for f in require_schema_fields):
                    compatible.append(c)
            if compatible:
                affordable = compatible

        # Score candidates: composite of reputation score, latency penalty, and price
        def candidate_score(s: ServiceRecord) -> float:
            rep = s.reputation
            success_rate = rep.success_rate if rep else 1.0
            latency = rep.median_latency_ms if rep else 300.0
            # Higher success rate is better, lower latency is better, lower price is better
            score = (success_rate * 100.0) - (latency / 100.0) - (s.price_atomic / 1000.0)
            return score

        affordable.sort(key=candidate_score, reverse=True)
        return affordable[0]

    def get_fallback_service(
        self,
        category: ServiceCategory,
        failed_service_id: str,
        remaining_budget_units: int,
    ) -> Optional[ServiceRecord]:
        """Find an alternative eligible service when primary provider fails."""
        return self.select_service_for_category(
            category=category,
            max_budget_units=remaining_budget_units,
            exclude_service_ids=[failed_service_id]
        )
