"""Daily measurement endpoints backed by `aq_marts.fct_ispu_daily`."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.config import get_settings
from src.api.dependencies import get_repository
from src.api.repositories.base import IspuRepository
from src.api.schemas.measurement import DailyMeasurement

router = APIRouter(prefix="/stations", tags=["measurements"])


def _require_station(repo: IspuRepository, station_id: str) -> None:
    if repo.get_station(station_id) is None:
        raise HTTPException(status_code=404, detail=f"Unknown station: {station_id}")


@router.get("/{station_id}/daily", response_model=list[DailyMeasurement])
def daily(
    station_id: str,
    start: date = Query(..., description="Inclusive start date (YYYY-MM-DD)."),
    end: date = Query(..., description="Inclusive end date (YYYY-MM-DD)."),
    repo: IspuRepository = Depends(get_repository),
) -> list[DailyMeasurement]:
    """Daily ISPU series for a station within a bounded date range."""
    _require_station(repo, station_id)
    if start > end:
        raise HTTPException(status_code=422, detail="start must be on or before end.")
    max_days = get_settings().max_daily_range_days
    if (end - start).days > max_days:
        raise HTTPException(
            status_code=422, detail=f"Date range must not exceed {max_days} days."
        )
    return repo.get_daily_series(station_id, start, end)


@router.get("/{station_id}/latest", response_model=DailyMeasurement)
def latest(
    station_id: str, repo: IspuRepository = Depends(get_repository)
) -> DailyMeasurement:
    """Most recent available reading for a station."""
    _require_station(repo, station_id)
    reading = repo.get_latest(station_id)
    if reading is None:
        raise HTTPException(status_code=404, detail="No measurements for this station.")
    return reading
