"""Monthly trend schema, mirroring `aq_marts.fct_ispu_monthly_trends`."""

from pydantic import BaseModel


class MonthlyTrend(BaseModel):
    """Pre-aggregated monthly air-quality metrics for one station."""

    monthly_trend_id: str
    station_id: str
    station_name: str
    administrative_area: str
    year: int
    month: int
    month_name: str
    total_recorded_days: int
    days_with_pm25: int
    avg_max_ispu: float | None = None
    peak_max_ispu: int | None = None
    avg_pm10: float | None = None
    avg_pm25: float | None = None
    good_days_count: int
    moderate_days_count: int
    unhealthy_days_count: int
    pct_unhealthy_days: float | None = None
