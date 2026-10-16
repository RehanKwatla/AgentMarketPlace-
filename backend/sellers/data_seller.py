"""[DEFINED INTERFACE & STUB] Data Seller Agent."""
from datetime import datetime, timezone
from backend.sellers.schemas import DataSellerInput, DataSellerOutput


class DataSellerService:
    """Provides market and financial asset metrics."""

    def __init__(self, service_id: str = "data_001"):
        self.service_id = service_id

    async def execute(self, payload: DataSellerInput) -> DataSellerOutput:
        """Fetch and return market data.
        NOTE: Temporary stub returning deterministic structured data for integration tests.
        Member 2 will wire live market feed/API.
        """
        symbol_upper = payload.symbol.upper()
        # Baseline deterministic prices for testing
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
