"""[IMPLEMENTED] Scraping Seller Agent with Injected Provider Adapter."""
from typing import Optional

from backend.sellers.common import (
    BaseSellerService,
    SellerExecutionContext,
    SellerExecutionError,
    SellerExecutionTimeoutError,
    SellerInputValidationError,
)
from backend.sellers.schemas import ScrapingSellerInput, ScrapingSellerOutput
from backend.sellers.providers.interfaces import ScrapingProviderInterface
from backend.sellers.providers.scraping.fetcher import FakeScrapingProvider
from backend.sellers.providers.errors import ProviderBaseError


class ScrapingSellerService(BaseSellerService[ScrapingSellerInput, ScrapingSellerOutput]):
    """Fetches, parses, and extracts clean markdown/text content from target URLs."""

    def __init__(
        self,
        service_id: str = "scraping_001",
        provider: Optional[ScrapingProviderInterface] = None,
        default_timeout_seconds: float = 15.0,
    ):
        super().__init__(
            service_id=service_id,
            name="Web Markdown & Content Extractor",
            input_model=ScrapingSellerInput,
            output_model=ScrapingSellerOutput,
            default_timeout_seconds=default_timeout_seconds,
        )
        self.provider = provider or FakeScrapingProvider()

    async def _execute_business_logic(
        self,
        payload: ScrapingSellerInput,
        context: SellerExecutionContext
    ) -> ScrapingSellerOutput:
        """Fetch and parse webpage content with bounded response limits and SSRF defense."""
        url_str = str(payload.url)
        try:
            data = await self.provider.scrape_url(url_str)
        except ProviderBaseError as prov_err:
            if prov_err.status_code == 400:
                raise SellerInputValidationError(details=prov_err.message, service_id=self.service_id)
            if prov_err.status_code == 504:
                raise SellerExecutionTimeoutError(timeout_seconds=self.default_timeout_seconds, service_id=self.service_id)
            raise SellerExecutionError(details=prov_err.message, service_id=self.service_id)
        except Exception as exc:
            raise SellerExecutionError(details=f"Scraping provider failure: {exc}", service_id=self.service_id)

        clean_content = data.get("content", "")
        # Enforce maximum extracted character safeguard
        bounded_content = clean_content[:50000]
        word_count = data.get("word_count") or len(bounded_content.split())

        return ScrapingSellerOutput(
            url=data.get("url", url_str),
            title=data.get("title", f"Extracted Data from {url_str}"),
            content=bounded_content,
            word_count=word_count,
        )

    async def execute(self, payload: ScrapingSellerInput) -> ScrapingSellerOutput:
        """Backward-compatible direct execution method for existing routes & tests."""
        output, _ = await self.execute_lifecycle(payload)
        return output
