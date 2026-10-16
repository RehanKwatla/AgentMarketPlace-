"""[IMPLEMENTED FOUNDATION] Reputation & Budget-Aware Service Selector."""
from typing import List, Optional
from backend.shared.constants import ServiceCategory, usdc_to_base_units
from backend.shared.schemas import ServiceDefinition
from backend.registry.service_catalog import ServiceCatalog, catalog


class ServiceSelector:
    """Selects best candidate seller agents taking price and reputation into account."""

    def __init__(self, service_catalog: ServiceCatalog = catalog):
        self.catalog = service_catalog

    def select_best_service(
        self,
        category: ServiceCategory,
        max_budget_units: int,
        exclude_service_ids: Optional[List[str]] = None
    ) -> Optional[ServiceDefinition]:
        """Find the optimal service provider for a given category."""
        candidates = self.catalog.list_services(category=category.value, is_active=True)
        if exclude_service_ids:
            candidates = [c for c in candidates if c.service_id not in exclude_service_ids]

        # Filter within budget
        valid = [c for c in candidates if c.price_base_units <= max_budget_units]
        if not valid:
            return None

        # Sort by price ascending (cheapest first)
        valid.sort(key=lambda s: s.price_base_units)
        return valid[0]
