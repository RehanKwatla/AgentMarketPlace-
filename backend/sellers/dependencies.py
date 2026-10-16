"""[IMPLEMENTED FOUNDATION] Seller Dependencies and Service Factories.

Provides reusable dependency providers and execution context extractors for
the seller microservices (Data, Scraping, Inference).

Adheres strictly to FastAPI dependency injection conventions, supporting
override in tests without mutating global state or performing side effects.
"""
from typing import Optional
from fastapi import Header, Request

from backend.shared.config import Settings, get_settings
from backend.shared.constants import (
    HEADER_IDEMPOTENCY_KEY,
    HEADER_X402_PAYMENT_PAYLOAD,
)
from backend.sellers.common import SellerExecutionContext
from backend.sellers.data_seller import DataSellerService
from backend.sellers.scraping_seller import ScrapingSellerService
from backend.sellers.inference_seller import InferenceSellerService


# ==============================================================================
# 1. Service Dependency Providers (Factories)
# ==============================================================================

def get_data_seller_service() -> DataSellerService:
    """Dependency provider returning DataSellerService instance.
    Can be overridden in tests via app.dependency_overrides[get_data_seller_service].
    """
    return DataSellerService(service_id="data_001")


def get_scraping_seller_service() -> ScrapingSellerService:
    """Dependency provider returning ScrapingSellerService instance.
    Can be overridden in tests via app.dependency_overrides[get_scraping_seller_service].
    """
    return ScrapingSellerService(service_id="scraping_001")


def get_inference_seller_service() -> InferenceSellerService:
    """Dependency provider returning InferenceSellerService instance.
    Can be overridden in tests via app.dependency_overrides[get_inference_seller_service].
    """
    return InferenceSellerService(service_id="inference_001")


# ==============================================================================
# 2. Execution Context Extractor Dependency
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

    return SellerExecutionContext(
        service_id=service_id,
        idempotency_key=idempotency_key,
        client_ip=client_ip,
    )
