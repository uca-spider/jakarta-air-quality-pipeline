"""Tests for the offline sample repository backend."""

from src.api.repositories.sample_repo import SampleRepository
from src.api.schemas.station import Station


def test_get_stations_returns_five():
    repo = SampleRepository()
    stations = repo.get_stations()
    assert len(stations) == 5
    assert all(isinstance(s, Station) for s in stations)


def test_get_known_station():
    station = SampleRepository().get_station("DKI1")
    assert station is not None
    assert station.station_id == "DKI1"


def test_get_station_unknown_returns_none():
    assert SampleRepository().get_station("DKI9") is None
