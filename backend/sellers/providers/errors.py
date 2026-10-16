"""[IMPLEMENTED] Normalized Provider Error Hierarchy for Seller Microservices.

Ensures consistent error classifications across Data, Scraping, and Inference providers
without leaking raw vendor exceptions or sensitive credentials.
"""
from typing import Optional


class ProviderBaseError(Exception):
    """Root base class for all provider-related errors."""
    def __init__(self, message: str, provider_name: str, status_code: int = 500, retryable: bool = False):
        super().__init__(message)
        self.message = message
        self.provider_name = provider_name
        self.status_code = status_code
        self.retryable = retryable


class ProviderConfigurationError(ProviderBaseError):
    """Raised when required provider configuration (API keys, URLs) is missing or invalid."""
    def __init__(self, message: str, provider_name: str):
        super().__init__(message, provider_name=provider_name, status_code=503, retryable=False)


class ProviderRequestRejectedError(ProviderBaseError):
    """Raised when upstream provider rejects request due to invalid input or client-side error (4xx)."""
    def __init__(self, message: str, provider_name: str):
        super().__init__(message, provider_name=provider_name, status_code=400, retryable=False)


class ProviderTimeoutError(ProviderBaseError):
    """Raised when an external provider call exceeds connect, read, or overall deadline."""
    def __init__(self, message: str, provider_name: str):
        super().__init__(message, provider_name=provider_name, status_code=504, retryable=True)


class ProviderRateLimitError(ProviderBaseError):
    """Raised when upstream provider responds with HTTP 429 Too Many Requests."""
    def __init__(self, message: str, provider_name: str, retry_after_seconds: Optional[float] = None):
        super().__init__(message, provider_name=provider_name, status_code=429, retryable=True)
        self.retry_after_seconds = retry_after_seconds


class ProviderUpstreamError(ProviderBaseError):
    """Raised when upstream provider encounters an outage or returns HTTP 5xx."""
    def __init__(self, message: str, provider_name: str):
        super().__init__(message, provider_name=provider_name, status_code=502, retryable=True)


class ProviderResponseInvalidError(ProviderBaseError):
    """Raised when provider returns unparseable or schema-violating payload."""
    def __init__(self, message: str, provider_name: str):
        super().__init__(message, provider_name=provider_name, status_code=502, retryable=False)


class ProviderOutputLimitExceededError(ProviderBaseError):
    """Raised when provider response exceeds maximum allowed characters, bytes, or tokens."""
    def __init__(self, message: str, provider_name: str):
        super().__init__(message, provider_name=provider_name, status_code=502, retryable=False)


class ProviderSSRFBlockedError(ProviderBaseError):
    """Raised when scraping target violates connection-time SSRF policies."""
    def __init__(self, message: str, destination: str):
        super().__init__(message, provider_name="scraping_fetcher", status_code=400, retryable=False)
        self.destination = destination
