"""Repository interface and shared error type for the API data layer."""

from typing import Protocol, runtime_checkable

from src.api.schemas.station import Station


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
