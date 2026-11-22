"""Tests for the monthly-trends router (sample mode)."""

from fastapi.testclient import TestClient

from src.api.main import create_app

client = TestClient(create_app())


def test_trends_200():
    r = client.get("/stations/DKI1/trends")
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_trends_year_filter_200():
    r = client.get("/stations/DKI1/trends", params={"year": 2024})
    assert r.status_code == 200
    assert all(row["year"] == 2024 for row in r.json())


def test_trends_unknown_station_404():
    r = client.get("/stations/DKI9/trends")
    assert r.status_code == 404
