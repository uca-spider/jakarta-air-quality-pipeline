"""Offline repository backend serving bundled synthetic sample data.

Lets the API (and its Swagger docs) run with zero GCP setup. Fixtures are
small, synthetic JSON files under ``sample_data/`` and are source, not data.
"""

import json
from pathlib import Path

from src.api.schemas.station import Station

_SAMPLE_DIR = Path(__file__).parent / "sample_data"


def _load(name: str) -> list[dict]:
    """Load a sample JSON fixture as a list of records."""
    return json.loads((_SAMPLE_DIR / name).read_text(encoding="utf-8"))


class SampleRepository:
    """Serves the Jakarta ISPU marts from bundled sample fixtures."""

    def __init__(self) -> None:
        self._stations: list[Station] = [Station(**row) for row in _load("stations.json")]

    def get_stations(self) -> list[Station]:
        return list(self._stations)

    def get_station(self, station_id: str) -> Station | None:
        return next((s for s in self._stations if s.station_id == station_id), None)
