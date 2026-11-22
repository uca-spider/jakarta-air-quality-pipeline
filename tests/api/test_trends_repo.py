"""Tests for monthly-trends repository methods (sample + mocked live)."""

from unittest.mock import MagicMock

from src.api.config import Settings
from src.api.repositories.live_repo import LiveRepository
from src.api.repositories.sample_repo import SampleRepository


def test_monthly_trends_filters_station():
    rows = SampleRepository().get_monthly_trends("DKI1", None)
    assert rows
    assert all(r.station_id == "DKI1" for r in rows)


def test_year_filter_optional_and_applied():
    repo = SampleRepository()
    all_rows = repo.get_monthly_trends("DKI1", None)
    y2024 = repo.get_monthly_trends("DKI1", 2024)
    assert all(r.year == 2024 for r in y2024)
    assert len(y2024) < len(all_rows)


def test_sorted_by_year_then_month():
    rows = SampleRepository().get_monthly_trends("DKI1", None)
    keys = [(r.year, r.month) for r in rows]
    assert keys == sorted(keys)


def test_live_trends_reads_monthly_mart_not_daily():
    client = MagicMock()
    client.query.return_value.result.return_value = []
    repo = LiveRepository(client, Settings(data_mode="live"))
    repo.get_monthly_trends("DKI1", None)
    sql = client.query.call_args[0][0]
    assert "fct_ispu_monthly_trends" in sql
    assert "fct_ispu_daily" not in sql
