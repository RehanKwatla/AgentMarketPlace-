"""[IMPLEMENTED] Provider Mode and Execution Bounds Configuration."""
import os
from enum import Enum
from typing import Optional, Any
from dotenv import load_dotenv
from pydantic import BaseModel, Field, model_validator

# Load environment variables from .env if present
load_dotenv()


class ProviderMode(str, Enum):
    FAKE = "fake"
    LIVE = "live"


class InferenceProviderType(str, Enum):
    GEMINI = "gemini"
    GROQ = "groq"
    OPENAI = "openai"


def _resolve_default_inference_provider() -> InferenceProviderType:
    env_val = os.getenv("INFERENCE_PROVIDER")
    if env_val:
        return InferenceProviderType(env_val.lower())
    if os.getenv("GROQ_API_KEY"):
        return InferenceProviderType.GROQ
    if os.getenv("GEMINI_API_KEY"):
        return InferenceProviderType.GEMINI
    if os.getenv("OPENAI_API_KEY"):
        return InferenceProviderType.OPENAI
    return InferenceProviderType.GROQ


class ProviderSettings(BaseModel):
    """Configuration settings for seller external provider adapters."""

    @model_validator(mode="before")
    @classmethod
    def _infer_provider_from_explicit_keys(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "inference_provider" not in data:
                if data.get("openai_api_key") and not data.get("gemini_api_key") and not data.get("groq_api_key"):
                    data["inference_provider"] = InferenceProviderType.OPENAI
                elif data.get("groq_api_key"):
                    data["inference_provider"] = InferenceProviderType.GROQ
                elif data.get("gemini_api_key"):
                    data["inference_provider"] = InferenceProviderType.GEMINI
        return data

    mode: ProviderMode = Field(
        default_factory=lambda: ProviderMode(os.getenv("SELLER_PROVIDER_MODE", "fake").lower())
    )

    # Data can be demo-backed independently while inference remains live.
    # Unset preserves the legacy shared SELLER_PROVIDER_MODE behavior.
    data_provider_mode: Optional[ProviderMode] = Field(
        default_factory=lambda: (
            ProviderMode(os.getenv("DATA_PROVIDER_MODE", "").lower())
            if os.getenv("DATA_PROVIDER_MODE")
            else None
        )
    )
    
    # Inference Provider Selection
    inference_provider: InferenceProviderType = Field(
        default_factory=_resolve_default_inference_provider
    )

    # Google Gemini Configuration
    gemini_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY"))
    gemini_model: str = Field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-3.8-flash"))

    # Groq Configuration
    groq_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("GROQ_API_KEY"))
    groq_model: str = Field(default_factory=lambda: os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b"))

    # OpenAI / Custom Generic Inference Configuration (Backward Compatibility)
    openai_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    inference_provider_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("INFERENCE_PROVIDER_API_KEY"))
    inference_provider_url: Optional[str] = Field(default_factory=lambda: os.getenv("INFERENCE_PROVIDER_URL"))
    inference_default_model: Optional[str] = Field(default_factory=lambda: os.getenv("INFERENCE_DEFAULT_MODEL"))

    # Inference Execution Bounds
    inference_timeout_seconds: float = Field(
        default_factory=lambda: float(os.getenv("INFERENCE_TIMEOUT_SECONDS", "15.0"))
    )
    inference_max_tokens: int = Field(default=2000)

    # Data Provider Bounds & Credentials
    data_provider_url: Optional[str] = Field(default_factory=lambda: os.getenv("DATA_PROVIDER_URL"))
    data_provider_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("DATA_PROVIDER_API_KEY"))

    # Scraping Provider Bounds
    scraping_connect_timeout_seconds: float = Field(default=5.0)
    scraping_read_timeout_seconds: float = Field(default=10.0)
    scraping_total_timeout_seconds: float = Field(default=15.0)
    scraping_max_redirects: int = Field(default=3)
    scraping_max_response_bytes: int = Field(default=1_000_000)  # 1 MB
    scraping_max_extract_chars: int = Field(default=50_000)


# Singleton configuration instance
provider_settings = ProviderSettings()


def get_provider_settings() -> ProviderSettings:
    """Return provider settings instance."""
    return provider_settings

