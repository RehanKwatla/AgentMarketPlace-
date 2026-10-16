"""Inference Provider subpackage."""
from .fake import FakeInferenceProvider
from .configured_provider import ConfiguredInferenceProvider

__all__ = ["FakeInferenceProvider", "ConfiguredInferenceProvider"]
