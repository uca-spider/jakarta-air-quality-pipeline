"""Live repository backend querying BigQuery marts (cost-aware SQL)."""

from collections.abc import Sequence
from typing import Any

from google.api_core.exceptions import GoogleAPIError
from google.cloud import bigquery

from src.api.config import Settings
from src.api.repositories.base import RepositoryError
from src.api.schemas.station import Station


def _to_station(row: Any) -> Station:
    return Station(
        station_id=row["station_id"],
        station_name=row["station_name"],
        station_label=row["station_label"],
        administrative_area=row["administrative_area"],
        latitude=row["latitude"],
        longitude=row["longitude"],
    )


class LiveRepository:
    """Serves the Jakarta ISPU marts from BigQuery."""

    def __init__(self, client: bigquery.Client, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    def _marts(self, table: str) -> str:
        s = self._settings
        return f"{s.gcp_project}.{s.marts_dataset}.{table}"

    def _run(
        self,
        sql: str,
        params: Sequence[bigquery.ScalarQueryParameter] | None = None,
    ) -> list[Any]:
        """Execute a query, mapping any BigQuery failure to RepositoryError."""
        try:
            if params:
                job = self._client.query(
                    sql, job_config=bigquery.QueryJobConfig(query_parameters=list(params))
                )
            else:
                job = self._client.query(sql)
            return list(job.result())
        except GoogleAPIError as exc:
            raise RepositoryError(str(exc)) from exc

    def get_stations(self) -> list[Station]:
        sql = (
            "SELECT station_id, station_name, station_label, administrative_area, "
            f"latitude, longitude FROM `{self._marts('dim_stations')}` ORDER BY station_id"
        )
        return [_to_station(r) for r in self._run(sql)]

    def get_station(self, station_id: str) -> Station | None:
        sql = (
            "SELECT station_id, station_name, station_label, administrative_area, "
            f"latitude, longitude FROM `{self._marts('dim_stations')}` "
            "WHERE station_id = @station_id"
        )
        params = [bigquery.ScalarQueryParameter("station_id", "STRING", station_id)]
        rows = self._run(sql, params)
        return _to_station(rows[0]) if rows else None
