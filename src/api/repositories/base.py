"""Repository interface and shared error type for the API data layer."""

from datetime import date
from typing import Protocol, runtime_checkable

from src.api.schemas.measurement import DailyMeasurement
from src.api.schemas.station import Station
from src.api.schemas.trend import MonthlyTrend


class RepositoryError(Exception):
    """Raised when the underlying data source fails (e.g. BigQuery error)."""


@runtime_checkable
class IspuRepository(Protocol):
    """Read access to the Jakarta ISPU marts.

    Implemented by both the offline `SampleRepository` and the BigQuery-backed
    `LiveRepository`. Methods are added as later resources are implemented.
    """

    def get_stations(self) -> list[Station]:
        """Return all monitoring stations."""
        ...

    def get_station(self, station_id: str) -> Station | None:
        """Return one station by id, or None if it does not exist."""
        ...

    def get_daily_series(
        self, station_id: str, start: date, end: date
    ) -> list[DailyMeasurement]:
        """Return daily measurements for a station within [start, end]."""
        ...

    def get_latest(self, station_id: str) -> DailyMeasurement | None:
        """Return the most recent measurement for a station, or None."""
        ...

    def get_monthly_trends(
        self, station_id: str, year: int | None
    ) -> list[MonthlyTrend]:
        """Return monthly trend rows for a station, optionally filtered by year."""
        ...
