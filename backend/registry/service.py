"""Service Registry Business Logic and Catalog Management."""
import re
from typing import Dict, List, Optional
from backend.shared.config import get_settings
from backend.shared.constants import (
    NETWORK_BASE_SEPOLIA,
    USDC_BASE_SEPOLIA,
    ServiceCategory,
    usdc_to_base_units,
)
from backend.shared.schemas import CapabilityMetadata
from backend.registry.schemas import (
    ServiceRecord,
    ServiceListResponse,
    ServiceReputationSummary,
)
from backend.registry.validation import validate_service_registration


class RegistryService:
    """In-memory service registry with persistence interfaces and Member 4 reputation link."""

    def __init__(self):
        self._services: Dict[str, ServiceRecord] = {}
        self._aliases: Dict[str, str] = {}
        self._load_seed_services()

    @staticmethod
    def _normalize_id(service_id: str) -> str:
        return service_id.strip().lower().replace("-", "_")

    def _load_seed_services(self) -> None:
        """Seed the registry with the three canonical seller services labeled as demo/seed data."""
        settings = get_settings()

        seed_sellers = [
            ServiceRecord(
                service_id="data_001",
                name="Alpha Financial Market Data [DEMO SEED]",
                category=ServiceCategory.DATA,
                capabilities=["data.lookup.v1", "crypto.market.rates"],
                description="[DEMO SEED] Provides real-time cryptocurrency and asset prices with 24h market volume statistics.",
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
                        "symbol": {"type": "string", "example": "ETH", "description": "Asset ticker symbol"}
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
                is_demo_seed=True,
                registry_version="1.0.0",
                capability_metadata=CapabilityMetadata(
                    version="1.0.0",
                    tags=["crypto", "market-data", "rates", "financial", "spot-prices"],
                    supported_formats=["application/json"],
                    max_payload_bytes=1024,
                    rate_limit_per_minute=60,
                    sla_latency_p95_ms=180,
                    deterministic=True,
                    constraints={
                        "supported_symbols": ["ETH", "BTC", "SOL", "USDC"],
                        "max_symbol_length": 10,
                    },
                ),
                reputation=ServiceReputationSummary(
                    service_id="data_001",
                    reputation_score=98.5,
                    success_rate=0.99,
                    median_latency_ms=120.0,
                    latency_p95_ms=180.0,
                    total_calls=120,
                    successful_calls=119,
                    paid_output_rejected_calls=1,
                    listed_price_usdc="0.002",
                    last_call_at="2026-10-16T12:00:00Z"
                )
            ),
            ServiceRecord(
                service_id="scraping_001",
                name="Web Markdown & Content Extractor [DEMO SEED]",
                category=ServiceCategory.SCRAPING,
                capabilities=["scraping.extract.v1", "web.markdown.fetch"],
                description="[DEMO SEED] Fetches remote URLs and extracts clean semantic markdown text with structural metadata.",
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
                        "url": {"type": "string", "format": "uri", "example": "https://ethereum.org"}
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
                is_demo_seed=True,
                registry_version="1.0.0",
                capability_metadata=CapabilityMetadata(
                    version="1.0.0",
                    tags=["web", "scraping", "markdown", "extraction", "content"],
                    supported_formats=["text/html", "application/json"],
                    max_payload_bytes=4096,
                    rate_limit_per_minute=30,
                    sla_latency_p95_ms=680,
                    deterministic=False,
                    constraints={
                        "allowed_schemes": ["http", "https"],
                        "max_url_length": 2048,
                        "blocked_hosts": ["localhost", "127.0.0.1", "0.0.0.0"],
                    },
                ),
                reputation=ServiceReputationSummary(
                    service_id="scraping_001",
                    reputation_score=96.0,
                    success_rate=0.96,
                    median_latency_ms=450.0,
                    latency_p95_ms=680.0,
                    total_calls=45,
                    successful_calls=43,
                    paid_output_rejected_calls=2,
                    listed_price_usdc="0.003",
                    last_call_at="2026-10-16T12:05:00Z"
                )
            ),
            ServiceRecord(
                service_id="inference_001",
                name="LLM Synthesis & Reasoning Engine [DEMO SEED]",
                category=ServiceCategory.INFERENCE,
                capabilities=["inference.summarize.v1", "ai.reasoning.synthesis"],
                description="[DEMO SEED] Performs analytical reasoning, summarization, and data synthesis from structured/unstructured inputs.",
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
                is_demo_seed=True,
                registry_version="1.0.0",
                capability_metadata=CapabilityMetadata(
                    version="1.0.0",
                    tags=["llm", "inference", "reasoning", "summarization", "synthesis"],
                    supported_formats=["text/plain", "application/json"],
                    max_payload_bytes=8192,
                    rate_limit_per_minute=20,
                    sla_latency_p95_ms=890,
                    deterministic=False,
                    constraints={
                        "max_prompt_length": 4000,
                        "max_tokens_limit": 1000,
                        "supported_models": ["mock-llm-v1", "gpt-3.5-turbo-equivalent"],
                    },
                ),
                reputation=ServiceReputationSummary(
                    service_id="inference_001",
                    reputation_score=99.0,
                    success_rate=0.99,
                    median_latency_ms=620.0,
                    latency_p95_ms=890.0,
                    total_calls=80,
                    successful_calls=79,
                    paid_output_rejected_calls=1,
                    listed_price_usdc="0.004",
                    last_call_at="2026-10-16T12:10:00Z"
                )
            )
        ]

        for s in seed_sellers:
            self.register_service(s)

    def register_service(self, service: ServiceRecord) -> None:
        """Register or update a service record with strict server-side schema validation."""
        validate_service_registration(service.model_dump())
        primary_id = service.service_id
        self._services[primary_id] = service

        # Register normalized aliases (e.g. data_001 <-> data-001)
        alt_id_1 = primary_id.replace("-", "_")
        alt_id_2 = primary_id.replace("_", "-")
        self._aliases[self._normalize_id(primary_id)] = primary_id
        self._aliases[self._normalize_id(alt_id_1)] = primary_id
        self._aliases[self._normalize_id(alt_id_2)] = primary_id

    def get_service(self, service_id: str) -> Optional[ServiceRecord]:
        """Lookup service with alias resolution (supporting both data_001 and data-001)."""
        normalized = self._normalize_id(service_id)
        resolved_id = self._aliases.get(normalized, service_id)
        service = self._services.get(resolved_id)
        if service and service.service_id != service_id:
            copy_svc = service.model_copy()
            copy_svc.service_id = service_id
            return copy_svc
        return service

    def get_active_service(self, service_id: str) -> Optional[ServiceRecord]:
        """Lookup service for buyer selection: excludes disabled services even if they exist."""
        service = self.get_service(service_id)
        if not service or not service.enabled or not service.is_active:
            return None
        return service

    def get_reputation(self, service_id: str) -> Optional[ServiceReputationSummary]:
        """Retrieve observed provider reputation through Member 4's ledger/reputation interface if available."""
        service = self.get_service(service_id)
        if not service:
            return None

        # Check Member 4's ReputationCalculator interface
        try:
            from backend.ledger.reputation import ReputationCalculator
            calc = ReputationCalculator()
            metrics = calc.calculate_for_service(service.service_id)
            if metrics and metrics.total_calls > 0:
                return ServiceReputationSummary(
                    service_id=service.service_id,
                    reputation_score=metrics.reputation_score,
                    success_rate=metrics.success_rate,
                    median_latency_ms=metrics.median_latency_ms,
                    latency_p95_ms=service.reputation.latency_p95_ms if service.reputation else 120.0,
                    total_calls=metrics.total_calls,
                    successful_calls=metrics.successful_calls,
                    paid_output_rejected_calls=metrics.schema_invalid_counts,
                    listed_price_usdc=service.price_usdc
                )
        except Exception:
            pass

        # Fallback to recorded reputation summary
        rep = service.reputation or ServiceReputationSummary(listed_price_usdc=service.price_usdc)
        rep.service_id = service.service_id
        return rep

    def list_services(
        self,
        category: Optional[str] = None,
        max_price_usdc: Optional[str] = None,
        min_price_usdc: Optional[str] = None,
        active: Optional[bool] = None,
        enabled: Optional[bool] = None,
        is_active: Optional[bool] = None,
        q: Optional[str] = None,
        capability: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> ServiceListResponse:
        """Search and filter services according to agreed API contracts."""
        results = list(self._services.values())

        # 1. Filter by enabled / active
        filter_status = enabled if enabled is not None else (is_active if is_active is not None else active)
        if filter_status is not None:
            results = [s for s in results if (s.enabled == filter_status and s.is_active == filter_status)]

        # 2. Filter by category
        if category:
            cat_clean = category.strip().lower()
            results = [
                s for s in results
                if s.category.value.lower() == cat_clean or s.category == cat_clean
            ]

        # 3. Filter by capability
        if capability:
            cap_clean = capability.strip().lower()
            results = [
                s for s in results
                if any(cap_clean in c.lower() for c in s.capabilities)
                or (s.capability_metadata and any(cap_clean in t.lower() for t in s.capability_metadata.tags))
            ]

        # 4. Filter by max price
        if max_price_usdc:
            max_units = usdc_to_base_units(max_price_usdc)
            results = [s for s in results if s.price_atomic <= max_units]

        # 5. Filter by min price
        if min_price_usdc:
            min_units = usdc_to_base_units(min_price_usdc)
            results = [s for s in results if s.price_atomic >= min_units]

        # 6. Text / capability query (q)
        if q:
            query = q.strip().lower()
            results = [
                s for s in results
                if query in s.name.lower()
                or query in s.description.lower()
                or query in s.service_id.lower()
                or query in s.category.value.lower()
                or any(query in c.lower() for c in s.capabilities)
                or (s.capability_metadata and any(query in t.lower() for t in s.capability_metadata.tags))
            ]

        total = len(results)
        paginated = results[offset : offset + limit]

        return ServiceListResponse(
            items=paginated,
            limit=limit,
            offset=offset,
            total=total
        )


# Global singleton instance for app runtime
registry_service = RegistryService()
