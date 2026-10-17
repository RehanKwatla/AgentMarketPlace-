"""[IMPLEMENTED] Configured Data Provider supporting FAKE and LIVE HTTP modes."""
from typing import Optional, Dict, Any
import httpx

from backend.sellers.providers.config import ProviderMode, ProviderSettings, get_provider_settings
from backend.sellers.providers.errors import (
    ProviderConfigurationError,
    ProviderRateLimitError,
    ProviderRequestRejectedError,
    ProviderResponseInvalidError,
    ProviderTimeoutError,
    ProviderUpstreamError,
)
from backend.sellers.providers.interfaces import DataProviderInterface
from backend.sellers.providers.data.fake import FakeDataProvider


class ConfiguredDataProvider(DataProviderInterface):
    """Configured market data provider with mode dispatch and robust error handling."""

    def __init__(
        self,
        settings: Optional[ProviderSettings] = None,
        client: Optional[httpx.AsyncClient] = None,
    ):
        self.settings = settings or get_provider_settings()
        self._client = client
        self._fake_provider = FakeDataProvider()

    async def get_data(self, ticker: str) -> Dict[str, Any]:
        """Fetch market data via fake generator or live HTTP endpoint."""
        if self.settings.mode == ProviderMode.FAKE:
            return await self._fake_provider.get_data(ticker)

        if not self.settings.data_provider_url:
            raise ProviderConfigurationError("LIVE mode requires DATA_PROVIDER_URL to be set.", provider_name="data_provider")

        headers = {}
        if self.settings.data_provider_api_key:
            headers["Authorization"] = f"Bearer {self.settings.data_provider_api_key}"

        timeout = httpx.Timeout(10.0)

        async def _do_fetch(client: httpx.AsyncClient) -> Dict[str, Any]:
            try:
                resp = await client.get(
                    self.settings.data_provider_url,
                    params={"symbol": ticker.upper()},
                    headers=headers,
                    timeout=timeout,
                )
            except httpx.TimeoutException as exc:
                raise ProviderTimeoutError(f"Data provider timed out: {exc}", provider_name="data_provider") from exc
            except httpx.HTTPError as exc:
                raise ProviderUpstreamError(f"Data provider network error: {exc}", provider_name="data_provider") from exc

            if resp.status_code == 429:
                retry_header = resp.headers.get("Retry-After")
                retry_secs = float(retry_header) if retry_header and retry_header.isdigit() else 30.0
                raise ProviderRateLimitError(
                    "Data provider rate limit exceeded",
                    provider_name="data_provider",
                    retry_after_seconds=retry_secs,
                )

            if resp.status_code >= 500:
                raise ProviderUpstreamError(f"Data provider upstream error: status {resp.status_code}", provider_name="data_provider")

            if resp.status_code != 200:
                raise ProviderRequestRejectedError(f"Data provider rejected request: status {resp.status_code}", provider_name="data_provider")

            try:
                data = resp.json()
            except Exception as exc:
                raise ProviderResponseInvalidError(f"Data provider returned malformed JSON: {exc}", provider_name="data_provider") from exc

            if not isinstance(data, dict):
                raise ProviderResponseInvalidError("Data provider response is not a JSON object", provider_name="data_provider")

            if "price" not in data:
                raise ProviderResponseInvalidError("Data provider response missing required field 'price'", provider_name="data_provider")

            if "symbol" not in data:
                data["symbol"] = ticker.upper()

            return data

        if self._client is not None:
            return await _do_fetch(self._client)
        else:
            async with httpx.AsyncClient() as client:
                return await _do_fetch(client)
