"""Service Catalog backwards-compatibility layer aliasing to registry_service."""
from typing import List, Optional
from backend.registry.service import RegistryService, registry_service
from backend.registry.schemas import ServiceRecord

ServiceCatalog = RegistryService
catalog = registry_service

__all__ = ["ServiceCatalog", "catalog"]
