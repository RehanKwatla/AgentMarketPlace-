"""Registry Service layer managing service discovery, filtering, and seeding."""
import logging
from typing import Dict, List, Optional
from backend.shared.config import get_settings
from backend.shared.constants import (
    NETWORK_BASE_SEPOLIA,
    USDC_BASE_SEPOLIA,
    ServiceCategory,
    usdc_to_base_units,
)
from backend.registry.schemas import (
    ServiceRecord,
    ServiceReputationSummary,
    ServiceListResponse,
)
from backend.registry.validation import validate_service_registration

logger = logging.getLogger(__name__)


class RegistryService:
    """Manages discoverable microservice records with multi-criteria filtering."""

    def __init__(self):
        self._services: Dict[str, ServiceRecord] = {}
        self._aliases: Dict[str, str] = {}  # E.g. "data_001" -> "data-001"
        self._seed_default_services()

    def _normalize_id(self, service_id: str) -> str:
        """Normalize dashes and underscores for robust lookup."""
        return service_id.strip().lower()

    def _seed_default_services(self) -> None:
        """Seed registry with the three mandatory canonical sellers."""
        settings = get_settings()

        canonical_sellers = [
            ServiceRecord(
                service_id="data_001",
                name="Structured Financial & Market Data Seller",
                category=ServiceCategory.DATA,
                description="Returns real-time and historical asset market prices, 24h trading statistics, and financial metrics.",
                endpoint_url=settings.data_seller_endpoint,
                price_usdc="0.002",
                price_atomic=2000,
                network=NETWORK_BASE_SEPOLIA,
                asset_address=USDC_BASE_SEPOLIA,
                pay_to=settings.data_seller_pay_to,
                input_schema={
                    "type": "object",
                    "required": ["symbol"],
                    "properties": {
                        "symbol": {"type": "string", "description": "Asset ticker symbol, e.g. ETH, BTC"}
                    }
                },
                output_schema={
                    "type": "object",
                    "required": ["symbol", "price", "volume_24h", "timestamp"],
                    "properties": {
                        "symbol": {"type": "string"},
                        "price": {"type": "number"},
                        "volume_24h": {"type": "number"},
                        "timestamp": {"type": "string"}
                    }
                },
                enabled=True,
                is_active=True,
                registry_version="1.0.0",
                reputation=ServiceReputationSummary(
                    success_rate=0.98,
                    median_latency_ms=210.0,
                    total_calls=48,
                    successful_calls=47,
                    paid_output_rejected_calls=1,
                    listed_price_usdc="0.002000",
                    last_call_at="2026-10-16T12:00:00Z"
                )
            ),
            ServiceRecord(
                service_id="scraping_001",
                name="Web Extraction & Markdown Scraping Seller",
                category=ServiceCategory.SCRAPING,
                description="Fetches public web targets, strips boilerplate, and returns clean structured text or markdown.",
                endpoint_url=settings.scraping_seller_endpoint,
                price_usdc="0.003",
                price_atomic=3000,
                network=NETWORK_BASE_SEPOLIA,
                asset_address=USDC_BASE_SEPOLIA,
                pay_to=settings.scraping_seller_pay_to,
                input_schema={
                    "type": "object",
                    "required": ["url"],
                    "properties": {
                        "url": {"type": "string", "description": "Target webpage URL"}
                    }
                },
                output_schema={
                    "type": "object",
                    "required": ["url", "title", "content", "word_count"],
                    "properties": {
                        "url": {"type": "string"},
                        "title": {"type": "string"},
                        "content": {"type": "string"},
                        "word_count": {"type": "integer"}
                    }
                },
                enabled=True,
                is_active=True,
                registry_version="1.0.0",
                reputation=ServiceReputationSummary(
                    success_rate=0.96,
                    median_latency_ms=450.0,
                    total_calls=32,
                    successful_calls=31,
                    paid_output_rejected_calls=1,
                    listed_price_usdc="0.003",
                    last_call_at="2026-10-16T12:05:00Z"
                )
            ),
            ServiceRecord(
                service_id="inference_001",
                name="LLM Synthesis & Reasoning Inference Seller",
                category=ServiceCategory.INFERENCE,
                description="Performs analytical reasoning, summarization, and data synthesis from structured/unstructured inputs.",
                endpoint_url=settings.inference_seller_endpoint,
                price_usdc="0.004",
                price_atomic=4000,
                network=NETWORK_BASE_SEPOLIA,
                asset_address=USDC_BASE_SEPOLIA,
                pay_to=settings.inference_seller_pay_to,
                input_schema={
                    "type": "object",
                    "required": ["prompt"],
                    "properties": {
                        "prompt": {"type": "string"},
                        "max_tokens": {"type": "integer", "default": 200}
                    }
                },
                output_schema={
                    "type": "object",
                    "required": ["response", "model_used", "tokens_generated"],
                    "properties": {
                        "response": {"type": "string"},
                        "model_used": {"type": "string"},
                        "tokens_generated": {"type": "integer"}
                    }
                },
                enabled=True,
                is_active=True,
                registry_version="1.0.0",
                reputation=ServiceReputationSummary(
                    success_rate=0.99,
                    median_latency_ms=620.0,
                    total_calls=64,
                    successful_calls=63,
                    paid_output_rejected_calls=0,
                    listed_price_usdc="0.004000",
                    last_call_at="2026-10-16T12:10:00Z"
                )
            )
        ]

        for s in canonical_sellers:
            self.register_service(s)

    def register_service(self, service: ServiceRecord) -> None:
        """Register or update a service record with schema validation."""
        validate_service_registration(service.model_dump())
        primary_id = service.service_id
        self._services[primary_id] = service

        # Register aliases (e.g. data_001 -> data-001 and vice-versa)
        alt_id_1 = primary_id.replace("-", "_")
        alt_id_2 = primary_id.replace("_", "-")
        self._aliases[self._normalize_id(primary_id)] = primary_id
        self._aliases[self._normalize_id(alt_id_1)] = primary_id
        self._aliases[self._normalize_id(alt_id_2)] = primary_id

    def get_service(self, service_id: str) -> Optional[ServiceRecord]:
        """Lookup service with alias resolution (supporting data_001 and data-001)."""
        normalized = self._normalize_id(service_id)
        resolved_id = self._aliases.get(normalized, service_id)
        service = self._services.get(resolved_id)
        if service and service.service_id != service_id:
            copy_svc = service.model_copy()
            copy_svc.service_id = service_id
            return copy_svc
        return service

    def get_reputation(self, service_id: str) -> Optional[ServiceReputationSummary]:
        service = self.get_service(service_id)
        if not service:
            return None
        rep = service.reputation or ServiceReputationSummary(listed_price_usdc=service.price_usdc)
        rep.service_id = service.service_id
        return rep

    def list_services(
        self,
        category: Optional[str] = None,
        max_price_usdc: Optional[str] = None,
        min_price_usdc: Optional[str] = None,
        active: Optional[bool] = None,
        q: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> ServiceListResponse:
        """Search and filter services according to API contract specification."""
        results = list(self._services.values())

        # 1. Filter by enabled / active
        if active is not None:
            results = [s for s in results if (s.enabled == active and s.is_active == active)]

        # 2. Filter by category
        if category:
            cat_clean = category.strip().lower()
            results = [
                s for s in results
                if s.category.value.lower() == cat_clean or s.category == cat_clean
            ]

        # 3. Filter by max price
        if max_price_usdc:
            max_units = usdc_to_base_units(max_price_usdc)
            results = [s for s in results if s.price_atomic <= max_units]

        # 4. Filter by min price
        if min_price_usdc:
            min_units = usdc_to_base_units(min_price_usdc)
            results = [s for s in results if s.price_atomic >= min_units]

        # 5. Text / capability search (q)
        if q:
            query = q.strip().lower()
            results = [
                s for s in results
                if query in s.name.lower()
                or query in s.description.lower()
                or query in s.service_id.lower()
                or query in s.category.value.lower()
            ]

        total = len(results)
        paginated = results[offset : offset + limit]

        return ServiceListResponse(
            items=paginated,
            limit=limit,
            offset=offset,
            total=total
        )


# Global singleton instance for runtime
registry_service = RegistryService()
