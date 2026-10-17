"""Scraping Provider subpackage."""
from .fetcher import SafeScrapingFetcher, FakeScrapingProvider
from .safety import validate_url_syntax, resolve_and_validate_destination
from .parser import extract_clean_content
from .transport import PinnedAsyncNetworkBackend, PinnedAsyncHTTPTransport

__all__ = [
    "SafeScrapingFetcher",
    "FakeScrapingProvider",
    "validate_url_syntax",
    "resolve_and_validate_destination",
    "extract_clean_content",
    "PinnedAsyncNetworkBackend",
    "PinnedAsyncHTTPTransport",
]
