"""[DEFINED INTERFACE] Abstract Base Classes for Seller External Providers."""
from abc import ABC, abstractmethod
from typing import Dict, Any


class DataProviderInterface(ABC):
    """Abstract interface for external or mock market data providers."""

    @abstractmethod
    async def get_data(self, ticker: str) -> Dict[str, Any]:
        """Fetch market data for a normalized ticker symbol.
        
        Returns:
            Dict conforming to DataSellerOutput schema fields (symbol, price, volume_24h, change_24h, etc.).
        Raises:
            ProviderBaseError on failure.
        """
        pass


class ScrapingProviderInterface(ABC):
    """Abstract interface for safe HTTP web extraction providers."""

    @abstractmethod
    async def scrape_url(self, url: str) -> Dict[str, Any]:
        """Fetch and extract text/markdown content from target URL with SSRF protection.
        
        Returns:
            Dict conforming to ScrapingSellerOutput schema fields (url, content, title, content_length).
        Raises:
            ProviderBaseError on failure.
        """
        pass


class InferenceProviderInterface(ABC):
    """Abstract interface for LLM/reasoning inference providers."""

    @abstractmethod
    async def generate(self, prompt: str, max_tokens: int, temperature: float) -> Dict[str, Any]:
        """Generate text inference for a bounded prompt.
        
        Returns:
            Dict conforming to InferenceSellerOutput schema fields (result, model, tokens_used).
        Raises:
            ProviderBaseError on failure.
        """
        pass
