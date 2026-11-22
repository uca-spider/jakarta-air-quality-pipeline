"""Tests for the data-quality summary router (sample mode)."""

from fastapi.testclient import TestClient

from src.api.main import create_app

client = TestClient(create_app())


def test_quality_summary_200():
    r = client.get("/quality/summary")
    assert r.status_code == 200
    body = r.json()
    assert len(body) >= 1
    assert {"source_file", "valid_rows", "quarantined_rows", "dominant_reason"} <= set(
        body[0].keys()
    )
