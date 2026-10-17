"""[IMPLEMENTED] Data Seller Agent with Injected Provider Adapter."""
from datetime import datetime, timezone
from typing import Optional

from backend.sellers.common import (
    BaseSellerService,
    SellerExecutionContext,
    SellerExecutionError,
    SellerExecutionTimeoutError,
    SellerInputValidationError,
)
from backend.sellers.schemas import DataSellerInput, DataSellerOutput
from backend.sellers.providers.interfaces import DataProviderInterface
from backend.sellers.providers.data.fake import FakeDataProvider
from backend.sellers.providers.errors import ProviderBaseError


class DataSellerService(BaseSellerService[DataSellerInput, DataSellerOutput]):
    """Provides market and financial asset metrics with lifecycle management."""

    def __init__(
        self,
        service_id: str = "data_001",
        provider: Optional[DataProviderInterface] = None,
        default_timeout_seconds: float = 5.0,
    ):
        super().__init__(
            service_id=service_id,
            name="Alpha Financial Market Data",
            input_model=DataSellerInput,
            output_model=DataSellerOutput,
            default_timeout_seconds=default_timeout_seconds,
        )
        self.provider = provider or FakeDataProvider()

    async def _execute_business_logic(
        self,
        payload: DataSellerInput,
        context: SellerExecutionContext
    ) -> DataSellerOutput:
        """Fetch and return market data via injected provider adapter."""
        try:
            raw_data = await self.provider.get_data(payload.symbol)
        except ProviderBaseError as prov_err:
            if prov_err.status_code == 400:
                raise SellerInputValidationError(details=prov_err.message, service_id=self.service_id)
            if prov_err.status_code == 504:
                raise SellerExecutionTimeoutError(timeout_seconds=self.default_timeout_seconds, service_id=self.service_id)
            raise SellerExecutionError(details=prov_err.message, service_id=self.service_id)
        except Exception as exc:
            raise SellerExecutionError(details=f"Data provider failure: {exc}", service_id=self.service_id)

        return DataSellerOutput(
            symbol=raw_data["symbol"],
            price=float(raw_data["price"]),
            volume_24h=float(raw_data.get("volume_24h", 0.0)),
            timestamp=raw_data.get("timestamp") or datetime.now(timezone.utc).isoformat(),
        )

    async def execute(self, payload: DataSellerInput) -> DataSellerOutput:
        """Backward-compatible direct execution method for existing routes & tests."""
        output, _ = await self.execute_lifecycle(payload)
        return output
