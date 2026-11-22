"""Tests for the meta (reference data) router."""

from fastapi.testclient import TestClient

from src.api.main import create_app


def test_categories_returns_five_bands():
    client = TestClient(create_app())
    r = client.get("/meta/categories")
    assert r.status_code == 200
    bands = r.json()
    assert len(bands) == 5
    assert bands[0]["label"] == "BAIK"
