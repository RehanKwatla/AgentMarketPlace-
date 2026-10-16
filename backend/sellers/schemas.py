"""Input and Output Schemas for the Three Seller Agents."""
from typing import Optional
from pydantic import BaseModel, Field, HttpUrl


# 1. Data Seller
class DataSellerInput(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10, description="Asset ticker symbol, e.g. BTC, ETH")


class DataSellerOutput(BaseModel):
    symbol: str
    price: float = Field(..., description="Current price in USD")
    volume_24h: float = Field(..., description="24-hour trading volume")
    timestamp: str = Field(..., description="ISO 8601 data timestamp")


# 2. Scraping Seller
class ScrapingSellerInput(BaseModel):
    url: str = Field(..., description="Target webpage URL to scrape")


class ScrapingSellerOutput(BaseModel):
    url: str
    title: str = Field(..., description="Extracted page title")
    content: str = Field(..., description="Clean markdown or text content")
    word_count: int = Field(..., description="Total extracted word count")


# 3. Inference Seller
class InferenceSellerInput(BaseModel):
    prompt: str = Field(..., min_length=1, description="Prompt or text to analyze")
    max_tokens: int = Field(default=200, ge=10, le=2000, description="Maximum generation tokens")
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)


class InferenceSellerOutput(BaseModel):
    response: str = Field(..., description="Synthesized response or analysis")
    model_used: str = Field(..., description="Identifier of the model invoked")
    tokens_generated: int = Field(..., description="Count of output tokens generated")
