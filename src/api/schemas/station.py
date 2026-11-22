"""Station schema, mirroring the `aq_marts.dim_stations` columns."""

from pydantic import BaseModel


class Station(BaseModel):
    """An official SPKU air-quality monitoring station in DKI Jakarta."""

    station_id: str
    station_name: str
    station_label: str
    administrative_area: str
    latitude: float
    longitude: float
