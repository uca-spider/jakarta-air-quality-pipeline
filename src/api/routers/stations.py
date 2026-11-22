"""Station endpoints backed by `aq_marts.dim_stations`."""

from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencies import get_repository
from src.api.repositories.base import IspuRepository
from src.api.schemas.station import Station

router = APIRouter(prefix="/stations", tags=["stations"])


@router.get("", response_model=list[Station])
def list_stations(repo: IspuRepository = Depends(get_repository)) -> list[Station]:
    """List all SPKU monitoring stations."""
    return repo.get_stations()


@router.get("/{station_id}", response_model=Station)
def get_station(
    station_id: str, repo: IspuRepository = Depends(get_repository)
) -> Station:
    """Return one station by id (`DKI1`–`DKI5`); 404 if unknown."""
    station = repo.get_station(station_id)
    if station is None:
        raise HTTPException(status_code=404, detail=f"Unknown station: {station_id}")
    return station
