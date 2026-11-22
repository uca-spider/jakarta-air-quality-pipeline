"""Offline repository backend serving bundled synthetic sample data.

Lets the API (and its Swagger docs) run with zero GCP setup. Fixtures are
small, synthetic JSON files under ``sample_data/`` and are source, not data.
"""

import json
from datetime import date
from pathlib import Path

from src.api.schemas.measurement import DailyMeasurement
from src.api.schemas.station import Station
from src.api.schemas.trend import MonthlyTrend
from src.api.services.ispu_categories import derive_category

_SAMPLE_DIR = Path(__file__).parent / "sample_data"


def _load(name: str) -> list[dict]:
    """Load a sample JSON fixture as a list of records."""
    return json.loads((_SAMPLE_DIR / name).read_text(encoding="utf-8"))


def _build_daily(row: dict) -> DailyMeasurement:
    """Build a DailyMeasurement, deriving the category when it is absent."""
    row = dict(row)
    row["category"] = derive_category(row.get("category"), row.get("max_ispu"))
    return DailyMeasurement(**row)


class SampleRepository:
    """Serves the Jakarta ISPU marts from bundled sample fixtures."""

    def __init__(self) -> None:
        self._stations: list[Station] = [Station(**row) for row in _load("stations.json")]
        self._daily: list[DailyMeasurement] = [
            _build_daily(row) for row in _load("daily.json")
        ]
        self._trends: list[MonthlyTrend] = [
            MonthlyTrend(**row) for row in _load("trends.json")
        ]

    def get_stations(self) -> list[Station]:
        return list(self._stations)

    def get_station(self, station_id: str) -> Station | None:
        return next((s for s in self._stations if s.station_id == station_id), None)

    def get_daily_series(
        self, station_id: str, start: date, end: date
    ) -> list[DailyMeasurement]:
        rows = [
            m
            for m in self._daily
            if m.station_id == station_id and start <= m.measurement_date <= end
        ]
        return sorted(rows, key=lambda m: m.measurement_date)

    def get_latest(self, station_id: str) -> DailyMeasurement | None:
        rows = [m for m in self._daily if m.station_id == station_id]
        return max(rows, key=lambda m: m.measurement_date) if rows else None

    def get_monthly_trends(
        self, station_id: str, year: int | None
    ) -> list[MonthlyTrend]:
        rows = [t for t in self._trends if t.station_id == station_id]
        if year is not None:
            rows = [t for t in rows if t.year == year]
        return sorted(rows, key=lambda t: (t.year, t.month))
