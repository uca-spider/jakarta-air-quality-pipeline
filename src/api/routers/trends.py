"""Monthly trend endpoints backed by `aq_marts.fct_ispu_monthly_trends`."""

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.dependencies import get_repository
from src.api.repositories.base import IspuRepository
from src.api.schemas.trend import MonthlyTrend

router = APIRouter(prefix="/stations", tags=["trends"])


@router.get("/{station_id}/trends", response_model=list[MonthlyTrend])
def trends(
    station_id: str,
    year: int | None = Query(None, description="Optional calendar year filter."),
    repo: IspuRepository = Depends(get_repository),
) -> list[MonthlyTrend]:
    """Pre-aggregated monthly trend metrics for a station."""
    if repo.get_station(station_id) is None:
        raise HTTPException(status_code=404, detail=f"Unknown station: {station_id}")
    return repo.get_monthly_trends(station_id, year)
