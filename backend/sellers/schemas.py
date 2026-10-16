"""Input and Output Schemas for the Three Seller Agents."""
from typing import Optional
from urllib.parse import urlparse
import ipaddress
from pydantic import BaseModel, Field, field_validator


# 1. Data Seller
class DataSellerInput(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10, description="Asset ticker symbol, e.g. BTC, ETH")

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Asset symbol cannot be empty or whitespace.")
        if not cleaned.isalnum():
            raise ValueError(f"Asset symbol '{cleaned}' must contain only alphanumeric characters.")
        return cleaned.upper()


class DataSellerOutput(BaseModel):
    symbol: str
    price: float = Field(..., description="Current price in USD")
    volume_24h: float = Field(..., description="24-hour trading volume")
    timestamp: str = Field(..., description="ISO 8601 data timestamp")


# 2. Scraping Seller
class ScrapingSellerInput(BaseModel):
    url: str = Field(..., max_length=2048, description="Target webpage URL to scrape")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        url_str = v.strip()
        if not url_str:
            raise ValueError("Target URL cannot be empty.")
        parsed = urlparse(url_str)
        if parsed.scheme.lower() not in ("http", "https"):
            raise ValueError(f"Invalid URL scheme '{parsed.scheme}'. Only HTTP and HTTPS are permitted.")
        hostname = (parsed.hostname or "").lower()
        if not hostname:
            raise ValueError("URL must include a valid hostname.")
        # SSRF checks: block loopback, private ranges, metadata, and local domains
        if hostname in ("localhost", "127.0.0.1", "::1", "0.0.0.0", "metadata.google.internal", "instance-data"):
            raise ValueError(f"SSRF Protection: Access to local/private destination '{hostname}' is prohibited.")
        if hostname.endswith(".local") or hostname.endswith(".internal") or hostname.endswith(".localhost"):
            raise ValueError(f"SSRF Protection: Access to private domain '{hostname}' is prohibited.")
        try:
            ip = ipaddress.ip_address(hostname)
            is_ip = True
        except ValueError:
            is_ip = False

        if is_ip and (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast):
            raise ValueError(f"SSRF Protection: Access to private/reserved IP address '{hostname}' is prohibited.")
        return url_str



class ScrapingSellerOutput(BaseModel):
    url: str
    title: str = Field(..., description="Extracted page title")
    content: str = Field(..., description="Clean markdown or text content")
    word_count: int = Field(..., description="Total extracted word count")


# 3. Inference Seller
class InferenceSellerInput(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=10000, description="Prompt or text to analyze")
    max_tokens: int = Field(default=200, ge=10, le=2000, description="Maximum generation tokens")
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Prompt cannot be empty or whitespace.")
        return cleaned


class InferenceSellerOutput(BaseModel):
    response: str = Field(..., description="Synthesized response or analysis")
    model_used: str = Field(..., description="Identifier of the model invoked")
    tokens_generated: int = Field(..., description="Count of output tokens generated")

