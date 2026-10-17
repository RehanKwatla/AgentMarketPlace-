"""[IMPLEMENTED] Deterministic Offline Data Provider for Testing & Demo."""
from datetime import datetime, timezone
from typing import Dict, Any

from backend.sellers.providers.interfaces import DataProviderInterface


class FakeDataProvider(DataProviderInterface):
    """Deterministic offline market data provider."""

    async def get_data(self, ticker: str) -> Dict[str, Any]:
        symbol = ticker.strip().upper()
        now = datetime.now(timezone.utc).isoformat()

        if symbol == "BTC":
            price = 67500.00
            volume_24h = 1500000.0
            change_24h = 2.5
        elif symbol == "ETH":
            price = 2650.50
            volume_24h = 1200000.0
            change_24h = -1.2
        else:
            seed_val = sum(ord(c) for c in symbol)
            price = round(100.0 + (seed_val % 500) * 1.5, 2)
            volume_24h = round(50000.0 + (seed_val % 1000) * 10.0, 1)
            change_24h = round(((seed_val % 20) - 10) * 0.5, 2)

        return {
            "symbol": symbol,
            "price": price,
            "volume_24h": volume_24h,
            "timestamp": now,
            "change_24h": change_24h,
        }
