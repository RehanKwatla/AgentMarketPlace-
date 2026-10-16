"""[IMPLEMENTED FOUNDATION] Data Seller Agent inheriting from BaseSellerService."""
from datetime import datetime, timezone
from typing import Optional

from backend.sellers.common import BaseSellerService, SellerExecutionContext
from backend.sellers.schemas import DataSellerInput, DataSellerOutput


class DataSellerService(BaseSellerService[DataSellerInput, DataSellerOutput]):
    """Provides market and financial asset metrics with lifecycle management."""

    def __init__(self, service_id: str = "data_001"):
        super().__init__(
            service_id=service_id,
            name="Alpha Financial Market Data",
            input_model=DataSellerInput,
            output_model=DataSellerOutput,
            default_timeout_seconds=5.0,
        )

    async def _execute_business_logic(
        self,
        payload: DataSellerInput,
        context: SellerExecutionContext
    ) -> DataSellerOutput:
        """Fetch and return market data.
        NOTE: Deterministic baseline prices for testing.
        Live feeds and external caching are wired in Phase 2.
        """
        symbol_upper = payload.symbol.upper()
        mock_prices = {
            "ETH": 2650.50,
            "BTC": 67500.00,
            "USDC": 1.00
        }
        price = mock_prices.get(symbol_upper, 100.00)
        return DataSellerOutput(
            symbol=symbol_upper,
            price=price,
            volume_24h=1420500.0,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    async def execute(self, payload: DataSellerInput) -> DataSellerOutput:
        """Backward-compatible direct execution method for existing routes & tests."""
        output, _ = await self.execute_lifecycle(payload)
        return output
