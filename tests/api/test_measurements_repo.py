"""Tests for daily-measurement repository methods (sample + mocked live)."""

from datetime import date
from unittest.mock import MagicMock

from src.api.config import Settings
from src.api.repositories.live_repo import LiveRepository
from src.api.repositories.sample_repo import SampleRepository


def test_daily_series_filters_by_station_and_range():
    rows = SampleRepository().get_daily_series("DKI1", date(2024, 1, 1), date(2024, 1, 2))
    assert rows, "expected sample rows"
    assert all(r.station_id == "DKI1" for r in rows)
    assert all(date(2024, 1, 1) <= r.measurement_date <= date(2024, 1, 2) for r in rows)


def test_gaps_not_fabricated():
    rows = SampleRepository().get_daily_series("DKI1", date(2024, 1, 1), date(2024, 1, 4))
    dates = {r.measurement_date for r in rows}
    assert date(2024, 1, 3) not in dates  # the missing day stays missing


def test_category_derived_when_null():
    rows = SampleRepository().get_daily_series("DKI1", date(2024, 1, 1), date(2024, 1, 4))
    row = next(r for r in rows if r.measurement_date == date(2024, 1, 4))
    assert row.category == "SEDANG"  # derived from max_ispu=75, stored category was null


def test_latest_returns_most_recent_sample():
    latest = SampleRepository().get_latest("DKI1")
    assert latest is not None
    assert latest.measurement_date == date(2024, 1, 4)


def test_live_daily_sql_filters_partition_and_cluster():
    client = MagicMock()
    client.query.return_value.result.return_value = []
    repo = LiveRepository(client, Settings(data_mode="live"))
    repo.get_daily_series("DKI1", date(2024, 1, 1), date(2024, 1, 31))
    sql = client.query.call_args[0][0]
    assert "measurement_date BETWEEN" in sql  # partition filter
    assert "station_id = @station_id" in sql  # cluster filter
