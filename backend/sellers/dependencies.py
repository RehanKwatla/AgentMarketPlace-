"""[IMPLEMENTED] Seller Dependencies, Provider Factories, and Execution Context.

Provides reusable dependency providers and execution context extractors for
the seller microservices (Data, Scraping, Inference).

Supports explicit provider injection (FAKE vs LIVE) and FastAPI dependency overrides
without mutating global state or performing side effects.
"""
from typing import Optional
from fastapi import Depends, Header, Request

from backend.shared.config import Settings, get_settings
from backend.shared.constants import (
    HEADER_IDEMPOTENCY_KEY,
    HEADER_X402_PAYMENT_PAYLOAD,
)
from backend.sellers.common import SellerExecutionContext
from backend.sellers.data_seller import DataSellerService
from backend.sellers.scraping_seller import ScrapingSellerService
from backend.sellers.inference_seller import InferenceSellerService

from backend.sellers.providers.config import (
    ProviderMode,
    ProviderSettings,
    get_provider_settings,
)
from backend.sellers.providers.interfaces import (
    DataProviderInterface,
    ScrapingProviderInterface,
    InferenceProviderInterface,
)
from backend.sellers.providers.data.fake import FakeDataProvider
from backend.sellers.providers.data.configured_provider import ConfiguredDataProvider
from backend.sellers.providers.scraping.fetcher import FakeScrapingProvider, SafeScrapingFetcher
from backend.sellers.providers.inference.fake import FakeInferenceProvider
from backend.sellers.providers.inference.configured_provider import ConfiguredInferenceProvider


# ==============================================================================
# 1. Provider Dependency Providers (Factories)
# ==============================================================================

def get_data_provider(
    settings: ProviderSettings = Depends(get_provider_settings),
) -> DataProviderInterface:
    """Dependency provider for DataProviderInterface.
    Selects ConfiguredDataProvider in LIVE mode, FakeDataProvider in FAKE mode.
    Can be overridden via app.dependency_overrides[get_data_provider].
    """
    if settings.mode == ProviderMode.LIVE:
        return ConfiguredDataProvider(settings=settings)
    return FakeDataProvider()


def get_scraping_provider(
    settings: ProviderSettings = Depends(get_provider_settings),
) -> ScrapingProviderInterface:
    """Dependency provider for ScrapingProviderInterface.
    Selects SafeScrapingFetcher in LIVE mode, FakeScrapingProvider in FAKE mode.
    Can be overridden via app.dependency_overrides[get_scraping_provider].
    """
    if settings.mode == ProviderMode.LIVE:
        return SafeScrapingFetcher(settings=settings)
    return FakeScrapingProvider()


def get_inference_provider(
    settings: ProviderSettings = Depends(get_provider_settings),
) -> InferenceProviderInterface:
    """Dependency provider for InferenceProviderInterface.
    Selects ConfiguredInferenceProvider in LIVE mode, FakeInferenceProvider in FAKE mode.
    Can be overridden via app.dependency_overrides[get_inference_provider].
    """
    if settings.mode == ProviderMode.LIVE:
        return ConfiguredInferenceProvider(settings=settings)
    return FakeInferenceProvider()


# ==============================================================================
# 2. Service Dependency Providers (Factories)
# ==============================================================================

def get_data_seller_service(
    provider: DataProviderInterface = Depends(get_data_provider),
) -> DataSellerService:
    """Dependency provider returning DataSellerService instance.
    Can be overridden in tests via app.dependency_overrides[get_data_seller_service].
    """
    return DataSellerService(service_id="data_001", provider=provider)


def get_scraping_seller_service(
    provider: ScrapingProviderInterface = Depends(get_scraping_provider),
) -> ScrapingSellerService:
    """Dependency provider returning ScrapingSellerService instance.
    Can be overridden in tests via app.dependency_overrides[get_scraping_seller_service].
    """
    return ScrapingSellerService(service_id="scraping_001", provider=provider)


def get_inference_seller_service(
    provider: InferenceProviderInterface = Depends(get_inference_provider),
) -> InferenceSellerService:
    """Dependency provider returning InferenceSellerService instance.
    Can be overridden in tests via app.dependency_overrides[get_inference_seller_service].
    """
    return InferenceSellerService(service_id="inference_001", provider=provider)


# ==============================================================================
# 3. Execution Context Extractor Dependency
# ==============================================================================

def get_seller_execution_context(
    request: Request,
    idempotency_key: Optional[str] = Header(None, alias=HEADER_IDEMPOTENCY_KEY),
) -> SellerExecutionContext:
    """Extracts HTTP request context into a structured SellerExecutionContext.
    
    Infers service_id from path if available (e.g. /data, /scraping, /inference).
    Captures client IP and client-supplied Idempotency-Key.
    """
    path = request.url.path.lower()
    if "data" in path:
        service_id = "data_001"
    elif "scraping" in path:
        service_id = "scraping_001"
    elif "inference" in path:
        service_id = "inference_001"
    else:
        service_id = "unknown_seller"

    client_ip = request.client.host if request.client else None
    cleaned_idempotency_key = idempotency_key if isinstance(idempotency_key, str) else None

    return SellerExecutionContext(
        service_id=service_id,
        idempotency_key=cleaned_idempotency_key,
        client_ip=client_ip,
    )
