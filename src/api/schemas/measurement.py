"""Daily measurement schema, mirroring `aq_marts.fct_ispu_daily` columns."""

from datetime import date

from pydantic import BaseModel


class DailyMeasurement(BaseModel):
    """One station's ISPU reading for a single calendar day."""

    measurement_date: date
    station_id: str
    pm10: int | None = None
    pm25: int | None = None
    so2: int | None = None
    co: int | None = None
    o3: int | None = None
    no2: int | None = None
    max_ispu: int | None = None
    critical_pollutant: str | None = None
    category: str | None = None
