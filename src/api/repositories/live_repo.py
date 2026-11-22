"""Live repository backend querying BigQuery marts (cost-aware SQL)."""

from collections.abc import Sequence
from datetime import date
from typing import Any

from google.api_core.exceptions import GoogleAPIError
from google.cloud import bigquery

from src.api.config import Settings
from src.api.repositories.base import RepositoryError
from src.api.schemas.measurement import DailyMeasurement
from src.api.schemas.quality import QualitySummaryRow
from src.api.schemas.station import Station
from src.api.schemas.trend import MonthlyTrend
from src.api.services.ispu_categories import derive_category

_TREND_COLUMNS = (
    "monthly_trend_id, station_id, station_name, administrative_area, year, month, "
    "month_name, total_recorded_days, days_with_pm25, avg_max_ispu, peak_max_ispu, "
    "avg_pm10, avg_pm25, good_days_count, moderate_days_count, unhealthy_days_count, "
    "pct_unhealthy_days"
)

_DAILY_COLUMNS = (
    "measurement_date, station_id, pm10, pm25, so2, co, o3, no2, "
    "max_ispu, critical_pollutant, category"
)


def _to_station(row: Any) -> Station:
    return Station(
        station_id=row["station_id"],
        station_name=row["station_name"],
        station_label=row["station_label"],
        administrative_area=row["administrative_area"],
        latitude=row["latitude"],
        longitude=row["longitude"],
    )


def _to_daily(row: Any) -> DailyMeasurement:
    return DailyMeasurement(
        measurement_date=row["measurement_date"],
        station_id=row["station_id"],
        pm10=row["pm10"],
        pm25=row["pm25"],
        so2=row["so2"],
        co=row["co"],
        o3=row["o3"],
        no2=row["no2"],
        max_ispu=row["max_ispu"],
        critical_pollutant=row["critical_pollutant"],
        category=derive_category(row["category"], row["max_ispu"]),
    )


class LiveRepository:
    """Serves the Jakarta ISPU marts from BigQuery."""

    def __init__(self, client: bigquery.Client, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    def _marts(self, table: str) -> str:
        s = self._settings
        return f"{s.gcp_project}.{s.marts_dataset}.{table}"

    def _raw(self, table: str) -> str:
        s = self._settings
        return f"{s.gcp_project}.{s.raw_dataset}.{table}"

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

    def get_daily_series(
        self, station_id: str, start: date, end: date
    ) -> list[DailyMeasurement]:
        # Filters on the monthly partition key (measurement_date) and the
        # cluster key (station_id) to minimise bytes scanned.
        sql = (
            f"SELECT {_DAILY_COLUMNS} FROM `{self._marts('fct_ispu_daily')}` "
            "WHERE station_id = @station_id "
            "AND measurement_date BETWEEN @start AND @end "
            "ORDER BY measurement_date"
        )
        params = [
            bigquery.ScalarQueryParameter("station_id", "STRING", station_id),
            bigquery.ScalarQueryParameter("start", "DATE", start),
            bigquery.ScalarQueryParameter("end", "DATE", end),
        ]
        return [_to_daily(r) for r in self._run(sql, params)]

    def get_latest(self, station_id: str) -> DailyMeasurement | None:
        sql = (
            f"SELECT {_DAILY_COLUMNS} FROM `{self._marts('fct_ispu_daily')}` "
            "WHERE station_id = @station_id "
            "ORDER BY measurement_date DESC LIMIT 1"
        )
        params = [bigquery.ScalarQueryParameter("station_id", "STRING", station_id)]
        rows = self._run(sql, params)
        return _to_daily(rows[0]) if rows else None

    def get_monthly_trends(
        self, station_id: str, year: int | None
    ) -> list[MonthlyTrend]:
        where = "WHERE station_id = @station_id"
        params = [bigquery.ScalarQueryParameter("station_id", "STRING", station_id)]
        if year is not None:
            where += " AND year = @year"
            params.append(bigquery.ScalarQueryParameter("year", "INT64", year))
        sql = (
            f"SELECT {_TREND_COLUMNS} FROM `{self._marts('fct_ispu_monthly_trends')}` "
            f"{where} ORDER BY year, month"
        )
        return [MonthlyTrend(**dict(r)) for r in self._run(sql, params)]

    def get_quality_summary(self) -> list[QualitySummaryRow]:
        sql = (
            "WITH valid AS ("
            f"  SELECT source_file, COUNT(*) AS valid_rows FROM `{self._raw('ispu')}` "
            "  GROUP BY source_file"
            "), quar AS ("
            "  SELECT source_file, COUNT(*) AS quarantined_rows "
            f"  FROM `{self._raw('ispu_quarantine')}` GROUP BY source_file"
            "), dominant AS ("
            "  SELECT source_file, quarantine_reason AS dominant_reason FROM ("
            "    SELECT source_file, quarantine_reason, "
            "    ROW_NUMBER() OVER (PARTITION BY source_file ORDER BY COUNT(*) DESC) AS rn "
            f"    FROM `{self._raw('ispu_quarantine')}` GROUP BY source_file, quarantine_reason"
            "  ) WHERE rn = 1"
            ") "
            "SELECT COALESCE(v.source_file, q.source_file) AS source_file, "
            "COALESCE(v.valid_rows, 0) AS valid_rows, "
            "COALESCE(q.quarantined_rows, 0) AS quarantined_rows, "
            "d.dominant_reason "
            "FROM valid v "
            "FULL OUTER JOIN quar q ON v.source_file = q.source_file "
            "LEFT JOIN dominant d ON COALESCE(v.source_file, q.source_file) = d.source_file "
            "ORDER BY source_file"
        )
        return [QualitySummaryRow(**dict(r)) for r in self._run(sql)]
