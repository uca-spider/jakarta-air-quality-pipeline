"""Tests for the stations router (sample mode + readiness failure)."""

from fastapi.testclient import TestClient

from src.api.dependencies import get_repository
from src.api.main import create_app
from src.api.repositories.base import RepositoryError


def test_list_stations_200():
    client = TestClient(create_app())
    r = client.get("/stations")
    assert r.status_code == 200
    assert len(r.json()) == 5


def test_get_unknown_station_404():
    client = TestClient(create_app())
    r = client.get("/stations/DKI9")
    assert r.status_code == 404


def test_readiness_503_when_repo_down():
    class _FailingRepo:
        def get_stations(self):
            raise RepositoryError("down")

        def get_station(self, station_id):  # pragma: no cover - not used here
            raise RepositoryError("down")

    app = create_app()
    app.dependency_overrides[get_repository] = lambda: _FailingRepo()
    client = TestClient(app, raise_server_exceptions=False)
    r = client.get("/health", params={"ready": 1})
    assert r.status_code == 503
