"""[IMPLEMENTED FOUNDATION] Service Catalog with Dynamic Filtering."""
from typing import Dict, List, Optional
from backend.shared.config import get_settings
from backend.shared.constants import (
    NETWORK_BASE_SEPOLIA,
    ServiceCategory,
    usdc_to_base_units,
)
from backend.shared.schemas import ServiceDefinition


class ServiceCatalog:
    """Manages available seller microservices and provides discovery/filtering."""

    def __init__(self):
        self._services: Dict[str, ServiceDefinition] = {}
        self._load_default_services()

    def _load_default_services(self) -> None:
        """Seed registry with the three primary seller services."""
        settings = get_settings()

        defaults = [
            ServiceDefinition(
                service_id="data_001",
                name="Alpha Financial Market Data",
                category=ServiceCategory.DATA,
                endpoint_url=settings.data_seller_endpoint,
                price_usdc="0.002",
                network=NETWORK_BASE_SEPOLIA,
                pay_to=settings.data_seller_pay_to,
                description="Provides real-time asset market prices and 24h trading statistics",
                input_schema={
                    "type": "object",
                    "required": ["symbol"],
                    "properties": {"symbol": {"type": "string", "example": "ETH"}}
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
                is_active=True
            ),
            ServiceDefinition(
                service_id="scraping_001",
                name="Web Markdown & Content Extractor",
                category=ServiceCategory.SCRAPING,
                endpoint_url=settings.scraping_seller_endpoint,
                price_usdc="0.003",
                network=NETWORK_BASE_SEPOLIA,
                pay_to=settings.scraping_seller_pay_to,
                description="Extracts clean markdown and textual content from target URLs",
                input_schema={
                    "type": "object",
                    "required": ["url"],
                    "properties": {"url": {"type": "string", "example": "https://example.com"}}
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
                is_active=True
            ),
            ServiceDefinition(
                service_id="inference_001",
                name="Agent Synthesis & Inference Engine",
                category=ServiceCategory.INFERENCE,
                endpoint_url=settings.inference_seller_endpoint,
                price_usdc="0.004",
                network=NETWORK_BASE_SEPOLIA,
                pay_to=settings.inference_seller_pay_to,
                description="Performs LLM summarization, reasoning, and data synthesis",
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
                is_active=True
            ),
        ]

        for s in defaults:
            self.register_service(s)

    def register_service(self, service: ServiceDefinition) -> None:
        self._services[service.service_id] = service

    def get_service(self, service_id: str) -> Optional[ServiceDefinition]:
        return self._services.get(service_id)

    def list_services(
        self,
        category: Optional[str] = None,
        max_price_usdc: Optional[str] = None,
        is_active: Optional[bool] = True
    ) -> List[ServiceDefinition]:
        results = list(self._services.values())

        if is_active is not None:
            results = [s for s in results if s.is_active == is_active]

        if category:
            results = [s for s in results if s.category.value == category or s.category == category]

        if max_price_usdc:
            max_units = usdc_to_base_units(max_price_usdc)
            results = [s for s in results if s.price_base_units <= max_units]

        return results


# Global singleton instance for app runtime
catalog = ServiceCatalog()
