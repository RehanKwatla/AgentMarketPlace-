"""Application Configuration with Pydantic Settings."""
from functools import lru_cache
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from .constants import NETWORK_BASE_SEPOLIA, USDC_BASE_SEPOLIA, CHAIN_ID_BASE_SEPOLIA


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Core App Settings
    environment: str = Field(default="development", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    # Blockchain & Network (Base Sepolia)
    blockchain_network: str = Field(default=NETWORK_BASE_SEPOLIA, alias="BLOCKCHAIN_NETWORK")
    base_sepolia_rpc_url: str = Field(default="https://sepolia.base.org", alias="BASE_SEPOLIA_RPC_URL")
    chain_id: int = Field(default=CHAIN_ID_BASE_SEPOLIA, alias="CHAIN_ID")

    # Token Configuration
    usdc_contract_address: str = Field(default=USDC_BASE_SEPOLIA, alias="USDC_CONTRACT_ADDRESS")
    usdc_decimals: int = Field(default=6, alias="USDC_DECIMALS")

    # x402 Facilitator
    x402_facilitator_url: str = Field(default="https://facilitator.x402.org", alias="X402_FACILITATOR_URL")
    x402_client_timeout_seconds: float = Field(default=15.0, alias="X402_CLIENT_TIMEOUT_SECONDS")

    # Buyer Settings
    buyer_wallet_address: str = Field(default="0x0000000000000000000000000000000000000000", alias="BUYER_WALLET_ADDRESS")
    buyer_private_key: Optional[str] = Field(default=None, alias="BUYER_PRIVATE_KEY")
    buyer_max_budget_usdc: str = Field(default="1.000000", alias="BUYER_MAX_BUDGET_USDC")
    buyer_default_per_request_max_usdc: str = Field(default="0.050000", alias="BUYER_DEFAULT_PER_REQUEST_MAX_USDC")

    # Seller Pay-To Addresses
    data_seller_pay_to: str = Field(default="0x0000000000000000000000000000000000000001", alias="DATA_SELLER_PAY_TO")
    scraping_seller_pay_to: str = Field(default="0x0000000000000000000000000000000000000002", alias="SCRAPING_SELLER_PAY_TO")
    inference_seller_pay_to: str = Field(default="0x0000000000000000000000000000000000000003", alias="INFERENCE_SELLER_PAY_TO")

    # Seller Endpoints
    data_seller_endpoint: str = Field(default="http://localhost:8000/api/v1/seller/data", alias="DATA_SELLER_ENDPOINT")
    scraping_seller_endpoint: str = Field(default="http://localhost:8000/api/v1/seller/scraping", alias="SCRAPING_SELLER_ENDPOINT")
    inference_seller_endpoint: str = Field(default="http://localhost:8000/api/v1/seller/inference", alias="INFERENCE_SELLER_ENDPOINT")

    # Database
    database_url: str = Field(default="sqlite:///./local_data/ledger.db", alias="DATABASE_URL")

    # Frontend
    frontend_port: int = Field(default=5173, alias="FRONTEND_PORT")
    vite_api_base_url: str = Field(default="http://localhost:8000", alias="VITE_API_BASE_URL")

    # Optional AI Keys
    groq_api_key: Optional[str] = Field(default=None, alias="GROQ_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")


@lru_cache()
def get_settings() -> Settings:
    """Return cached instance of application settings."""
    return Settings()
