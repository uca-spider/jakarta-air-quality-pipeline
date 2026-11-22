"""Tests for the live BigQuery repository backend (client is mocked)."""

from unittest.mock import MagicMock

import pytest
from google.api_core.exceptions import GoogleAPIError

from src.api.config import Settings
from src.api.repositories.base import RepositoryError
from src.api.repositories.live_repo import LiveRepository


@pytest.fixture
def settings():
    return Settings(data_mode="live")


@pytest.fixture
def mock_bq_client():
    client = MagicMock()
    client.query.return_value.result.return_value = []
    return client


def test_get_stations_queries_marts_dataset(mock_bq_client, settings):
    repo = LiveRepository(mock_bq_client, settings)
    repo.get_stations()
    sql = mock_bq_client.query.call_args[0][0]
    assert "aq_marts.dim_stations" in sql


def test_query_error_raises_repository_error(mock_bq_client, settings):
    mock_bq_client.query.side_effect = GoogleAPIError("boom")
    with pytest.raises(RepositoryError):
        LiveRepository(mock_bq_client, settings).get_stations()
