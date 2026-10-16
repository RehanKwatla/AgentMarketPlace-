"""Registry Schemas matching API_CONTRACTS.md and Member 3 specifications."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator
from backend.shared.constants import (
    NETWORK_BASE_SEPOLIA,
    USDC_BASE_SEPOLIA,
    ServiceCategory,
    usdc_to_base_units,
    base_units_to_usdc,
)


class ServiceReputationSummary(BaseModel):
    service_id: Optional[str] = None
    reputation_score: float = Field(default=98.0, ge=0.0, le=100.0)
    success_rate: float = Field(default=1.0, ge=0.0, le=1.0)
    median_latency_ms: float = Field(default=0.0, ge=0.0)
    latency_p95_ms: float = Field(default=120.0, ge=0.0)
    total_calls: int = Field(default=0, ge=0)
    successful_calls: int = Field(default=0, ge=0)
    paid_output_rejected_calls: int = Field(default=0, ge=0)
    listed_price_usdc: str = Field(default="0.002000")
    last_call_at: Optional[str] = None


class ServiceRecord(BaseModel):
    service_id: str = Field(..., description="Stable public identifier slug, e.g. data-001 or data_001")
    name: str = Field(..., min_length=2, max_length=128)
    category: ServiceCategory = Field(..., description="Category: data, scraping, or inference")
    capabilities: List[str] = Field(default_factory=list, description="Capability URIs, e.g. data.lookup.v1")
    description: str = Field(default="", max_length=1000)
    endpoint_url: str = Field(..., description="Public or internal endpoint URL")
    price_usdc: str = Field(..., description="Decimal USDC price, e.g. '0.002000'")
    price_atomic: int = Field(default=0, ge=0, description="Integer base units (6 decimals)")
    price_base_units: int = Field(default=0, ge=0, description="Integer base units alias")
    network: str = Field(default=NETWORK_BASE_SEPOLIA, description="CAIP-2 network string")
    asset_address: str = Field(default=USDC_BASE_SEPOLIA, description="Token contract address")
    pay_to: str = Field(..., description="Seller receiving wallet address")
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = Field(default=True)
    enabled: bool = Field(default=True)
    is_demo_seed: bool = Field(default=True, description="True for demo/seed records, False for live registrations")
    registry_version: str = Field(default="1.0.0")
    token: Optional[str] = Field(default=None, description="Alias for asset_address")
    pay_to_address: Optional[str] = Field(default=None, description="Alias for pay_to")
    capability: Optional[str] = Field(default=None, description="Primary capability URI")
    reputation: Optional[ServiceReputationSummary] = Field(default_factory=ServiceReputationSummary)

    @model_validator(mode="before")
    @classmethod
    def resolve_field_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("pay_to") and data.get("pay_to_address"):
                data["pay_to"] = data["pay_to_address"]
            elif not data.get("pay_to_address") and data.get("pay_to"):
                data["pay_to_address"] = data["pay_to"]

            if not data.get("asset_address") and data.get("token"):
                data["asset_address"] = data["token"]
            elif not data.get("token") and data.get("asset_address"):
                data["token"] = data["asset_address"]

            if not data.get("capability") and data.get("capabilities"):
                data["capability"] = data["capabilities"][0]
            elif not data.get("capabilities") and data.get("capability"):
                data["capabilities"] = [data["capability"]]
        return data

    @model_validator(mode="after")
    def sync_prices_and_active(self) -> "ServiceRecord":
        # Sync token and asset_address
        if self.token:
            self.asset_address = self.token
        elif self.asset_address:
            self.token = self.asset_address

        # Sync pay_to and pay_to_address
        if self.pay_to_address:
            self.pay_to = self.pay_to_address
        elif self.pay_to:
            self.pay_to_address = self.pay_to

        # Sync capability and capabilities
        if self.capabilities and not self.capability:
            self.capability = self.capabilities[0]
        elif self.capability and not self.capabilities:
            self.capabilities = [self.capability]
        if self.price_usdc and (self.price_atomic is None or self.price_atomic == 0):
            self.price_atomic = usdc_to_base_units(self.price_usdc)
        elif self.price_atomic > 0 and (not self.price_usdc or self.price_usdc == "0"):
            self.price_usdc = base_units_to_usdc(self.price_atomic)

        # Sync price_base_units and price_atomic
        if self.price_atomic > 0:
            self.price_base_units = self.price_atomic
        elif self.price_base_units > 0:
            self.price_atomic = self.price_base_units

        # Synchronize enabled and is_active
        if not self.enabled:
            self.is_active = False
        elif not self.is_active:
            self.enabled = False

        return self


class ServiceListResponse(BaseModel):
    items: List[ServiceRecord] = Field(default_factory=list)
    limit: int = 20
    offset: int = 0
    total: int = 0

    # Backwards compatibility alias for 'services'
    @property
    def services(self) -> List[ServiceRecord]:
        return self.items

    def __iter__(self):
        return iter(self.items)

    def __getitem__(self, item):
        return self.items[item]

    def __len__(self):
        return len(self.items)

    def model_dump(self, *args, **kwargs):
        data = super().model_dump(*args, **kwargs)
        # Ensure both 'items' and 'services' are accessible in JSON responses
        data["services"] = data.get("items", [])
        return data


class ServiceRegistrationRequest(BaseModel):
    service_id: str = Field(..., min_length=3, max_length=64)
    name: str = Field(..., min_length=2, max_length=128)
    category: ServiceCategory
    capabilities: List[str] = Field(default_factory=list)
    description: str = Field(default="")
    endpoint_url: str
    price_usdc: str
    network: str = Field(default=NETWORK_BASE_SEPOLIA)
    pay_to: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    enabled: bool = Field(default=True)
