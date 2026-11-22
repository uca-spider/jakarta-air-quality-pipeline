"""Tests for the health endpoint."""

from fastapi.testclient import TestClient

from src.api.main import create_app


def test_health_ok():
    client = TestClient(create_app())
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
