"""[IMPLEMENTED FOUNDATION] Scraping Seller Agent inheriting from BaseSellerService."""
from typing import Optional

from backend.sellers.common import BaseSellerService, SellerExecutionContext
from backend.sellers.schemas import ScrapingSellerInput, ScrapingSellerOutput


class ScrapingSellerService(BaseSellerService[ScrapingSellerInput, ScrapingSellerOutput]):
    """Fetches, parses, and extracts clean markdown/text content from target URLs."""

    def __init__(self, service_id: str = "scraping_001"):
        super().__init__(
            service_id=service_id,
            name="Web Markdown & Content Extractor",
            input_model=ScrapingSellerInput,
            output_model=ScrapingSellerOutput,
            default_timeout_seconds=5.0,
        )

    async def _execute_business_logic(
        self,
        payload: ScrapingSellerInput,
        context: SellerExecutionContext
    ) -> ScrapingSellerOutput:
        """Fetch and parse webpage content.
        NOTE: Deterministic baseline extracted structure for testing.
        Live async fetch, SSRF protection, and HTML parsing wired in Phase 3.
        """
        url_str = str(payload.url)
        content_stub = (
            f"Extracted content from {url_str}: Autonomous agent economies leverage "
            "micropayment rails such as x402 on Base Sepolia for frictionless API settlements."
        )
        return ScrapingSellerOutput(
            url=url_str,
            title=f"Extracted Data from {url_str}",
            content=content_stub,
            word_count=len(content_stub.split())
        )

    async def execute(self, payload: ScrapingSellerInput) -> ScrapingSellerOutput:
        """Backward-compatible direct execution method for existing routes & tests."""
        output, _ = await self.execute_lifecycle(payload)
        return output
