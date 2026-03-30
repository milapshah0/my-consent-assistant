from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=True, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    database_url: str = Field(alias="DATABASE_URL")
    database_pool_size: int = Field(default=20, alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=10, alias="DATABASE_MAX_OVERFLOW")

    confluence_email: str = Field(default="", alias="CONFLUENCE_EMAIL")
    confluence_api_token: str = Field(default="", alias="CONFLUENCE_API_TOKEN")
    confluence_base_url: str = Field(default="", alias="CONFLUENCE_BASE_URL")
    confluence_space_keys_raw: str = Field(default="", alias="CONFLUENCE_SPACE_KEYS")

    aha_api_key: str = Field(default="", alias="AHA_API_KEY")
    aha_base_url: str = Field(default="", alias="AHA_BASE_URL")
    aha_product_key: str = Field(default="", alias="AHA_PRODUCT_KEY")

    azure_openai_api_key: str = Field(default="", alias="AZURE_OPENAI_API_KEY")
    azure_openai_endpoint: str = Field(default="", alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_version: str = Field(
        default="2024-12-01-preview", alias="AZURE_OPENAI_API_VERSION"
    )
    azure_openai_chat_deployment: str = Field(
        default="gpt-4o-mini", alias="AZURE_OPENAI_CHAT_DEPLOYMENT"
    )
    azure_openai_embedding_deployment: str = Field(
        default="text-embedding-3-small",
        alias="AZURE_OPENAI_EMBEDDING_DEPLOYMENT",
    )
    azure_openai_embedding_api_version: str = Field(
        default="2024-02-01", alias="AZURE_OPENAI_EMBEDDING_API_VERSION"
    )

    cosmos_endpoint: str = Field(default="", alias="COSMOS_ENDPOINT")
    cosmos_key: str = Field(default="", alias="COSMOS_KEY")
    cosmos_database_name: str = Field(default="", alias="COSMOS_DATABASE_NAME")

    background_jobs_enabled: bool = Field(default=True, alias="BACKGROUND_JOBS_ENABLED")
    sync_interval_minutes: int = Field(default=15, alias="SYNC_INTERVAL_MINUTES")

    cors_origins_raw: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")

    @property
    def cors_origins(self) -> List[str]:
        return [
            origin.strip()
            for origin in self.cors_origins_raw.split(",")
            if origin.strip()
        ]

    @property
    def confluence_space_keys(self) -> List[str]:
        return [
            key.strip()
            for key in self.confluence_space_keys_raw.split(",")
            if key.strip()
        ]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
