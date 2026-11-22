"""Health and readiness endpoints."""

from fastapi import APIRouter

from src.api.config import get_settings

router = APIRouter(tags=["meta"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness probe. Returns the service status and active data mode."""
    return {"status": "ok", "mode": get_settings().data_mode}
