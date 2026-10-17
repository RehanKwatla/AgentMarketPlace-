"""[IMPLEMENTED] Data Provider package."""
from .fake import FakeDataProvider
from .configured_provider import ConfiguredDataProvider

__all__ = ["FakeDataProvider", "ConfiguredDataProvider"]
