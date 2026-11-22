"""Health and readiness endpoints."""

from fastapi import APIRouter, Depends

from src.api.config import get_settings
from src.api.dependencies import get_repository
from src.api.repositories.base import IspuRepository

router = APIRouter(tags=["meta"])


@router.get("/health")
def health(
    ready: bool = False,
    repo: IspuRepository = Depends(get_repository),
) -> dict[str, str]:
    """Liveness probe.

    With ``?ready=1`` it also performs a readiness check by touching the data
    source; a data-source failure surfaces as HTTP 503 via the app's
    RepositoryError handler.
    """
    if ready:
        repo.get_stations()
    return {"status": "ok", "mode": get_settings().data_mode}
