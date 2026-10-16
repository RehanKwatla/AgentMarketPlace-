"""Service Selector ranking candidates by reputation, latency, and price."""
from typing import List, Optional
from backend.shared.constants import ServiceCategory
from backend.registry.schemas import ServiceRecord
from backend.registry.service import RegistryService, registry_service


class ServiceSelector:
    """Selects optimal active seller microservices using multi-attribute utility."""

    def __init__(self, registry: RegistryService = registry_service):
        self.registry = registry

    def select_service_for_category(
        self,
        category: ServiceCategory,
        max_budget_units: int,
        exclude_service_ids: Optional[List[str]] = None
    ) -> Optional[ServiceRecord]:
        """Select highest scoring active candidate within budget."""
        exclude = set(exclude_service_ids or [])
        res = self.registry.list_services(category=category.value, active=True)
        candidates = [s for s in res.items if s.service_id not in exclude and s.enabled and s.is_active]

        # Filter strictly within budget
        affordable = [s for s in candidates if s.price_atomic <= max_budget_units]
        if not affordable:
            return None

        # Score candidates: composite utility (Reputation 50%, Price 30%, Latency 20%)
        def score(s: ServiceRecord) -> float:
            rep_score = s.reputation.reputation_score if s.reputation else 50.0
            price_score = 10000.0 / (s.price_atomic + 1)
            lat = s.reputation.median_latency_ms if s.reputation else 500.0
            latency_score = 1000.0 / (lat + 1)
            return (rep_score * 0.5) + (price_score * 0.3) + (latency_score * 0.2)

        affordable.sort(key=score, reverse=True)
        return affordable[0]

    def select_best_service(
        self,
        category: ServiceCategory,
        max_budget_units: int,
        exclude_service_ids: Optional[List[str]] = None
    ) -> Optional[ServiceRecord]:
        """Backwards compatibility alias for older test fixtures."""
        return self.select_service_for_category(category, max_budget_units, exclude_service_ids)
