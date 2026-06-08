from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    elasticsearch_url: str = Field(default="http://localhost:9200", alias="ELASTICSEARCH_URL")
    elasticsearch_index: str = Field(default="cirro-search-v1", alias="ELASTICSEARCH_INDEX")
    elasticsearch_request_timeout: int = Field(default=10, alias="ELASTICSEARCH_REQUEST_TIMEOUT")


@lru_cache
def get_settings() -> Settings:
    return Settings()
