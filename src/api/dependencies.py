"""Shared FastAPI dependencies, including repository selection by data mode."""

from functools import lru_cache

from src.api.config import get_settings
from src.api.repositories.base import IspuRepository
from src.api.repositories.sample_repo import SampleRepository


@lru_cache
def get_repository() -> IspuRepository:
    """Return the repository backend selected by ``API_DATA_MODE``."""
    settings = get_settings()
    if settings.data_mode == "live":
        from src.api.repositories.bigquery_client import make_bigquery_client
        from src.api.repositories.live_repo import LiveRepository

        return LiveRepository(make_bigquery_client(settings.gcp_project), settings)
    return SampleRepository()
