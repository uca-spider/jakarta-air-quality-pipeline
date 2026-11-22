"""Tests for the daily-measurements and latest-reading router (sample mode)."""

from fastapi.testclient import TestClient

from src.api.main import create_app

client = TestClient(create_app())


def test_daily_requires_date_range():
    r = client.get("/stations/DKI1/daily")
    assert r.status_code == 422


def test_daily_range_too_wide_422():
    r = client.get(
        "/stations/DKI1/daily", params={"start": "2020-01-01", "end": "2024-01-01"}
    )
    assert r.status_code == 422


def test_daily_start_after_end_422():
    r = client.get(
        "/stations/DKI1/daily", params={"start": "2024-02-01", "end": "2024-01-01"}
    )
    assert r.status_code == 422


def test_daily_unknown_station_404():
    r = client.get(
        "/stations/DKI9/daily", params={"start": "2024-01-01", "end": "2024-01-31"}
    )
    assert r.status_code == 404


def test_daily_returns_series_200():
    r = client.get(
        "/stations/DKI1/daily", params={"start": "2024-01-01", "end": "2024-01-04"}
    )
    assert r.status_code == 200
    assert len(r.json()) == 3  # 01-01, 01-02, 01-04 (01-03 is a gap)


def test_latest_returns_most_recent():
    r = client.get("/stations/DKI1/latest")
    assert r.status_code == 200
    assert r.json()["measurement_date"] == "2024-01-04"
