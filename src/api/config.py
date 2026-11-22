"""Application settings for the Jakarta Air Quality REST API.

Settings are read from environment variables with the ``API_`` prefix
(for example ``API_DATA_MODE=live``). Defaults make the API run in
offline ``sample`` mode with zero GCP setup.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the API."""

    model_config = SettingsConfigDict(env_prefix="API_")

    data_mode: Literal["sample", "live"] = "sample"
    gcp_project: str = "jakarta-air-quality"
    marts_dataset: str = "aq_marts"
    raw_dataset: str = "aq_raw"
    cors_origins: list[str] = ["*"]
    max_daily_range_days: int = 366


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""
    return Settings()
